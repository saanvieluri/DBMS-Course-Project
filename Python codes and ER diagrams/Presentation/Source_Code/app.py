"""Online Course Learning Progress Management System - Tkinter UI (MySQL backend)."""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime

from mysql.connector import Error

import db as dbm

BG, WH, TEAL, DK, GR, RED = "#F5FAF9", "#FFFFFF", "#0F766E", "#1F2937", "#6B7280", "#DC2626"
LEVELS = ["Beginner", "Intermediate", "Advanced"]


def cid(combo):
    """Return the numeric id from a 'id - label' combobox value."""
    value = combo.get()
    if not value:
        raise ValueError("Please choose a value in every dropdown.")
    return int(value.split(" - ")[0])


def set_choices(combo, rows):
    current = combo.get()
    values = [f"{r[0]} - {r[1]}" for r in rows]
    combo["values"] = values
    combo.set(current if current in values else "")


class BaseTab(ttk.Frame):
    name = ""
    form_title = ""
    list_title = ""
    noun = "record"
    select_sql = ""
    delete_note = ""

    def __init__(self, nb, app):
        super().__init__(nb, padding=12)
        self.app, self.db = app, app.db
        self.form = ttk.LabelFrame(self, text=self.form_title, padding=10)
        self.form.pack(fill="x")
        self.build_form(self.form)
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(10, 4))
        ttk.Label(bar, text=self.list_title, font=("TkDefaultFont", 12, "bold"), foreground=TEAL).pack(side="left")
        self.build_bar(bar)
        wrap = ttk.Frame(self)
        wrap.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(wrap, show="headings", selectmode="browse")
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

    # --- hooks ---
    def build_form(self, f): pass
    def reload_choices(self): pass
    def delete_row(self, rid): raise NotImplementedError

    def build_bar(self, bar):
        ttk.Button(bar, text="Delete selected", style="Danger.TButton", command=self.delete).pack(side="right")
        ttk.Button(bar, text="Refresh", command=self.app.refresh_all).pack(side="right", padx=6)

    def refresh(self):
        self.reload_choices()
        cols, rows = self.db.query(self.select_sql)
        self.fill(cols, rows)

    def fill(self, cols, rows):
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = cols
        for i, c in enumerate(cols):
            self.tree.heading(c, text=c.replace("_", " ").title())
            self.tree.column(c, width=70 if i == 0 else 150, anchor="w", stretch=True)
        for r in rows:
            self.tree.insert("", "end", values=["" if v is None else v for v in r])

    def selected_id(self):
        sel = self.tree.selection()
        if not sel:
            raise ValueError("Select a row in the list first.")
        return int(self.tree.item(sel[0])["values"][0])

    def delete(self):
        try:
            rid = self.selected_id()
        except ValueError as e:
            messagebox.showinfo("Delete", str(e))
            return
        if messagebox.askyesno("Confirm delete", f"Delete {self.noun} #{rid}?{self.delete_note}"):
            self.app.run_action(f"DELETE {self.noun} #{rid}", lambda: self.delete_row(rid))

    @staticmethod
    def grid_row(parent, items):
        for i, (label, widget) in enumerate(items):
            ttk.Label(parent, text=label).grid(row=0, column=i * 2, sticky="w", padx=(0, 6))
            widget.grid(row=0, column=i * 2 + 1, sticky="w", padx=(0, 18))


# ------------------------------------------------------------------ tabs
class EnrolmentsTab(BaseTab):
    name = "Enrolments"
    form_title = "Enrol a learner in a course (INSERT)"
    list_title = "Enrolments (VIEW)"
    noun = "enrolment"
    delete_note = "\n\nIts lesson progress, quiz attempts, certificate and feedback are deleted too (ON DELETE CASCADE)."
    select_sql = ("SELECT e.enrolment_id, l.name AS learner, c.title AS course, e.status, e.enrolled_on "
                  "FROM enrolment e JOIN learner l ON l.learner_id = e.learner_id "
                  "JOIN course c ON c.course_id = e.course_id ORDER BY e.enrolment_id DESC")

    def build_form(self, f):
        self.learner = ttk.Combobox(f, state="readonly", width=26)
        self.course = ttk.Combobox(f, state="readonly", width=34)
        self.grid_row(f, [("Learner", self.learner), ("Course", self.course)])
        ttk.Button(f, text="Enrol", style="Accent.TButton", command=self.add).grid(row=0, column=4)

    def reload_choices(self):
        set_choices(self.learner, self.db.query("SELECT learner_id, name FROM learner ORDER BY name")[1])
        set_choices(self.course, self.db.query("SELECT course_id, title FROM course ORDER BY title")[1])

    def add(self):
        try:
            lid, cid_ = cid(self.learner), cid(self.course)
        except ValueError as e:
            messagebox.showwarning("Check input", str(e))
            return
        self.app.run_action("INSERT enrolment", lambda: self.db.enrol(lid, cid_))

    def delete_row(self, rid): self.db.delete_enrolment(rid)


