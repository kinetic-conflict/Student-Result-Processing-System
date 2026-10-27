-- Student Result Processing System - Important SQL Queries
-- This file contains key SQL queries used in the application
-- Reference these queries during Assessment 9 demonstration

USE student_result_db;

-- ============================================
-- INSERT OPERATIONS
-- ============================================

-- Insert a new student
INSERT INTO students (registration_number, full_name, email, department, semester, academic_year)
VALUES ('2024CS999', 'Test Student', 'test@student.edu', 'Computer Science', 3, '2024-2025');

-- Insert a new subject
INSERT INTO subjects (subject_code, subject_name, credits, semester)
VALUES ('CS399', 'Test Subject', 3.0, 3);

-- Insert a new examination
INSERT INTO examinations (exam_name, academic_year, semester, exam_date)
VALUES ('Test Examination', '2024-2025', 3, '2024-12-25');

-- Insert marks for a student
INSERT INTO marks (student_id, subject_id, exam_id, marks_obtained, maximum_marks)
VALUES (1, 1, 2, 85.00, 100.00);

-- ============================================
-- SELECT OPERATIONS
-- ============================================

-- Select all students
SELECT * FROM students;

-- Select a specific student by registration number
SELECT * FROM students WHERE registration_number = '2024CS001';

-- Select all subjects
SELECT * FROM subjects;

-- Select subjects for a specific semester
SELECT * FROM subjects WHERE semester = 3;

-- Select all examinations
SELECT * FROM examinations;

-- Select all marks with student, subject, and exam details (JOIN)
SELECT 
    m.mark_id,
    s.registration_number,
    s.full_name,
    sub.subject_code,
    sub.subject_name,
    e.exam_name,
    m.marks_obtained,
    m.maximum_marks,
    (m.marks_obtained / m.maximum_marks * 100) AS percentage
FROM marks m
JOIN students s ON m.student_id = s.student_id
JOIN subjects sub ON m.subject_id = sub.subject_id
JOIN examinations e ON m.exam_id = e.exam_id;

-- ============================================
-- UPDATE OPERATIONS
-- ============================================

-- Update student information
UPDATE students 
SET email = 'newemail@vit.edu' 
WHERE student_id = 1;

-- Update marks
UPDATE marks 
SET marks_obtained = 90.00 
WHERE mark_id = 1;

-- ============================================
-- DELETE OPERATIONS
-- ============================================

-- Delete a marks record (safe test record)
DELETE FROM marks WHERE mark_id = 999;

-- Delete a student (cascade will delete related marks)
DELETE FROM students WHERE student_id = 999;

-- ============================================
-- MULTI-TABLE JOIN
-- ============================================

-- Complete student result with all details
SELECT 
    s.student_id,
    s.registration_number,
    s.full_name,
    s.department,
    s.semester,
    sub.subject_code,
    sub.subject_name,
    sub.credits,
    e.exam_name,
    e.academic_year,
    m.marks_obtained,
    m.maximum_marks,
    (m.marks_obtained / m.maximum_marks * 100) AS percentage
FROM students s
JOIN marks m ON s.student_id = m.student_id
JOIN subjects sub ON m.subject_id = sub.subject_id
JOIN examinations e ON m.exam_id = e.exam_id
ORDER BY s.registration_number, sub.subject_code;

-- ============================================
-- WHERE AND ORDER BY CLAUSES
-- ============================================

-- Filter by registration number
SELECT * FROM marks 
WHERE student_id = (SELECT student_id FROM students WHERE registration_number = '2024CS001');

-- Filter by examination
SELECT 
    s.registration_number,
    s.full_name,
    sub.subject_name,
    m.marks_obtained,
    m.maximum_marks
FROM marks m
JOIN students s ON m.student_id = s.student_id
JOIN subjects sub ON m.subject_id = sub.subject_id
WHERE m.exam_id = 2;

-- Filter by semester
SELECT 
    s.registration_number,
    s.full_name,
    s.semester,
    sub.subject_name,
    m.marks_obtained
FROM marks m
JOIN students s ON m.student_id = s.student_id
JOIN subjects sub ON m.subject_id = sub.subject_id
WHERE s.semester = 3;

-- Filter by academic year
SELECT 
    e.exam_name,
    e.academic_year,
    COUNT(DISTINCT m.student_id) AS total_students,
    AVG(m.marks_obtained / m.maximum_marks * 100) AS average_percentage
FROM marks m
JOIN examinations e ON m.exam_id = e.exam_id
WHERE e.academic_year = '2024-2025'
GROUP BY e.exam_id, e.exam_name, e.academic_year;

-- Sort by marks obtained (descending)
SELECT 
    s.registration_number,
    s.full_name,
    sub.subject_name,
    m.marks_obtained,
    (m.marks_obtained / m.maximum_marks * 100) AS percentage
