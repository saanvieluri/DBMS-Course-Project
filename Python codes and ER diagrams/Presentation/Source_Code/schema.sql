-- Online Course Learning Progress Management System
-- Run:  mysql -u root -p < schema.sql
DROP DATABASE IF EXISTS course_progress;
CREATE DATABASE course_progress CHARACTER SET utf8mb4;
USE course_progress;

CREATE TABLE instructor (
  instructor_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(80) NOT NULL,
  email VARCHAR(100) NOT NULL UNIQUE,
  department VARCHAR(60) NOT NULL
);
CREATE TABLE learner (
  learner_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(80) NOT NULL,
  email VARCHAR(100) NOT NULL UNIQUE,
  joined_date DATE NOT NULL
);
CREATE TABLE course (
  course_id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(120) NOT NULL,
  level VARCHAR(15) NOT NULL DEFAULT 'Beginner',
  instructor_id INT NOT NULL,
  CONSTRAINT chk_course_level CHECK (level IN ('Beginner','Intermediate','Advanced')),
  FOREIGN KEY (instructor_id) REFERENCES instructor(instructor_id)
);
CREATE TABLE module (
  module_id INT AUTO_INCREMENT PRIMARY KEY,
  course_id INT NOT NULL,
  title VARCHAR(120) NOT NULL,
  seq_no INT NOT NULL,
  UNIQUE (course_id, seq_no),
  FOREIGN KEY (course_id) REFERENCES course(course_id)
);
CREATE TABLE lesson (
  lesson_id INT AUTO_INCREMENT PRIMARY KEY,
  module_id INT NOT NULL,
  title VARCHAR(120) NOT NULL,
  duration_min INT NOT NULL DEFAULT 30,
  CONSTRAINT chk_lesson_duration CHECK (duration_min > 0),
  FOREIGN KEY (module_id) REFERENCES module(module_id)
);
CREATE TABLE enrolment (
  enrolment_id INT AUTO_INCREMENT PRIMARY KEY,
  learner_id INT NOT NULL,
  course_id INT NOT NULL,
  status VARCHAR(12) NOT NULL DEFAULT 'Active',
  enrolled_on DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (learner_id, course_id),
  CONSTRAINT chk_enrol_status CHECK (status IN ('Active','Completed','Dropped')),
  FOREIGN KEY (learner_id) REFERENCES learner(learner_id),
  FOREIGN KEY (course_id) REFERENCES course(course_id)
);
CREATE TABLE lesson_progress (
  progress_id INT AUTO_INCREMENT PRIMARY KEY,
  enrolment_id INT NOT NULL,
  lesson_id INT NOT NULL,
  completion_pct INT NOT NULL DEFAULT 0,
  UNIQUE (enrolment_id, lesson_id),
  CONSTRAINT chk_progress_pct CHECK (completion_pct BETWEEN 0 AND 100),
  FOREIGN KEY (enrolment_id) REFERENCES enrolment(enrolment_id) ON DELETE CASCADE,
  FOREIGN KEY (lesson_id) REFERENCES lesson(lesson_id)
);
CREATE TABLE quiz (
  quiz_id INT AUTO_INCREMENT PRIMARY KEY,
  course_id INT NOT NULL,
  title VARCHAR(120) NOT NULL,
  max_score INT NOT NULL DEFAULT 10,
  max_attempts INT NOT NULL DEFAULT 3,
  CONSTRAINT chk_quiz_limits CHECK (max_score > 0 AND max_attempts > 0),
  FOREIGN KEY (course_id) REFERENCES course(course_id)
);
CREATE TABLE question (
  question_id INT AUTO_INCREMENT PRIMARY KEY,
  quiz_id INT NOT NULL,
  question_text VARCHAR(255) NOT NULL,
  correct_option CHAR(1) NOT NULL,
  marks INT NOT NULL DEFAULT 5,
  CONSTRAINT chk_question_option CHECK (correct_option IN ('A','B','C','D')),
  FOREIGN KEY (quiz_id) REFERENCES quiz(quiz_id)
);
CREATE TABLE attempt (
  attempt_id INT AUTO_INCREMENT PRIMARY KEY,
  enrolment_id INT NOT NULL,
  quiz_id INT NOT NULL,
  attempt_no INT NOT NULL DEFAULT 1,
  score INT NOT NULL DEFAULT 0,
  attempt_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (enrolment_id, quiz_id, attempt_no),
  CONSTRAINT chk_attempt_score CHECK (score >= 0),
  FOREIGN KEY (enrolment_id) REFERENCES enrolment(enrolment_id) ON DELETE CASCADE,
  FOREIGN KEY (quiz_id) REFERENCES quiz(quiz_id)
);
CREATE TABLE response (
  response_id INT AUTO_INCREMENT PRIMARY KEY,
  attempt_id INT NOT NULL,
  question_id INT NOT NULL,
  chosen_option CHAR(1) NOT NULL,
  is_correct TINYINT(1) NOT NULL DEFAULT 0,
  UNIQUE (attempt_id, question_id),
  CONSTRAINT chk_response_option CHECK (chosen_option IN ('A','B','C','D')),
  FOREIGN KEY (attempt_id) REFERENCES attempt(attempt_id) ON DELETE CASCADE,
  FOREIGN KEY (question_id) REFERENCES question(question_id)
);
CREATE TABLE certificate (
  certificate_id INT AUTO_INCREMENT PRIMARY KEY,
  enrolment_id INT NOT NULL UNIQUE,
  issue_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (enrolment_id) REFERENCES enrolment(enrolment_id) ON DELETE CASCADE
);
CREATE TABLE feedback (
  feedback_id INT AUTO_INCREMENT PRIMARY KEY,
  enrolment_id INT NOT NULL,
  rating INT NOT NULL,
  comments VARCHAR(255),
  CONSTRAINT chk_feedback_rating CHECK (rating BETWEEN 1 AND 5),
  FOREIGN KEY (enrolment_id) REFERENCES enrolment(enrolment_id) ON DELETE CASCADE
);

