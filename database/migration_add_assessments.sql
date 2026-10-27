-- Migration Script: Add Assessment System
-- This script adds support for 6-component assessment system
-- It preserves existing data by migrating it to the new structure
-- Execute this AFTER schema.sql and seed.sql have been run
-- This migration is safe to run multiple times (uses IF NOT EXISTS)

USE student_result_db;

-- Step 1: Create assessments table to define assessment types
CREATE TABLE IF NOT EXISTS assessments (
    assessment_id INT AUTO_INCREMENT PRIMARY KEY,
    assessment_code VARCHAR(20) NOT NULL UNIQUE,
    assessment_name VARCHAR(50) NOT NULL,
    maximum_marks DECIMAL(6 , 2 ) NOT NULL,
    weight_percentage DECIMAL(5 , 2 ) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_weight CHECK (weight_percentage > 0
        AND weight_percentage <= 100),
    CONSTRAINT chk_max_marks CHECK (maximum_marks > 0)
)  ENGINE=INNODB;

-- Step 2: Insert the 6 assessment components
-- Use INSERT IGNORE to prevent errors if already exists
INSERT IGNORE INTO assessments (assessment_code, assessment_name, maximum_marks, weight_percentage) VALUES
('CAT1', 'Continuous Assessment Test 1', 50.00, 15.00),
('CAT2', 'Continuous Assessment Test 2', 50.00, 15.00),
('CAT3', 'Continuous Assessment Test 3', 50.00, 15.00),
('ASSIGN', 'Assignment', 50.00, 10.00),
('PROJECT', 'Project', 100.00, 20.00),
('ENDSEM', 'End Semester Examination', 100.00, 25.00);

-- Step 3: Create assessment_marks table to store individual assessment scores
CREATE TABLE IF NOT EXISTS assessment_marks (
    assessment_mark_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    subject_id INT NOT NULL,
    assessment_id INT NOT NULL,
    marks_obtained DECIMAL(6 , 2 ) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_assessment_marks_student FOREIGN KEY (student_id)
        REFERENCES students (student_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_assessment_marks_subject FOREIGN KEY (subject_id)
        REFERENCES subjects (subject_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_assessment_marks_assessment FOREIGN KEY (assessment_id)
        REFERENCES assessments (assessment_id)
        ON DELETE CASCADE,
    CONSTRAINT uq_student_subject_assessment UNIQUE (student_id , subject_id , assessment_id),
    CONSTRAINT chk_assessment_marks_obtained CHECK (marks_obtained >= 0)
)  ENGINE=INNODB;

-- Step 4: Create indexes for performance
-- Indexes are created with the table, but we ensure they exist
-- Skip if table already exists (indexes will be there)
-- This section only runs if table was just created
-- Note: Indexes are defined in the CREATE TABLE statement above

-- Step 5: Migrate existing marks to assessment_marks
-- This preserves existing data by treating existing marks as End Semester marks
-- Only runs if there are existing marks that haven't been migrated
INSERT IGNORE INTO assessment_marks (student_id, subject_id, assessment_id, marks_obtained)
SELECT 
    m.student_id,
    m.subject_id,
    (SELECT assessment_id FROM assessments WHERE assessment_code = 'ENDSEM'),
    m.marks_obtained
FROM marks m
WHERE NOT EXISTS (
    SELECT 1 FROM assessment_marks am
    WHERE am.student_id = m.student_id 
    AND am.subject_id = m.subject_id
    AND am.assessment_id = (SELECT assessment_id FROM assessments WHERE assessment_code = 'ENDSEM')
);

-- Display migration summary
SELECT 'Assessment system migration completed!' AS message;
SELECT 
    COUNT(*) AS total_assessments
FROM
    assessments;
SELECT 
    COUNT(*) AS migrated_marks
FROM
    assessment_marks;