FROM marks m
JOIN students s ON m.student_id = s.student_id
JOIN subjects sub ON m.subject_id = sub.subject_id
WHERE m.exam_id = 2
ORDER BY m.marks_obtained DESC;

-- Sort by percentage (ascending)
SELECT 
    s.registration_number,
    s.full_name,
    sub.subject_name,
    (m.marks_obtained / m.maximum_marks * 100) AS percentage
FROM marks m
JOIN students s ON m.student_id = s.student_id
JOIN subjects sub ON m.subject_id = sub.subject_id
WHERE m.exam_id = 2
ORDER BY percentage ASC;

-- ============================================
-- GROUP BY AND AGGREGATE FUNCTIONS
-- ============================================

-- Count total students
SELECT COUNT(*) AS total_students FROM students;

-- Count total subjects
SELECT COUNT(*) AS total_subjects FROM subjects;

-- Count total examinations
SELECT COUNT(*) AS total_examinations FROM examinations;

-- Count total marks records
SELECT COUNT(*) AS total_marks FROM marks;

-- SUM - Total marks obtained by a student in an exam
SELECT 
    s.registration_number,
    s.full_name,
    e.exam_name,
    SUM(m.marks_obtained) AS total_obtained,
    SUM(m.maximum_marks) AS total_maximum,
    (SUM(m.marks_obtained) / SUM(m.maximum_marks) * 100) AS overall_percentage
FROM marks m
JOIN students s ON m.student_id = s.student_id
JOIN examinations e ON m.exam_id = e.exam_id
WHERE s.registration_number = '2024CS001' AND e.exam_id = 2
GROUP BY s.student_id, s.registration_number, s.full_name, e.exam_id, e.exam_name;

-- AVG - Average marks per subject
SELECT 
    sub.subject_code,
    sub.subject_name,
    AVG(m.marks_obtained) AS average_marks,
    AVG(m.marks_obtained / m.maximum_marks * 100) AS average_percentage
FROM marks m
JOIN subjects sub ON m.subject_id = sub.subject_id
GROUP BY sub.subject_id, sub.subject_code, sub.subject_name
ORDER BY average_percentage DESC;

-- MIN - Lowest marks in each subject
SELECT 
    sub.subject_code,
    sub.subject_name,
    MIN(m.marks_obtained) AS lowest_marks
FROM marks m
JOIN subjects sub ON m.subject_id = sub.subject_id
GROUP BY sub.subject_id, sub.subject_code, sub.subject_name;

-- MAX - Highest marks in each subject
SELECT 
    sub.subject_code,
    sub.subject_name,
    MAX(m.marks_obtained) AS highest_marks
FROM marks m
JOIN subjects sub ON m.subject_id = sub.subject_id
GROUP BY sub.subject_id, sub.subject_code, sub.subject_name;

-- Student-wise total and average
SELECT 
    s.registration_number,
    s.full_name,
    COUNT(m.mark_id) AS subject_count,
    SUM(m.marks_obtained) AS total_obtained,
    SUM(m.maximum_marks) AS total_maximum,
    (SUM(m.marks_obtained) / SUM(m.maximum_marks) * 100) AS overall_percentage
FROM marks m
JOIN students s ON m.student_id = s.student_id
GROUP BY s.student_id, s.registration_number, s.full_name
ORDER BY overall_percentage DESC;

-- Examination-wise statistics
SELECT 
    e.exam_name,
    e.academic_year,
    COUNT(DISTINCT m.student_id) AS students_appeared,
    COUNT(m.mark_id) AS total_marks_entries,
    AVG(m.marks_obtained / m.maximum_marks * 100) AS average_percentage,
    MAX(m.marks_obtained / m.maximum_marks * 100) AS highest_percentage,
    MIN(m.marks_obtained / m.maximum_marks * 100) AS lowest_percentage
FROM marks m
JOIN examinations e ON m.exam_id = e.exam_id
GROUP BY e.exam_id, e.exam_name, e.academic_year;

-- ============================================
-- SUBQUERIES
-- ============================================

-- Students whose performance exceeds the average percentage
SELECT 
    s.registration_number,
    s.full_name,
    (SUM(m.marks_obtained) / SUM(m.maximum_marks) * 100) AS overall_percentage
FROM marks m
JOIN students s ON m.student_id = s.student_id
GROUP BY s.student_id, s.registration_number, s.full_name
HAVING (SUM(m.marks_obtained) / SUM(m.maximum_marks) * 100) > (
    SELECT AVG(marks_obtained / maximum_marks * 100) 
    FROM marks
)
ORDER BY overall_percentage DESC;