class LearnersTab(BaseTab):
    name = "Learners"
    form_title = "Register a learner (INSERT)"
    list_title = "Learners (VIEW)"
    noun = "learner"
    delete_note = "\n\nLearners who have enrolments cannot be deleted (FOREIGN KEY)."
    select_sql = "SELECT learner_id, name, email, joined_date FROM learner ORDER BY learner_id DESC"

    def build_form(self, f):
        self.name_v, self.email_v, self.date_v = tk.StringVar(), tk.StringVar(), tk.StringVar(value=str(date.today()))
        self.grid_row(f, [("Name", ttk.Entry(f, textvariable=self.name_v, width=24)),
                          ("Email", ttk.Entry(f, textvariable=self.email_v, width=28)),
                          ("Joined (YYYY-MM-DD)", ttk.Entry(f, textvariable=self.date_v, width=12))])
        ttk.Button(f, text="Add learner", style="Accent.TButton", command=self.add).grid(row=0, column=6)

    def add(self):
        name, email, joined = self.name_v.get().strip(), self.email_v.get().strip(), self.date_v.get().strip()
        try:
            if not name or "@" not in email:
                raise ValueError("Enter a name and a valid email address.")
            datetime.strptime(joined, "%Y-%m-%d")
        except ValueError as e:
            messagebox.showwarning("Check input", str(e) if "Enter" in str(e) else "Date must be YYYY-MM-DD.")
            return
        if self.app.run_action("INSERT learner", lambda: self.db.add_learner(name, email, joined)):
            self.name_v.set(""); self.email_v.set("")

    def delete_row(self, rid): self.db.delete_learner(rid)


class CoursesTab(BaseTab):
    name = "Courses"
    form_title = "Publish a course (INSERT)"
    list_title = "Courses (VIEW)"
    noun = "course"
    delete_note = "\n\nCourses that have modules or enrolments cannot be deleted (FOREIGN KEY)."
    select_sql = ("SELECT c.course_id, c.title, c.level, i.name AS instructor FROM course c "
                  "JOIN instructor i ON i.instructor_id = c.instructor_id ORDER BY c.course_id DESC")

    def build_form(self, f):
        self.title_v = tk.StringVar()
        self.level = ttk.Combobox(f, state="readonly", values=LEVELS, width=14)
        self.level.set("Beginner")
        self.instructor = ttk.Combobox(f, state="readonly", width=26)
        self.grid_row(f, [("Title", ttk.Entry(f, textvariable=self.title_v, width=30)),
                          ("Level", self.level), ("Instructor", self.instructor)])
        ttk.Button(f, text="Publish course", style="Accent.TButton", command=self.add).grid(row=0, column=6)

    def reload_choices(self):
        set_choices(self.instructor, self.db.query("SELECT instructor_id, name FROM instructor ORDER BY name")[1])

    def add(self):
        title = self.title_v.get().strip()
        try:
            if not title:
                raise ValueError("Enter a course title.")
            iid = cid(self.instructor)
        except ValueError as e:
            messagebox.showwarning("Check input", str(e))
            return
        if self.app.run_action("INSERT course", lambda: self.db.add_course(title, self.level.get(), iid)):
            self.title_v.set("")

    def delete_row(self, rid): self.db.delete_course(rid)


