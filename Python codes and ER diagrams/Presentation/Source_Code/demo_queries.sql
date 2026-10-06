USE course_progress;

-- ===== SLIDE 7: SQL QUERIES (run each one separately: select it, press Ctrl+Enter) =====

-- Query 1: JOIN + AGGREGATE (average progress per learner per course)
SELECT l.name AS learner, c.title AS course,
       ROUND(AVG(lp.completion_pct), 1) AS progress
FROM learner l
JOIN enrolment e ON e.learner_id = l.learner_id
JOIN course c ON c.course_id = e.course_id
JOIN lesson_progress lp ON lp.enrolment_id = e.enrolment_id
GROUP BY l.name, c.title
ORDER BY l.name;

-- Query 2: AGGREGATE (learners per course, including courses with none)
SELECT c.title, COUNT(e.enrolment_id) AS learners
FROM course c
LEFT JOIN enrolment e ON e.course_id = c.course_id
GROUP BY c.title
ORDER BY learners DESC;

-- Query 3: NESTED query (learners who scored at least 5 out of 10 in a quiz)
SELECT name FROM learner
WHERE learner_id IN (
  SELECT learner_id FROM enrolment
  WHERE enrolment_id IN (SELECT enrolment_id FROM attempt WHERE score >= 5));

-- ===== SLIDE 9: TESTING (each of these SHOULD give an error) =====

-- Test 1: duplicate enrolment -> UNIQUE constraint
INSERT INTO enrolment (learner_id, course_id) VALUES (1, 1);

-- Test 2: progress above 100 -> CHECK constraint
UPDATE lesson_progress SET completion_pct = 120 WHERE progress_id = 1;

-- Test 3: delete a course that has modules/enrolments -> FOREIGN KEY
DELETE FROM course WHERE course_id = 1;

-- Test 4: delete a learner who is enrolled -> FOREIGN KEY
DELETE FROM learner WHERE learner_id = 1;
