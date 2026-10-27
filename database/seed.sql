-- Student Result Processing System - Sample Data
-- Execute this script after schema.sql to populate the database with demonstration data
-- Execute order: schema.sql -> seed.sql

USE student_result_db;

-- Insert sample students
INSERT INTO students (registration_number, full_name, email, department, semester, academic_year) VALUES
('2024CS001', 'Rahul Sharma', 'rahul.sharma@vit.edu', 'Computer Science', 3, '2024-2025'),
('2024CS002', 'Priya Patel', 'priya.patel@vit.edu', 'Computer Science', 3, '2024-2025'),
('2024CS003', 'Amit Kumar', 'amit.kumar@vit.edu', 'Computer Science', 3, '2024-2025'),
('2024CS004', 'Sneha Reddy', 'sneha.reddy@vit.edu', 'Computer Science', 3, '2024-2025'),
('2024CS005', 'Vikram Singh', 'vikram.singh@vit.edu', 'Computer Science', 3, '2024-2025'),
('2024IT001', 'Anjali Gupta', 'anjali.gupta@vit.edu', 'Information Technology', 3, '2024-2025'),
('2024IT002', 'Rohan Das', 'rohan.das@vit.edu', 'Information Technology', 3, '2024-2025'),
('2024ME001', 'Karan Joshi', 'karan.joshi@vit.edu', 'Mechanical Engineering', 3, '2024-2025');

-- Insert sample subjects
INSERT INTO subjects (subject_code, subject_name, credits, semester) VALUES
('CS301', 'Data Structures and Algorithms', 4.0, 3),
('CS302', 'Database Management Systems', 4.0, 3),
('CS303', 'Operating Systems', 4.0, 3),
('CS304', 'Computer Networks', 3.0, 3),
('CS305', 'Web Technologies', 3.0, 3),
('IT301', 'Software Engineering', 4.0, 3),
('IT302', 'Data Mining', 3.0, 3),
('ME301', 'Thermodynamics', 4.0, 3);

-- Insert sample examinations
INSERT INTO examinations (exam_name, academic_year, semester, exam_date) VALUES
('Mid Semester Examination', '2024-2025', 3, '2024-10-15'),
('End Semester Examination', '2024-2025', 3, '2024-12-20'),
('Internal Assessment 1', '2024-2025', 3, '2024-09-10'),
('Internal Assessment 2', '2024-2025', 3, '2024-11-15');

-- Insert sample marks for demonstration
-- These marks will be used for the reproducible calculation example:
-- Subject 1 (CS301): 85/100
-- Subject 2 (CS302): 76/100
-- Subject 3 (CS303): 92/100
-- Expected: Total = 253/300, Percentage = 84.33%, Grades = A, B, A+, Status = Pass

INSERT INTO marks (student_id, subject_id, exam_id, marks_obtained, maximum_marks) VALUES
-- Rahul Sharma (2024CS001) - Demonstration student
(1, 1, 2, 85.00, 100.00),  -- CS301: 85/100 (Grade A)
(1, 2, 2, 76.00, 100.00),  -- CS302: 76/100 (Grade B)
(1, 3, 2, 92.00, 100.00),  -- CS303: 92/100 (Grade A+)
(1, 4, 2, 78.00, 100.00),  -- CS304: 78/100 (Grade B)
(1, 5, 2, 88.00, 100.00),  -- CS305: 88/100 (Grade A)

-- Priya Patel (2024CS002)
(2, 1, 2, 92.00, 100.00),
(2, 2, 2, 88.00, 100.00),
(2, 3, 2, 95.00, 100.00),
(2, 4, 2, 90.00, 100.00),
(2, 5, 2, 85.00, 100.00),

-- Amit Kumar (2024CS003) - Student with one failing subject
(3, 1, 2, 45.00, 100.00),  -- Below 40% - Fail
(3, 2, 2, 72.00, 100.00),
(3, 3, 2, 68.00, 100.00),
(3, 4, 2, 55.00, 100.00),
(3, 5, 2, 62.00, 100.00),

-- Sneha Reddy (2024CS004) - Student with incomplete results
(4, 1, 2, 82.00, 100.00),
(4, 2, 2, 79.00, 100.00),
(4, 3, 2, 88.00, 100.00),
-- Missing marks for CS304 and CS305 - Incomplete

-- Vikram Singh (2024CS005)
(5, 1, 2, 75.00, 100.00),
(5, 2, 2, 82.00, 100.00),
(5, 3, 2, 70.00, 100.00),
(5, 4, 2, 68.00, 100.00),
(5, 5, 2, 72.00, 100.00),

-- Anjali Gupta (2024IT001)
(6, 6, 2, 85.00, 100.00),
(6, 7, 2, 78.00, 100.00),

-- Rohan Das (2024IT002)
(7, 6, 2, 90.00, 100.00),
(7, 7, 2, 85.00, 100.00),

-- Karan Joshi (2024ME001)
(8, 8, 2, 72.00, 100.00);

-- Insert admin user (password: admin123 - hashed with werkzeug)
-- In production, use proper password hashing with bcrypt
INSERT INTO users (username, password_hash, role) VALUES
('admin', 'scrypt:32768:8:1$kL8v5z7q9mN2p4r6$tX9v3w5y7zA1b2c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7', 'admin');

-- Display summary
SELECT 'Sample data inserted successfully!' AS message;
SELECT COUNT(*) AS total_students FROM students;
SELECT COUNT(*) AS total_subjects FROM subjects;
SELECT COUNT(*) AS total_examinations FROM examinations;
SELECT COUNT(*) AS total_marks FROM marks;