class ProgressTab(BaseTab):
    name = "Lesson Progress"
    form_title = "Record lesson progress (INSERT / UPDATE)"
    list_title = "Lesson progress (VIEW)"
    noun = "progress record"
    select_sql = ("SELECT lp.progress_id, l.name AS learner, c.title AS course, ls.title AS lesson, "
                  "lp.completion_pct FROM lesson_progress lp "
                  "JOIN enrolment e ON e.enrolment_id = lp.enrolment_id "
                  "JOIN learner l ON l.learner_id = e.learner_id JOIN course c ON c.course_id = e.course_id "
                  "JOIN lesson ls ON ls.lesson_id = lp.lesson_id ORDER BY lp.progress_id DESC")

    def build_form(self, f):
        self.enrol = ttk.Combobox(f, state="readonly", width=40)
        self.lesson = ttk.Combobox(f, state="readonly", width=24)
        self.pct = ttk.Spinbox(f, from_=0, to=100, width=6)
        self.pct.set(100)
        self.enrol.bind("<<ComboboxSelected>>", lambda e: (self.lesson.set(""), self.load_lessons()))
        self.grid_row(f, [("Enrolment", self.enrol), ("Lesson", self.lesson), ("Completion %", self.pct)])
        ttk.Button(f, text="Save progress", style="Accent.TButton", command=self.add).grid(row=0, column=6)

    def reload_choices(self):
        set_choices(self.enrol, self.db.query(
            "SELECT e.enrolment_id, CONCAT(l.name, ' / ', c.title) FROM enrolment e "
            "JOIN learner l ON l.learner_id = e.learner_id JOIN course c ON c.course_id = e.course_id "
            "WHERE e.status <> 'Dropped' ORDER BY e.enrolment_id")[1])
        self.load_lessons()

    def load_lessons(self):
        if not self.enrol.get():
            self.lesson["values"] = []
            return
        rows = self.db.query(
            "SELECT ls.lesson_id, ls.title FROM lesson ls JOIN module m ON m.module_id = ls.module_id "
            "WHERE m.course_id = (SELECT course_id FROM enrolment WHERE enrolment_id = %s) "
            "ORDER BY m.seq_no, ls.lesson_id", (cid(self.enrol),))[1]
        set_choices(self.lesson, rows)

    def add(self):
        try:
            eid, lid, pct = cid(self.enrol), cid(self.lesson), int(self.pct.get())
        except ValueError as e:
            messagebox.showwarning("Check input", "Choose an enrolment, a lesson and a whole-number percentage.")
            return
        self.app.run_action("SAVE lesson progress", lambda: self.db.save_progress(eid, lid, pct))

    def delete_row(self, rid): self.db.delete_progress(rid)


class AttemptsTab(BaseTab):
    name = "Quiz Attempts"
    form_title = "Record a quiz attempt (INSERT)"
    list_title = "Quiz attempts (VIEW)"
    noun = "quiz attempt"
    delete_note = "\n\nIts question responses are deleted too (ON DELETE CASCADE)."
    select_sql = ("SELECT a.attempt_id, l.name AS learner, q.title AS quiz, a.attempt_no, "
                  "CONCAT(a.score, ' / ', q.max_score) AS score, a.attempt_date FROM attempt a "
                  "JOIN enrolment e ON e.enrolment_id = a.enrolment_id JOIN learner l ON l.learner_id = e.learner_id "
                  "JOIN quiz q ON q.quiz_id = a.quiz_id ORDER BY a.attempt_id DESC")

    def build_form(self, f):
        self.enrol = ttk.Combobox(f, state="readonly", width=40)
        self.quiz = ttk.Combobox(f, state="readonly", width=24)
        self.score = ttk.Spinbox(f, from_=0, to=100, width=6)
        self.score.set(0)
        self.enrol.bind("<<ComboboxSelected>>", lambda e: (self.quiz.set(""), self.load_quizzes()))
        self.grid_row(f, [("Enrolment", self.enrol), ("Quiz", self.quiz), ("Score", self.score)])
        ttk.Button(f, text="Record attempt", style="Accent.TButton", command=self.add).grid(row=0, column=6)

    def reload_choices(self):
        set_choices(self.enrol, self.db.query(
            "SELECT e.enrolment_id, CONCAT(l.name, ' / ', c.title) FROM enrolment e "
            "JOIN learner l ON l.learner_id = e.learner_id JOIN course c ON c.course_id = e.course_id "
            "WHERE e.status <> 'Dropped' ORDER BY e.enrolment_id")[1])
        self.load_quizzes()

    def load_quizzes(self):
        if not self.enrol.get():
            self.quiz["values"] = []
            return
        set_choices(self.quiz, self.db.query(
            "SELECT quiz_id, title FROM quiz WHERE course_id = "
            "(SELECT course_id FROM enrolment WHERE enrolment_id = %s)", (cid(self.enrol),))[1])

    def add(self):
        try:
            eid, qid, score = cid(self.enrol), cid(self.quiz), int(self.score.get())
        except ValueError:
            messagebox.showwarning("Check input", "Choose an enrolment, a quiz and a whole-number score.")
            return
        self.app.run_action("INSERT quiz attempt", lambda: self.db.add_attempt(eid, qid, score))

    def delete_row(self, rid): self.db.delete_attempt(rid)