-- Indexes on frequently searched columns
CREATE INDEX idx_learner_name ON learner(name);
CREATE INDEX idx_course_title ON course(title);
CREATE INDEX idx_progress_lesson ON lesson_progress(lesson_id);
CREATE INDEX idx_attempt_quiz ON attempt(quiz_id);

-- View: progress of every enrolment (average over ALL lessons of the course)
CREATE VIEW v_learner_progress AS
SELECT e.enrolment_id, l.name AS learner, c.title AS course, e.status,
       ROUND(COALESCE(SUM(lp.completion_pct), 0) /
         (SELECT COUNT(*) FROM lesson ls JOIN module m ON m.module_id = ls.module_id
           WHERE m.course_id = c.course_id), 1) AS progress_pct
FROM enrolment e
JOIN learner l ON l.learner_id = e.learner_id
JOIN course c ON c.course_id = e.course_id
LEFT JOIN lesson_progress lp ON lp.enrolment_id = e.enrolment_id
GROUP BY e.enrolment_id, l.name, c.course_id, c.title, e.status;

-- ---------------- Sample data (5+ rows per table) ----------------
INSERT INTO instructor (name, email, department) VALUES
  ('Dr. Ananya Rao', 'ananya.rao@university.edu', 'Computer Science'),
  ('Prof. Vikram Mehta', 'vikram.mehta@university.edu', 'Mathematics'),
  ('Dr. Kavita Nair', 'kavita.nair@university.edu', 'Design'),
  ('Prof. Suresh Kulkarni', 'suresh.k@university.edu', 'Computer Science'),
  ('Dr. Farah Khan', 'farah.khan@university.edu', 'Statistics');
INSERT INTO learner (name, email, joined_date) VALUES
  ('Anita Sharma', 'anita.sharma@mail.com', '2026-06-12'),
  ('Rahul Verma', 'rahul.verma@mail.com', '2026-06-15'),
  ('Meera Iyer', 'meera.iyer@mail.com', '2026-06-20'),
  ('Karan Singh', 'karan.singh@mail.com', '2026-07-02'),
  ('Priya Reddy', 'priya.reddy@mail.com', '2026-07-10'),
  ('Arjun Patel', 'arjun.patel@mail.com', '2026-07-18');
INSERT INTO course (title, level, instructor_id) VALUES
  ('Python Basics', 'Beginner', 1),
  ('Data Science Introduction', 'Intermediate', 2),
  ('Web Design Fundamentals', 'Beginner', 3),
  ('Java Object-Oriented Programming', 'Intermediate', 4),
  ('Statistics for Engineers', 'Advanced', 5);
INSERT INTO module (course_id, title, seq_no) VALUES
  (1, 'Getting Started', 1),
  (1, 'Control Flow and Functions', 2),
  (2, 'Data Handling', 1),
  (2, 'Modelling Basics', 2),
  (3, 'HTML and CSS', 1),
  (3, 'Layout and Design', 2),
  (4, 'Classes and Objects', 1),
  (4, 'Inheritance and Interfaces', 2),
  (5, 'Probability', 1),
  (5, 'Inference', 2);
INSERT INTO lesson (module_id, title, duration_min) VALUES
  (1, 'Installing Python', 20),
  (1, 'Variables and Types', 25),
  (2, 'Loops', 30),
  (2, 'Writing Functions', 35),
  (3, 'Lists and Dicts', 20),
  (3, 'Reading CSV Files', 25),
  (4, 'Linear Regression', 30),
  (4, 'Model Evaluation', 35),
  (5, 'HTML Structure', 20),
  (5, 'Forms', 25),
  (6, 'CSS Selectors', 30),
  (6, 'Flexbox and Grid', 35),
  (7, 'Defining Classes', 20),
  (7, 'Constructors', 25),
  (8, 'Inheritance', 30),
  (8, 'Interfaces', 35),
  (9, 'Random Variables', 20),
  (9, 'Distributions', 25),
  (10, 'Hypothesis Tests', 30),
  (10, 'Confidence Intervals', 35);
