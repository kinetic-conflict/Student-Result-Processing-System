-- Student Result Processing System - Database Schema
-- MySQL 8.x compatible
-- Execute this script first to create the database and all tables

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS student_result_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE student_result_db;

-- Drop tables if they exist (for clean recreation)
DROP TABLE IF EXISTS marks;
DROP TABLE IF EXISTS examinations;
DROP TABLE IF EXISTS subjects;
DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS users;

-- Students table
CREATE TABLE students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    registration_number VARCHAR(20) NOT NULL UNIQUE,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    department VARCHAR(50),
    semester INT,
    academic_year VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_semester CHECK (semester > 0 AND semester <= 10)
) ENGINE=InnoDB;

-- Subjects table
CREATE TABLE subjects (
    subject_id INT AUTO_INCREMENT PRIMARY KEY,
    subject_code VARCHAR(20) NOT NULL UNIQUE,
    subject_name VARCHAR(100) NOT NULL,
    credits DECIMAL(3,1) NOT NULL,
    semester INT NOT NULL,
    CONSTRAINT chk_credits CHECK (credits > 0 AND credits <= 10),
    CONSTRAINT chk_subject_semester CHECK (semester > 0 AND semester <= 10)
) ENGINE=InnoDB;

-- Examinations table
CREATE TABLE examinations (
    exam_id INT AUTO_INCREMENT PRIMARY KEY,
    exam_name VARCHAR(100) NOT NULL,
    academic_year VARCHAR(10) NOT NULL,
    semester INT NOT NULL,
    exam_date DATE,
    CONSTRAINT chk_exam_semester CHECK (semester > 0 AND semester <= 10)
) ENGINE=InnoDB;

-- Marks table
CREATE TABLE marks (
    mark_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    subject_id INT NOT NULL,
    exam_id INT NOT NULL,
    marks_obtained DECIMAL(6,2) NOT NULL,
    maximum_marks DECIMAL(6,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    CONSTRAINT fk_marks_student FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    CONSTRAINT fk_marks_subject FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE,
    CONSTRAINT fk_marks_exam FOREIGN KEY (exam_id) REFERENCES examinations(exam_id) ON DELETE CASCADE,
    
    -- Unique constraint to prevent duplicate marks for same student, subject, and exam
    CONSTRAINT uq_student_subject_exam UNIQUE (student_id, subject_id, exam_id),
    
    -- Check constraints for data integrity
    CONSTRAINT chk_marks_obtained CHECK (marks_obtained >= 0),
    CONSTRAINT chk_maximum_marks CHECK (maximum_marks > 0),
    CONSTRAINT chk_marks_not_exceed_max CHECK (marks_obtained <= maximum_marks)
) ENGINE=InnoDB;

-- Users table (for authentication, if implemented)
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'admin',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Create indexes for better query performance
CREATE INDEX idx_students_registration ON students(registration_number);
CREATE INDEX idx_students_name ON students(full_name);
CREATE INDEX idx_students_semester ON students(semester);
CREATE INDEX idx_subjects_code ON subjects(subject_code);
CREATE INDEX idx_subjects_semester ON subjects(semester);
CREATE INDEX idx_examinations_semester ON examinations(semester);
CREATE INDEX idx_examinations_year ON examinations(academic_year);
CREATE INDEX idx_marks_student ON marks(student_id);
CREATE INDEX idx_marks_subject ON marks(subject_id);
CREATE INDEX idx_marks_exam ON marks(exam_id);

-- Display schema information
SELECT 'Database schema created successfully!' AS message;