REPORTS = {
    "Learner progress": "SELECT enrolment_id, learner, course, status, progress_pct FROM v_learner_progress ORDER BY learner",
    "Course summary": ("SELECT c.course_id, c.title AS course, i.name AS instructor, COUNT(e.enrolment_id) AS enrolled, "
                       "COALESCE(SUM(e.status = 'Completed'), 0) AS completed FROM course c "
                       "JOIN instructor i ON i.instructor_id = c.instructor_id "
                       "LEFT JOIN enrolment e ON e.course_id = c.course_id "
                       "GROUP BY c.course_id, c.title, i.name ORDER BY c.course_id"),
    "Certificate eligibility": ("SELECT e.enrolment_id, l.name AS learner, c.title AS course FROM enrolment e "
                                "JOIN learner l ON l.learner_id = e.learner_id JOIN course c ON c.course_id = e.course_id "
                                "WHERE e.status = 'Completed' AND NOT EXISTS "
                                "(SELECT 1 FROM certificate ce WHERE ce.enrolment_id = e.enrolment_id) "
                                "ORDER BY e.enrolment_id"),
}


class ReportsTab(BaseTab):
    name = "Reports"
    form_title = "Choose a report (SELECT with joins and aggregates)"
    list_title = "Report output"
    noun = "report row"

    @property
    def select_sql(self):
        return REPORTS[self.report.get()]

    def build_form(self, f):
        self.report = ttk.Combobox(f, state="readonly", values=list(REPORTS), width=28)
        self.report.set("Learner progress")
        self.report.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        self.grid_row(f, [("Report", self.report)])

    def build_bar(self, bar):
        ttk.Button(bar, text="Issue certificate", style="Accent.TButton", command=self.issue).pack(side="right")
        ttk.Button(bar, text="Refresh", command=self.app.refresh_all).pack(side="right", padx=6)

    def issue(self):
        if self.report.get() != "Certificate eligibility":
            messagebox.showinfo("Certificate", "Open the 'Certificate eligibility' report and select a row.")
            return
        try:
            rid = self.selected_id()
        except ValueError as e:
            messagebox.showinfo("Certificate", str(e))
            return
        self.app.run_action(f"INSERT certificate for enrolment #{rid}", lambda: self.db.issue_certificate(rid))


class BrowserTab(BaseTab):
    name = "Database Browser"
    form_title = "Look at any table directly in MySQL (SELECT *)"
    list_title = "Table contents (newest first)"

    @property
    def select_sql(self):
        t = self.table.get()
        return f"SELECT * FROM {t} ORDER BY 1 DESC LIMIT 300"

    def build_form(self, f):
        self.table = ttk.Combobox(f, state="readonly", values=dbm.TABLES, width=22)
        self.table.set("enrolment")
        self.table.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        self.info = ttk.Label(f, foreground=GR)
        self.grid_row(f, [("Table", self.table), ("", self.info)])

    def build_bar(self, bar):
        ttk.Button(bar, text="Refresh", command=self.app.refresh_all).pack(side="right")

    def refresh(self):
        super().refresh()
        n = self.db.query(f"SELECT COUNT(*) FROM {self.table.get()}")[1][0][0]
        self.info.config(text=f"{n} rows in {self.table.get()}")


