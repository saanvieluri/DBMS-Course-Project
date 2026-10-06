"""Database layer: MySQL connection, queries and business rules."""
import os
from contextlib import contextmanager

import mysql.connector
from mysql.connector import Error

# ---- EDIT THESE (or set environment variables) -------------------------
CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "your_password"),
    "database": os.getenv("DB_NAME", "course_progress"),
}
# -------------------------------------------------------------------------

TABLES = ["instructor", "learner", "course", "module", "lesson", "enrolment",
          "lesson_progress", "quiz", "question", "attempt", "response",
          "certificate", "feedback"]


def friendly(err):
    """Turn a MySQL error into a readable message."""
    code = getattr(err, "errno", None)
    msg = str(err)
    if code == 1062:
        return "Duplicate entry: this record already exists (UNIQUE constraint).\n\n" + msg
    if code == 1451:
        return "Cannot delete: other records depend on this row (FOREIGN KEY constraint).\n\n" + msg
    if code == 1452:
        return "Cannot insert: the referenced record does not exist (FOREIGN KEY constraint).\n\n" + msg
    if code in (3819, 4025):
        return "Value rejected by a CHECK constraint.\n\n" + msg
    if code == 1048:
        return "A required (NOT NULL) value is missing.\n\n" + msg
    return msg


class Db:
    def __init__(self):
        self.conn = mysql.connector.connect(**CONFIG)
        self.conn.autocommit = True      # reads always see the latest committed data
        self.log = []                    # (sql, rows_affected) of the last action

    # ---------- low level ----------
    def query(self, sql, params=()):
        cur = self.conn.cursor()
        try:
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            return cols, cur.fetchall()
        finally:
            cur.close()

    def one(self, sql, params=()):
        rows = self.query(sql, params)[1]
        return rows[0] if rows else None

    def execute(self, sql, params=()):
        cur = self.conn.cursor()
        try:
            cur.execute(sql, params)
            stmt = cur.statement
            if isinstance(stmt, bytes):
                stmt = stmt.decode()
            self.log.append((" ".join(stmt.split()), cur.rowcount))
            return cur.lastrowid
        finally:
            cur.close()

    @contextmanager
    def tx(self):
        self.conn.start_transaction()
        try:
            yield
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def counts(self):
        return {t: self.query(f"SELECT COUNT(*) FROM {t}")[1][0][0] for t in TABLES}

    # ---------- learners ----------
    def add_learner(self, name, email, joined):
        with self.tx():
            self.execute("INSERT INTO learner (name, email, joined_date) VALUES (%s, %s, %s)",
                         (name, email, joined))

    def delete_learner(self, learner_id):
        with self.tx():
            self.execute("DELETE FROM learner WHERE learner_id = %s", (learner_id,))

    # ---------- courses ----------
    def add_course(self, title, level, instructor_id):
        with self.tx():
            self.execute("INSERT INTO course (title, level, instructor_id) VALUES (%s, %s, %s)",
                         (title, level, instructor_id))

    def delete_course(self, course_id):
        with self.tx():
            self.execute("DELETE FROM course WHERE course_id = %s", (course_id,))

    # ---------- enrolments ----------
    def enrol(self, learner_id, course_id):
        with self.tx():
            self.execute("INSERT INTO enrolment (learner_id, course_id) VALUES (%s, %s)",
                         (learner_id, course_id))

    def delete_enrolment(self, enrolment_id):
        with self.tx():      # progress, attempts, responses, certificate, feedback cascade
            self.execute("DELETE FROM enrolment WHERE enrolment_id = %s", (enrolment_id,))

    # ---------- lesson progress ----------
    def save_progress(self, enrolment_id, lesson_id, pct):
        if not 0 <= pct <= 100:
            raise ValueError("Progress must be between 0 and 100.")
        enrol = self.one("SELECT course_id, status FROM enrolment WHERE enrolment_id = %s", (enrolment_id,))
        if enrol is None:
            raise ValueError("Enrolment not found.")
        course_id, status = enrol
        if status == "Dropped":
            raise ValueError("This enrolment was dropped; progress cannot be recorded.")
        in_course = self.one(
            "SELECT 1 FROM lesson ls JOIN module m ON m.module_id = ls.module_id "
            "WHERE ls.lesson_id = %s AND m.course_id = %s", (lesson_id, course_id))
        if not in_course:
            raise ValueError("That lesson does not belong to the enrolled course.")
        with self.tx():
            self.execute(
                "INSERT INTO lesson_progress (enrolment_id, lesson_id, completion_pct) VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE completion_pct = VALUES(completion_pct)",
                (enrolment_id, lesson_id, pct))
            total = self.one("SELECT COUNT(*) FROM lesson ls JOIN module m ON m.module_id = ls.module_id "
                             "WHERE m.course_id = %s", (course_id,))[0]
            done = self.one("SELECT COUNT(*) FROM lesson_progress WHERE enrolment_id = %s "
                            "AND completion_pct = 100", (enrolment_id,))[0]
            if done == total and status == "Active":
                self.execute("UPDATE enrolment SET status = 'Completed' WHERE enrolment_id = %s",
                             (enrolment_id,))

    def delete_progress(self, progress_id):
        with self.tx():
            self.execute("DELETE FROM lesson_progress WHERE progress_id = %s", (progress_id,))

    # ---------- quiz attempts ----------
    def add_attempt(self, enrolment_id, quiz_id, score):
        enrol = self.one("SELECT course_id FROM enrolment WHERE enrolment_id = %s", (enrolment_id,))
        quiz = self.one("SELECT course_id, max_score, max_attempts FROM quiz WHERE quiz_id = %s", (quiz_id,))
        if enrol is None or quiz is None:
            raise ValueError("Enrolment or quiz not found.")
        if enrol[0] != quiz[0]:
            raise ValueError("This quiz belongs to a different course than the enrolment.")
        if not 0 <= score <= quiz[1]:
            raise ValueError(f"Score must be between 0 and {quiz[1]} for this quiz.")
        used = self.one("SELECT COUNT(*) FROM attempt WHERE enrolment_id = %s AND quiz_id = %s",
                        (enrolment_id, quiz_id))[0]
        if used >= quiz[2]:
            raise ValueError(f"Attempt limit reached ({quiz[2]} attempts allowed).")
        with self.tx():
            self.execute("INSERT INTO attempt (enrolment_id, quiz_id, attempt_no, score) VALUES (%s, %s, %s, %s)",
                         (enrolment_id, quiz_id, used + 1, score))

    def delete_attempt(self, attempt_id):
        with self.tx():
            self.execute("DELETE FROM attempt WHERE attempt_id = %s", (attempt_id,))

    # ---------- certificates ----------
    def issue_certificate(self, enrolment_id):
        row = self.one("SELECT status FROM enrolment WHERE enrolment_id = %s", (enrolment_id,))
        if row is None or row[0] != "Completed":
            raise ValueError("Certificate can be issued only for a completed enrolment.")
        with self.tx():
            self.execute("INSERT INTO certificate (enrolment_id) VALUES (%s)", (enrolment_id,))
