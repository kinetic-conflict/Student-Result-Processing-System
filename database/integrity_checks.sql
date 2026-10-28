-- Student Result Processing System - Data Integrity Checks
-- READ ONLY: every statement here is a SELECT. Safe to run on a database that holds real records.
--
-- Run it from the MySQL prompt or Workbench:  source database/integrity_checks.sql;
-- Each check returns one row per problem, in a column called `problem`, and no rows when all is well.
-- Rows that start with "Review:" are questions, not errors: they can be legitimate (for example a
-- student who has since moved to the next semester) and only an administrator can say.

USE student_result_db;

-- 1. The assessment components exist.
SELECT 'No assessment components are defined' AS problem
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM assessments);

-- 2. The weights add up to exactly 100, otherwise totals and grades are on the wrong scale.
SELECT CONCAT('Assessment weights total ', SUM(weight_percentage), ', not 100') AS problem
FROM assessments
HAVING SUM(weight_percentage) <> 100;

-- 3. No assessment mark is above its component's maximum (possible if a maximum was lowered by hand).
SELECT CONCAT('Assessment mark above its maximum: ', s.registration_number, ' ', sub.subject_code, ' ',
              a.assessment_code, ' = ', am.marks_obtained, ' (maximum ', a.maximum_marks, ')') AS problem
FROM assessment_marks am
JOIN students s ON s.student_id = am.student_id
JOIN subjects sub ON sub.subject_id = am.subject_id
JOIN assessments a ON a.assessment_id = am.assessment_id
WHERE am.marks_obtained > a.maximum_marks;

-- 4. No examination mark is outside 0..maximum (the CHECK constraints stop this on MySQL 8.0.16+).
SELECT CONCAT('Examination mark outside its range: ', s.registration_number, ' ', sub.subject_code, ' = ',
              m.marks_obtained, ' / ', m.maximum_marks) AS problem
FROM marks m
JOIN students s ON s.student_id = m.student_id
JOIN subjects sub ON sub.subject_id = m.subject_id
WHERE m.marks_obtained < 0 OR m.maximum_marks <= 0 OR m.marks_obtained > m.maximum_marks;

-- 5. The same examination is not listed twice (marks entered against the copy would be split).
SELECT CONCAT('Duplicate examination: ', MIN(exam_name), ' ', academic_year, ' semester ', semester,
              ' (', COUNT(*), ' rows)') AS problem
FROM examinations
GROUP BY exam_name, academic_year, semester
HAVING COUNT(*) > 1;

-- 6. Review: an examination mark whose examination and subject are in different semesters.
SELECT CONCAT('Review: ', s.registration_number, ' has a mark in a semester ', e.semester, ' examination (',
              e.exam_name, ', ', e.academic_year, ') for ', sub.subject_code, ', a semester ', sub.semester,
              ' subject') AS problem
FROM marks m
JOIN students s ON s.student_id = m.student_id
JOIN subjects sub ON sub.subject_id = m.subject_id
JOIN examinations e ON e.exam_id = m.exam_id
WHERE e.semester <> sub.semester;

-- 7. Review: assessment marks for a subject outside the student's current semester.
SELECT DISTINCT CONCAT('Review: ', s.registration_number, ' (semester ', s.semester,
                       ') has assessment marks for ', sub.subject_code, ', a semester ', sub.semester,
                       ' subject') AS problem
FROM assessment_marks am
JOIN students s ON s.student_id = am.student_id
JOIN subjects sub ON sub.subject_id = am.subject_id
WHERE s.semester <> sub.semester;

SELECT 'Checks finished. Every section above that returned rows needs a look.' AS message;
