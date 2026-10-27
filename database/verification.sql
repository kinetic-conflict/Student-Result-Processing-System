-- Student Result Processing System - Assessment Verification Queries
-- This file contains verification queries for Assessment 9 demonstrations
-- Use these queries in MySQL Workbench to verify database operations

USE student_result_db;

-- ============================================
-- ASSESSMENT 9: INSERT VERIFICATION
-- ============================================

-- Verify student insertion (after adding through frontend)
-- Replace '2024CS999' with the actual registration number used in demonstration
SELECT 
    'INSERT VERIFICATION - Student' AS operation,
    student_id,
    registration_number,
    full_name,
    email,
    department,
    semester,
    academic_year,
    created_at
FROM students 
WHERE registration_number = '2024CS999';

-- Verify marks insertion (after adding through frontend)
-- Replace with the actual mark_id from the demonstration
SELECT 
    'INSERT VERIFICATION - Marks' AS operation,
    mark_id,
    student_id,
    subject_id,
    exam_id,
    marks_obtained,
    maximum_marks,
    created_at
FROM marks 
WHERE mark_id = (SELECT MAX(mark_id) FROM marks);

-- ============================================
-- ASSESSMENT 9: SELECT VERIFICATION
-- ============================================

-- Verify student retrieval by registration number
SELECT 
    'SELECT VERIFICATION - Student by Registration' AS operation,
    student_id,
    registration_number,
    full_name,
    email,
    department,
    semester
FROM students 
WHERE registration_number = '2024CS001';

-- Verify marks retrieval with JOIN
SELECT 
    'SELECT VERIFICATION - Marks with JOIN' AS operation,
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
JOIN examinations e ON m.exam_id = e.exam_id
WHERE s.registration_number = '2024CS001';

-- ============================================
-- ASSESSMENT 9: UPDATE VERIFICATION
-- ============================================

-- Verify marks update (after updating through frontend)
-- Replace with the actual mark_id updated in demonstration
SELECT 
    'UPDATE VERIFICATION - Marks' AS operation,
    mark_id,
    student_id,
    subject_id,
    exam_id,
    marks_obtained,
    maximum_marks,
    updated_at
FROM marks 
WHERE mark_id = 1;  -- Replace with actual mark_id from demonstration

-- Show updated_at timestamp to confirm the update
SELECT 
    'UPDATE VERIFICATION - Timestamp' AS operation,
    mark_id,
    marks_obtained,
    updated_at
FROM marks 
WHERE mark_id = 1;  -- Replace with actual mark_id from demonstration

-- ============================================
-- ASSESSMENT 9: DELETE VERIFICATION
-- ============================================

-- Verify marks deletion (after deleting through frontend)
-- This query should return 0 rows if the deletion was successful
SELECT 
    'DELETE VERIFICATION - Marks (should be 0 rows)' AS operation,
    mark_id,
    student_id,
    subject_id,
    exam_id,
    marks_obtained
FROM marks 
WHERE mark_id = 999;  -- Replace with actual mark_id deleted in demonstration

-- Verify the mark_id no longer exists
SELECT 
    'DELETE VERIFICATION - Check existence' AS operation,
    COUNT(*) AS count
FROM marks 
WHERE mark_id = 999;  -- Replace with actual mark_id deleted in demonstration
-- Expected result: count = 0

-- ============================================
-- ASSESSMENT 9: JOIN VERIFICATION
-- ============================================

-- Multi-table JOIN verification
SELECT 
    'JOIN VERIFICATION - Multi-table' AS operation,
    s.registration_number,
    s.full_name,
    s.department,
    sub.subject_code,
    sub.subject_name,
    e.exam_name,
    e.academic_year,
    m.marks_obtained,
    m.maximum_marks,
    (m.marks_obtained / m.maximum_marks * 100) AS percentage
FROM students s
JOIN marks m ON s.student_id = m.student_id
JOIN subjects sub ON m.subject_id = sub.subject_id
JOIN examinations e ON m.exam_id = e.exam_id
WHERE s.registration_number = '2024CS001'
ORDER BY sub.subject_code;

-- ============================================
-- ASSESSMENT 9: WHERE AND ORDER BY VERIFICATION
-- ============================================

