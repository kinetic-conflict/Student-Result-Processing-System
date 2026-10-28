-- VIT-Style Student Data Expansion
-- SYNTHETIC DEMONSTRATION DATA. Every person, number and email below is made up.
-- Do not load this into a database that holds real student records.
--
-- Adds 25 students and 30 subjects in the style of VIT registration numbers.
-- Safe to run again: rows are matched on their natural keys and skipped if present.
-- Execute after migration_add_assessments.sql

USE student_result_db;

-- Insert 25 VIT-style students with registration numbers like 23BCE1042, 24BIT0237, etc.
-- Program codes: BCE (Bioengineering), BIT (Information Technology), BDS (Data Science), 
-- BAI (AI), BEC (Electronics), BME (Mechanical Engineering)
-- Admission years: 2023, 2024, 2025
-- Email pattern: firstname.lastname2025@students.example

INSERT IGNORE INTO students (registration_number, full_name, email, department, semester, academic_year) VALUES
-- 2023 Batch (3rd year students)
('23BCE1042', 'Arjun Nair', 'arjun.nair2023@students.example', 'Bioengineering', 5, '2024-2025'),
('23BCE1156', 'Diya Sharma', 'diya.sharma2023@students.example', 'Bioengineering', 5, '2024-2025'),
('23BIT0237', 'Karthik Rajan', 'karthik.rajan2023@students.example', 'Information Technology', 5, '2024-2025'),
('23BIT0389', 'Meera Krishnan', 'meera.krishnan2023@students.example', 'Information Technology', 5, '2024-2025'),
('23BDS0156', 'Neha Verma', 'neha.verma2023@students.example', 'Data Science', 5, '2024-2025'),
('23BDS0278', 'Rohan Singh', 'rohan.singh2023@students.example', 'Data Science', 5, '2024-2025'),
('23BAI0934', 'Sanya Gupta', 'sanya.gupta2023@students.example', 'Artificial Intelligence', 5, '2024-2025'),
('23BAI1089', 'Vikram Patel', 'vikram.patel2023@students.example', 'Artificial Intelligence', 5, '2024-2025'),

-- 2024 Batch (2nd year students)
('24BCE0567', 'Aditi Reddy', 'aditi.reddy2024@students.example', 'Bioengineering', 3, '2024-2025'),
('24BCE0789', 'Bhavesh Kumar', 'bhavesh.kumar2024@students.example', 'Bioengineering', 3, '2024-2025'),
('24BIT0145', 'Chitra Iyer', 'chitra.iyer2024@students.example', 'Information Technology', 3, '2024-2025'),
('24BIT0298', 'Deepak Menon', 'deepak.menon2024@students.example', 'Information Technology', 3, '2024-2025'),
('24BDS0089', 'Esha Das', 'esha.das2024@students.example', 'Data Science', 3, '2024-2025'),
('24BDS0192', 'Farhan Ahmed', 'farhan.ahmed2024@students.example', 'Data Science', 3, '2024-2025'),
('24BAI0493', 'Gauri Joshi', 'gauri.joshi2024@students.example', 'Artificial Intelligence', 3, '2024-2025'),
('24BAI0621', 'Harsh Mehta', 'harsh.mehta2024@students.example', 'Artificial Intelligence', 3, '2024-2025'),
('24BEC0345', 'Ishaan Nair', 'ishaan.nair2024@students.example', 'Electronics', 3, '2024-2025'),
('24BEC0456', 'Jaya Pillai', 'jaya.pillai2024@students.example', 'Electronics', 3, '2024-2025'),