INSERT INTO enrolment (learner_id, course_id, status, enrolled_on) VALUES
  (1, 1, 'Completed', '2026-07-01 10:00:00'),
  (2, 1, 'Active', '2026-07-03 10:00:00'),
  (3, 2, 'Completed', '2026-07-05 10:00:00'),
  (4, 3, 'Completed', '2026-07-08 10:00:00'),
  (5, 1, 'Dropped', '2026-07-12 10:00:00'),
  (6, 4, 'Completed', '2026-07-20 10:00:00'),
  (1, 2, 'Active', '2026-08-01 10:00:00'),
  (2, 3, 'Completed', '2026-08-04 10:00:00'),
  (4, 1, 'Completed', '2026-08-10 10:00:00');
INSERT INTO lesson_progress (enrolment_id, lesson_id, completion_pct) VALUES
  (1, 1, 100),
  (1, 2, 100),
  (1, 3, 100),
  (1, 4, 100),
  (2, 1, 100),
  (2, 2, 100),
  (2, 3, 50),
  (2, 4, 0),
  (3, 5, 100),
  (3, 6, 100),
  (3, 7, 100),
  (3, 8, 100),
  (4, 9, 100),
  (4, 10, 100),
  (4, 11, 100),
  (4, 12, 100),
  (5, 1, 100),
  (5, 2, 40),
  (5, 3, 0),
  (5, 4, 0),
  (6, 13, 100),
  (6, 14, 100),
  (6, 15, 100),
  (6, 16, 100),
  (7, 5, 100),
  (7, 6, 60),
  (7, 7, 0),
  (7, 8, 0),
  (8, 9, 100),
  (8, 10, 100),
  (8, 11, 100),
  (8, 12, 100),
  (9, 1, 100),
  (9, 2, 100),
  (9, 3, 100),
  (9, 4, 100);
INSERT INTO quiz (course_id, title, max_score, max_attempts) VALUES
  (1, 'Quiz: Python Basics', 10, 3),
  (2, 'Quiz: Data Science', 10, 3),
  (3, 'Quiz: Web Design', 10, 3),
  (4, 'Quiz: Java OOP', 10, 3),
  (5, 'Quiz: Statistics', 10, 3);
INSERT INTO question (quiz_id, question_text, correct_option, marks) VALUES
  (1, 'Which keyword defines a function in Python?', 'B', 5),
  (1, 'Which symbol starts a comment in Python?', 'A', 5),
  (2, 'Which library is used for data frames?', 'C', 5),
  (2, 'What does CSV stand for?', 'A', 5),
  (3, 'Which tag creates a hyperlink?', 'D', 5),
  (3, 'Which CSS property sets text colour?', 'B', 5),
  (4, 'Which keyword creates a subclass in Java?', 'A', 5),
  (4, 'Which keyword creates an object in Java?', 'C', 5),
  (5, 'What is the mean of 2, 4, 6?', 'B', 5),
  (5, 'A p-value below 0.05 usually means?', 'D', 5);
INSERT INTO attempt (enrolment_id, quiz_id, attempt_no, score, attempt_date) VALUES
  (1, 1, 1, 10, '2026-07-10 11:00:00'),
  (2, 1, 1, 5, '2026-07-12 11:00:00'),
  (2, 1, 2, 10, '2026-07-14 11:00:00'),
  (3, 2, 1, 5, '2026-07-20 11:00:00'),
  (4, 3, 1, 10, '2026-07-25 11:00:00'),
  (5, 1, 1, 0, '2026-07-22 11:00:00'),
  (6, 4, 1, 5, '2026-08-05 11:00:00');
INSERT INTO response (attempt_id, question_id, chosen_option, is_correct) VALUES
  (1, 1, 'B', 1),
  (1, 2, 'A', 1),
  (2, 1, 'B', 1),
  (2, 2, 'C', 0),
  (3, 1, 'B', 1),
  (3, 2, 'A', 1),
  (4, 3, 'C', 1),
  (4, 4, 'B', 0);
INSERT INTO certificate (enrolment_id, issue_date) VALUES
  (1, '2026-07-30 10:00:00'),
  (3, '2026-08-10 10:00:00'),
  (4, '2026-08-12 10:00:00'),
  (6, '2026-08-25 10:00:00'),
  (9, '2026-08-30 10:00:00');
INSERT INTO feedback (enrolment_id, rating, comments) VALUES
  (1, 5, 'Clear and well paced'),
  (3, 4, 'Good practical examples'),
  (4, 5, 'Loved the design tasks'),
  (6, 4, 'Challenging but useful'),
  (9, 3, 'Needs more exercises');