# ------------------------------------------------------------------ main window
class App(tk.Tk):
    def __init__(self, database):
        super().__init__()
        self.db = database
        self.title("Online Course Learning Progress Management System")
        self.geometry("1180x780")
        self.minsize(980, 680)
        self.configure(bg=BG)
        self.style_setup()

        head = ttk.Frame(self, padding=(14, 10))
        head.pack(fill="x")
        ttk.Label(head, text="Online Course Learning Progress Management", font=("TkDefaultFont", 16, "bold"),
                  foreground=TEAL).pack(side="left")
        cfg = dbm.CONFIG
        ttk.Label(head, text=f"Connected to MySQL  {cfg['database']} @ {cfg['host']}", foreground=GR).pack(side="right")

        logbox = ttk.LabelFrame(self, text="Database activity: SQL executed and row counts", padding=6)
        logbox.pack(side="bottom", fill="x", padx=14, pady=(0, 12))
        self.logtext = tk.Text(logbox, height=9, bg=WH, fg=DK, relief="flat", wrap="word",
                               font=("Courier", 10), state="disabled")
        self.logtext.pack(fill="x")
        self.logtext.tag_config("head", foreground=TEAL, font=("Courier", 10, "bold"))
        self.logtext.tag_config("bad", foreground=RED, font=("Courier", 10, "bold"))
        self.logtext.tag_config("count", foreground="#B45309")

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        self.tabs = [cls(self.nb, self) for cls in
                     (EnrolmentsTab, LearnersTab, CoursesTab, ProgressTab, AttemptsTab, ReportsTab, BrowserTab)]
        for t in self.tabs:
            self.nb.add(t, text=t.name)
        self.refresh_all()
        self.say("Ready. Every change you make is committed to MySQL and shown here.", "head")

    def style_setup(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=DK)
        s.configure("TFrame", background=BG)
        s.configure("TLabel", background=BG)
        s.configure("TLabelframe", background=BG, bordercolor="#CFE5E0")
        s.configure("TLabelframe.Label", background=BG, foreground=TEAL, font=("TkDefaultFont", 10, "bold"))
        s.configure("TNotebook", background=BG, borderwidth=0)
        s.configure("TNotebook.Tab", padding=(14, 6), background="#E1EEEB", foreground=DK)
        s.map("TNotebook.Tab", background=[("selected", WH)], foreground=[("selected", TEAL)])
        s.configure("Treeview", rowheight=26, background=WH, fieldbackground=WH, bordercolor="#CFE5E0")
        s.map("Treeview", background=[("selected", "#CFE8E3")], foreground=[("selected", DK)])
        s.configure("Treeview.Heading", background=TEAL, foreground=WH, font=("TkDefaultFont", 10, "bold"), padding=5)
        s.map("Treeview.Heading", background=[("active", "#0B5F58")])
        s.configure("TButton", padding=(10, 4))
        s.configure("Accent.TButton", background=TEAL, foreground=WH)
        s.map("Accent.TButton", background=[("active", "#0B5F58")])
        s.configure("Danger.TButton", background=RED, foreground=WH)
        s.map("Danger.TButton", background=[("active", "#B91C1C")])

    # ---- log ----
    def say(self, text, tag=None):
        self.logtext.config(state="normal")
        self.logtext.insert("end", text + "\n", tag)
        self.logtext.see("end")
        self.logtext.config(state="disabled")

    def run_action(self, label, fn):
        before = self.db.counts()
        self.db.log.clear()
        stamp = datetime.now().strftime("%H:%M:%S")
        try:
            fn()
        except ValueError as e:
            messagebox.showwarning("Not allowed", str(e))
            return False
        except Error as e:
            self.say(f"[{stamp}] {label}: REJECTED by MySQL (rolled back)", "bad")
            messagebox.showerror("Database error", dbm.friendly(e))
            return False
        after = self.db.counts()
        self.say(f"[{stamp}] {label}", "head")
        for sql, n in self.db.log:
            self.say(f"  SQL: {sql}   ->  {n} row(s)")
        changes = [f"{t}: {before[t]} -> {after[t]}" for t in dbm.TABLES if before[t] != after[t]]
        self.say("  Row counts  " + (",  ".join(changes) if changes else "no change in row counts"), "count")
        self.refresh_all()
        return True

    def refresh_all(self):
        for t in self.tabs:
            t.refresh()


def main():
    try:
        database = dbm.Db()
    except Error as e:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Cannot connect to MySQL",
                             f"{e}\n\nCheck the password and database name in db.py, "
                             "and make sure MySQL is running and schema.sql has been executed.")
        return
    App(database).mainloop()


if __name__ == "__main__":
    main()