-- WHERE clause verification - Filter by registration number
SELECT 
    'WHERE VERIFICATION - Registration Number' AS operation,
    s.registration_number,
    s.full_name,
    sub.subject_name,
    m.marks_obtained,
    (m.marks_obtained / m.maximum_marks * 100) AS percentage
FROM marks m
JOIN students s ON m.student_id = s.student_id
JOIN subjects sub ON m.subject_id = sub.subject_id
WHERE s.registration_number = '2024CS001';

-- WHERE clause verification - Filter by examination
SELECT 
    'WHERE VERIFICATION - Examination' AS operation,
    s.registration_number,
    s.full_name,
    sub.subject_name,
    e.exam_name,
    m.marks_obtained
FROM marks m
JOIN students s ON m.student_id = s.student_id
JOIN subjects sub ON m.subject_id = sub.subject_id
JOIN examinations e ON m.exam_id = e.exam_id
WHERE e.exam_id = 2;

-- ORDER BY verification - Sort by marks descending
SELECT 
    'ORDER BY VERIFICATION - Marks Descending' AS operation,
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

-- ORDER BY verification - Sort by percentage ascending
SELECT 
    'ORDER BY VERIFICATION - Percentage Ascending' AS operation,
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
-- ASSESSMENT 9: GROUP BY AND AGGREGATE VERIFICATION
-- ============================================

-- COUNT verification
SELECT 
    'AGGREGATE VERIFICATION - COUNT' AS operation,
    'Total Students' AS metric,
    COUNT(*) AS value
FROM students;

-- SUM verification - Total marks for a student
SELECT 
    'AGGREGATE VERIFICATION - SUM' AS operation,
    s.registration_number,
    s.full_name,
    SUM(m.marks_obtained) AS total_obtained,
    SUM(m.maximum_marks) AS total_maximum,
    (SUM(m.marks_obtained) / SUM(m.maximum_marks) * 100) AS overall_percentage
FROM marks m
JOIN students s ON m.student_id = s.student_id
WHERE s.registration_number = '2024CS001'
GROUP BY s.student_id, s.registration_number, s.full_name;

-- AVG verification - Average marks per subject
SELECT 
    'AGGREGATE VERIFICATION - AVG' AS operation,
    sub.subject_code,
    sub.subject_name,
    AVG(m.marks_obtained) AS average_marks,
    AVG(m.marks_obtained / m.maximum_marks * 100) AS average_percentage
FROM marks m
JOIN subjects sub ON m.subject_id = sub.subject_id
GROUP BY sub.subject_id, sub.subject_code, sub.subject_name
ORDER BY average_percentage DESC;

-- MIN verification - Lowest marks in each subject
SELECT 
    'AGGREGATE VERIFICATION - MIN' AS operation,
    sub.subject_code,
    sub.subject_name,
    MIN(m.marks_obtained) AS lowest_marks
FROM marks m
JOIN subjects sub ON m.subject_id = sub.subject_id
GROUP BY sub.subject_id, sub.subject_code, sub.subject_name;

-- MAX verification - Highest marks in each subject
SELECT 
    'AGGREGATE VERIFICATION - MAX' AS operation,
    sub.subject_code,
    sub.subject_name,
    MAX(m.marks_obtained) AS highest_marks
FROM marks m
JOIN subjects sub ON m.subject_id = sub.subject_id
GROUP BY sub.subject_id, sub.subject_code, sub.subject_name;

-- ============================================
-- ASSESSMENT 9: SUBQUERY VERIFICATION
-- ============================================

-- Subquery verification - Students above average
SELECT 
    'SUBQUERY VERIFICATION - Above Average' AS operation,
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

-- Subquery verification - Students with failing subjects
SELECT DISTINCT
    'SUBQUERY VERIFICATION - Failed Students' AS operation,
    s.registration_number,
    s.full_name
FROM marks m
JOIN students s ON m.student_id = s.student_id
WHERE (m.marks_obtained / m.maximum_marks * 100) < 40
ORDER BY s.registration_number;

-- ============================================
-- ASSESSMENT 10: END-TO-END WORKFLOW VERIFICATION
-- ============================================

-- Verify demonstration student (2024CS001) complete result
SELECT 
    'END-TO-END VERIFICATION - Complete Result' AS operation,
    s.registration_number,
    s.full_name,
    COUNT(m.mark_id) AS subjects_attempted,
    SUM(m.marks_obtained) AS total_obtained,
    SUM(m.maximum_marks) AS total_maximum,
    ROUND(SUM(m.marks_obtained) / SUM(m.maximum_marks) * 100, 2) AS overall_percentage