-- 2025 Batch (1st year students)
('25BCE0234', 'Kavita Rao', 'kavita.rao2025@students.example', 'Bioengineering', 1, '2025-2026'),
('25BCE0356', 'Lakshman Singh', 'lakshman.singh2025@students.example', 'Bioengineering', 1, '2025-2026'),
('25BIT0123', 'Madhuri Desai', 'madhuri.desai2025@students.example', 'Information Technology', 1, '2025-2026'),
('25BIT0245', 'Nandan Kulkarni', 'nandan.kulkarni2025@students.example', 'Information Technology', 1, '2025-2026'),
('25BME0189', 'Omkar Patil', 'omkar.patil2025@students.example', 'Mechanical Engineering', 1, '2025-2026'),
('25BME0298', 'Priyanka Choudhury', 'priyanka.choudhury2025@students.example', 'Mechanical Engineering', 1, '2025-2026'),
('25BDS0078', 'Quasim Ali', 'quasim.ali2025@students.example', 'Data Science', 1, '2025-2026');

-- Add subjects with VIT-style course codes (these sit beside the generic codes; nothing is replaced)
INSERT IGNORE INTO subjects (subject_code, subject_name, credits, semester) VALUES
-- Common Engineering Courses (Semester 1-2)
('CSE1001', 'Engineering Mathematics I', 4.0, 1),
('CSE1002', 'Engineering Physics', 3.0, 1),
('CSE1003', 'Basic Electrical Engineering', 3.0, 1),
('CSE1004', 'Engineering Graphics', 3.0, 1),
('CSE1005', 'Problem Solving using Python', 3.0, 1),
('CSE2001', 'Engineering Mathematics II', 4.0, 2),
('CSE2002', 'Engineering Chemistry', 3.0, 2),
('CSE2003', 'Basic Mechanical Engineering', 3.0, 2),
('CSE2004', 'Environmental Science', 2.0, 2),
('CSE2005', 'Digital Logic Design', 4.0, 2),

-- Core Computer Science Courses (Semester 3-4)
('CSE3001', 'Data Structures and Algorithms', 4.0, 3),
('CSE3002', 'Database Management Systems', 4.0, 3),
('CSE3003', 'Object Oriented Programming', 4.0, 3),
('CSE3004', 'Computer Organization', 3.0, 3),
('CSE3005', 'Discrete Mathematics', 3.0, 3),
('CSE4001', 'Operating Systems', 4.0, 4),
('CSE4002', 'Computer Networks', 4.0, 4),
('CSE4003', 'Software Engineering', 3.0, 4),
('CSE4004', 'Theory of Computation', 3.0, 4),
('CSE4005', 'Web Technologies', 3.0, 4),

-- Advanced Courses (Semester 5-6)
('CSE5001', 'Machine Learning', 4.0, 5),
('CSE5002', 'Computer Graphics', 3.0, 5),
('CSE5003', 'Distributed Systems', 3.0, 5),
('CSE5004', 'Cloud Computing', 3.0, 5),
('CSE5005', 'Cyber Security', 3.0, 5),
('CSE6001', 'Artificial Intelligence', 4.0, 6),
('CSE6002', 'Big Data Analytics', 3.0, 6),
('CSE6003', 'Internet of Things', 3.0, 6),
('CSE6004', 'Blockchain Technology', 3.0, 6),
('CSE6005', 'Capstone Project', 6.0, 6);

-- Add examinations for the new academic year (examinations have no unique key, so check first)
INSERT INTO examinations (exam_name, academic_year, semester, exam_date)
SELECT v.exam_name, v.academic_year, v.semester, v.exam_date
FROM (
    SELECT 'End Semester Examination 2025-2026' AS exam_name, '2025-2026' AS academic_year, 1 AS semester, DATE '2025-12-15' AS exam_date
    UNION ALL SELECT 'Mid Semester Examination 2025-2026', '2025-2026', 1, DATE '2025-10-10'
) AS v
WHERE NOT EXISTS (
    SELECT 1 FROM examinations e
    WHERE e.exam_name = v.exam_name AND e.academic_year = v.academic_year AND e.semester = v.semester
);

-- Display summary
SELECT 'VIT student data expansion completed!' AS message;
SELECT COUNT(*) AS total_students FROM students;
SELECT COUNT(*) AS total_subjects FROM subjects;
SELECT COUNT(*) AS total_examinations FROM examinations;