-- Top-performing students (above 85%)
SELECT 
    s.registration_number,
    s.full_name,
    (SUM(m.marks_obtained) / SUM(m.maximum_marks) * 100) AS overall_percentage
FROM marks m
JOIN students s ON m.student_id = s.student_id
GROUP BY s.student_id, s.registration_number, s.full_name
HAVING (SUM(m.marks_obtained) / SUM(m.maximum_marks) * 100) >= 85
ORDER BY overall_percentage DESC;

-- Students who failed (at least one subject below 40%)
SELECT DISTINCT
    s.registration_number,
    s.full_name
FROM marks m
JOIN students s ON m.student_id = s.student_id
WHERE (m.marks_obtained / m.maximum_marks * 100) < 40
ORDER BY s.registration_number;

-- Students with incomplete results (fewer subjects than expected)
-- This assumes each student should have 5 subjects
SELECT 
    s.registration_number,
    s.full_name,
    COUNT(m.mark_id) AS subjects_recorded
FROM students s
LEFT JOIN marks m ON s.student_id = m.student_id
GROUP BY s.student_id, s.registration_number, s.full_name
HAVING COUNT(m.mark_id) < 5
ORDER BY s.registration_number;

-- Subject-wise average compared to overall average
SELECT 
    sub.subject_code,
    sub.subject_name,
    AVG(m.marks_obtained / m.maximum_marks * 100) AS subject_average,
    (SELECT AVG(marks_obtained / maximum_marks * 100) FROM marks) AS overall_average,
    (AVG(m.marks_obtained / m.maximum_marks * 100) - (SELECT AVG(marks_obtained / maximum_marks * 100) FROM marks)) AS difference
FROM marks m
JOIN subjects sub ON m.subject_id = sub.subject_id
GROUP BY sub.subject_id, sub.subject_code, sub.subject_name
ORDER BY subject_average DESC;

-- ============================================
-- TRANSACTION EXAMPLE
-- ============================================

-- Example transaction: Insert marks for multiple subjects for a student
-- This should be executed as a transaction to ensure atomicity
-- START TRANSACTION;
-- INSERT INTO marks (student_id, subject_id, exam_id, marks_obtained, maximum_marks) VALUES (1, 1, 2, 85.00, 100.00);
-- INSERT INTO marks (student_id, subject_id, exam_id, marks_obtained, maximum_marks) VALUES (1, 2, 2, 76.00, 100.00);
-- INSERT INTO marks (student_id, subject_id, exam_id, marks_obtained, maximum_marks) VALUES (1, 3, 2, 92.00, 100.00);
-- COMMIT;
-- ROLLBACK; -- Use if any INSERT fails

-- ============================================
-- REPORT QUERIES
-- ============================================

-- Examination-wise result report
SELECT 
    e.exam_name,
    e.academic_year,
    e.semester,
    COUNT(DISTINCT m.student_id) AS total_students,
    COUNT(m.mark_id) AS total_subject_entries,
    AVG(m.marks_obtained / m.maximum_marks * 100) AS average_percentage,
    SUM(CASE WHEN (m.marks_obtained / m.maximum_marks * 100) >= 40 THEN 1 ELSE 0 END) AS passed_subjects,
    SUM(CASE WHEN (m.marks_obtained / m.maximum_marks * 100) < 40 THEN 1 ELSE 0 END) AS failed_subjects
FROM marks m
JOIN examinations e ON m.exam_id = e.exam_id
GROUP BY e.exam_id, e.exam_name, e.academic_year, e.semester;

-- Subject-wise performance report
SELECT 
    sub.subject_code,
    sub.subject_name,
    sub.credits,
    COUNT(m.mark_id) AS total_entries,
    AVG(m.marks_obtained) AS average_marks,
    AVG(m.marks_obtained / m.maximum_marks * 100) AS average_percentage,
    MAX(m.marks_obtained) AS highest_marks,
    MIN(m.marks_obtained) AS lowest_marks
FROM marks m
JOIN subjects sub ON m.subject_id = sub.subject_id
GROUP BY sub.subject_id, sub.subject_code, sub.subject_name, sub.credits
ORDER BY average_percentage DESC;

-- Pass percentage by examination
SELECT 
    e.exam_name,
    e.academic_year,
    COUNT(DISTINCT CASE WHEN (m.marks_obtained / m.maximum_marks * 100) >= 40 THEN m.student_id END) AS passed_students,
    COUNT(DISTINCT m.student_id) AS total_students,
    (COUNT(DISTINCT CASE WHEN (m.marks_obtained / m.maximum_marks * 100) >= 40 THEN m.student_id END) * 100.0 / COUNT(DISTINCT m.student_id)) AS pass_percentage
FROM marks m
JOIN examinations e ON m.exam_id = e.exam_id
GROUP BY e.exam_id, e.exam_name, e.academic_year;
