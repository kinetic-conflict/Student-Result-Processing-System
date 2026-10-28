-- Student Result Processing System - Sample Data
-- SYNTHETIC DEMONSTRATION DATA. Every person, number and email below is made up.
-- Do not load this into a database that holds real student records.
--
-- Execute order: schema.sql -> seed.sql
-- Safe to run again: rows are matched on their natural keys and skipped if present.

USE student_result_db;

-- Sample students (emails use the reserved ".example" domain)
INSERT IGNORE INTO students (registration_number, full_name, email, department, semester, academic_year) VALUES
('2024CS001', 'Rahul Sharma', 'rahul.sharma@students.example', 'Computer Science', 3, '2024-2025'),
('2024CS002', 'Priya Patel', 'priya.patel@students.example', 'Computer Science', 3, '2024-2025'),
('2024CS003', 'Amit Kumar', 'amit.kumar@students.example', 'Computer Science', 3, '2024-2025'),
('2024CS004', 'Sneha Reddy', 'sneha.reddy@students.example', 'Computer Science', 3, '2024-2025'),
('2024CS005', 'Vikram Singh', 'vikram.singh@students.example', 'Computer Science', 3, '2024-2025'),
('2024IT001', 'Anjali Gupta', 'anjali.gupta@students.example', 'Information Technology', 3, '2024-2025'),
('2024IT002', 'Rohan Das', 'rohan.das@students.example', 'Information Technology', 3, '2024-2025'),
('2024ME001', 'Karan Joshi', 'karan.joshi@students.example', 'Mechanical Engineering', 3, '2024-2025');

-- Sample subjects
INSERT IGNORE INTO subjects (subject_code, subject_name, credits, semester) VALUES
('CS301', 'Data Structures and Algorithms', 4.0, 3),
('CS302', 'Database Management Systems', 4.0, 3),
('CS303', 'Operating Systems', 4.0, 3),
('CS304', 'Computer Networks', 3.0, 3),
('CS305', 'Web Technologies', 3.0, 3),
('IT301', 'Software Engineering', 4.0, 3),
('IT302', 'Data Mining', 3.0, 3),
('ME301', 'Thermodynamics', 4.0, 3);

-- Sample examinations (examinations have no unique key, so check before inserting)
INSERT INTO examinations (exam_name, academic_year, semester, exam_date)
SELECT v.exam_name, v.academic_year, v.semester, v.exam_date
FROM (
    SELECT 'Mid Semester Examination' AS exam_name, '2024-2025' AS academic_year, 3 AS semester, DATE '2024-10-15' AS exam_date
    UNION ALL SELECT 'End Semester Examination', '2024-2025', 3, DATE '2024-12-20'
    UNION ALL SELECT 'Internal Assessment 1', '2024-2025', 3, DATE '2024-09-10'
    UNION ALL SELECT 'Internal Assessment 2', '2024-2025', 3, DATE '2024-11-15'
) AS v
WHERE NOT EXISTS (
    SELECT 1 FROM examinations e
    WHERE e.exam_name = v.exam_name AND e.academic_year = v.academic_year AND e.semester = v.semester
);

-- Sample marks, all in the End Semester Examination, all out of 100.
-- Reproducible example for 2024CS001: 85 + 76 + 92 + 78 + 88 = 419 / 500 = 83.8%.
-- 2024CS003's lowest mark is 45/100, which is still a pass (the pass mark is 40%).
-- 2024CS004 has only three of five subjects entered, which makes the record incomplete.
INSERT IGNORE INTO marks (student_id, subject_id, exam_id, marks_obtained, maximum_marks)
SELECT s.student_id, sub.subject_id, e.exam_id, v.marks_obtained, 100.00
FROM (
    SELECT '2024CS001' AS registration_number, 'CS301' AS subject_code, 85.00 AS marks_obtained
    UNION ALL SELECT '2024CS001', 'CS302', 76.00
    UNION ALL SELECT '2024CS001', 'CS303', 92.00
    UNION ALL SELECT '2024CS001', 'CS304', 78.00
    UNION ALL SELECT '2024CS001', 'CS305', 88.00
    UNION ALL SELECT '2024CS002', 'CS301', 92.00
    UNION ALL SELECT '2024CS002', 'CS302', 88.00
    UNION ALL SELECT '2024CS002', 'CS303', 95.00
    UNION ALL SELECT '2024CS002', 'CS304', 90.00
    UNION ALL SELECT '2024CS002', 'CS305', 85.00
    UNION ALL SELECT '2024CS003', 'CS301', 45.00
    UNION ALL SELECT '2024CS003', 'CS302', 72.00
    UNION ALL SELECT '2024CS003', 'CS303', 68.00
    UNION ALL SELECT '2024CS003', 'CS304', 55.00
    UNION ALL SELECT '2024CS003', 'CS305', 62.00
    UNION ALL SELECT '2024CS004', 'CS301', 82.00
    UNION ALL SELECT '2024CS004', 'CS302', 79.00
    UNION ALL SELECT '2024CS004', 'CS303', 88.00
    UNION ALL SELECT '2024CS005', 'CS301', 75.00
    UNION ALL SELECT '2024CS005', 'CS302', 82.00
    UNION ALL SELECT '2024CS005', 'CS303', 70.00
    UNION ALL SELECT '2024CS005', 'CS304', 68.00
    UNION ALL SELECT '2024CS005', 'CS305', 72.00
    UNION ALL SELECT '2024IT001', 'IT301', 85.00
    UNION ALL SELECT '2024IT001', 'IT302', 78.00
    UNION ALL SELECT '2024IT002', 'IT301', 90.00
    UNION ALL SELECT '2024IT002', 'IT302', 85.00
    UNION ALL SELECT '2024ME001', 'ME301', 72.00
) AS v
JOIN students s ON s.registration_number = v.registration_number
JOIN subjects sub ON sub.subject_code = v.subject_code
JOIN examinations e ON e.exam_name = 'End Semester Examination'
                   AND e.academic_year = '2024-2025' AND e.semester = 3;

-- Display summary
SELECT 'Sample data ready.' AS message;
SELECT COUNT(*) AS total_students FROM students;
SELECT COUNT(*) AS total_subjects FROM subjects;
SELECT COUNT(*) AS total_examinations FROM examinations;
SELECT COUNT(*) AS total_marks FROM marks;