FROM marks m
JOIN students s ON m.student_id = s.student_id
WHERE s.registration_number = '2024CS001' AND m.exam_id = 2
GROUP BY s.student_id, s.registration_number, s.full_name;

-- Verify individual subject marks for demonstration student
SELECT 
    'END-TO-END VERIFICATION - Subject Marks' AS operation,
    sub.subject_code,
    sub.subject_name,
    m.marks_obtained,
    m.maximum_marks,
    ROUND(m.marks_obtained / m.maximum_marks * 100, 2) AS percentage
FROM marks m
JOIN subjects sub ON m.subject_id = sub.subject_id
WHERE m.student_id = 1 AND m.exam_id = 2
ORDER BY sub.subject_code;

-- Expected values for 2024CS001:
-- CS301: 85/100 (85.00%)
-- CS302: 76/100 (76.00%)
-- CS303: 92/100 (92.00%)
-- Total: 253/300 (84.33%)

-- ============================================
-- DATA INTEGRITY VERIFICATION
-- ============================================

-- Verify unique constraint on registration numbers
SELECT 
    'INTEGRITY VERIFICATION - Unique Registration' AS operation,
    registration_number,
    COUNT(*) AS count
FROM students
GROUP BY registration_number
HAVING COUNT(*) > 1;
-- Expected: 0 rows (no duplicates)

-- Verify unique constraint on subject codes
SELECT 
    'INTEGRITY VERIFICATION - Unique Subject Code' AS operation,
    subject_code,
    COUNT(*) AS count
FROM subjects
GROUP BY subject_code
HAVING COUNT(*) > 1;
-- Expected: 0 rows (no duplicates)

-- Verify unique constraint on (student_id, subject_id, exam_id)
SELECT 
    'INTEGRITY VERIFICATION - Unique Marks Entry' AS operation,
    student_id,
    subject_id,
    exam_id,
    COUNT(*) AS count
FROM marks
GROUP BY student_id, subject_id, exam_id
HAVING COUNT(*) > 1;
-- Expected: 0 rows (no duplicates)

-- Verify no negative marks
SELECT 
    'INTEGRITY VERIFICATION - No Negative Marks' AS operation,
    COUNT(*) AS count
FROM marks
WHERE marks_obtained < 0;
-- Expected: 0 rows

-- Verify no marks exceed maximum
SELECT 
    'INTEGRITY VERIFICATION - Marks Not Exceed Max' AS operation,
    COUNT(*) AS count
FROM marks
WHERE marks_obtained > maximum_marks;
-- Expected: 0 rows

-- Verify all maximum marks are positive
SELECT 
    'INTEGRITY VERIFICATION - Positive Maximum Marks' AS operation,
    COUNT(*) AS count
FROM marks
WHERE maximum_marks <= 0;
-- Expected: 0 rows

-- ============================================
-- FOREIGN KEY VERIFICATION
-- ============================================

-- Verify all marks have valid student references
SELECT 
    'FK VERIFICATION - Valid Student References' AS operation,
    COUNT(*) AS orphaned_marks
FROM marks m
LEFT JOIN students s ON m.student_id = s.student_id
WHERE s.student_id IS NULL;
-- Expected: 0 rows

-- Verify all marks have valid subject references
SELECT 
    'FK VERIFICATION - Valid Subject References' AS operation,
    COUNT(*) AS orphaned_marks
FROM marks m
LEFT JOIN subjects s ON m.subject_id = s.subject_id
WHERE s.subject_id IS NULL;
-- Expected: 0 rows

-- Verify all marks have valid exam references
SELECT 
    'FK VERIFICATION - Valid Exam References' AS operation,
    COUNT(*) AS orphaned_marks
FROM marks m
LEFT JOIN examinations e ON m.exam_id = e.exam_id
WHERE e.exam_id IS NULL;
-- Expected: 0 rows

-- ============================================
-- FINAL SUMMARY
-- ============================================

SELECT 'VERIFICATION COMPLETE' AS status;
SELECT COUNT(*) AS total_students FROM students;
SELECT COUNT(*) AS total_subjects FROM subjects;
SELECT COUNT(*) AS total_examinations FROM examinations;
SELECT COUNT(*) AS total_marks FROM marks;
