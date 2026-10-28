-- Student Result Processing System - Database Schema
-- MySQL 8.0.16+ (CHECK constraints are enforced from that version)
--
-- Safe to run on an existing database: it only creates what is missing and
-- never drops, truncates or alters anything. Run it first on a new install.
-- Existing installs skip this file and run `flask --app app migrate` instead.

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS student_result_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE student_result_db;

-- Students table
CREATE TABLE IF NOT EXISTS students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    registration_number VARCHAR(20) NOT NULL UNIQUE,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    department VARCHAR(50),
    semester INT,
    academic_year VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_students_name (full_name),
    INDEX idx_students_semester (semester),
    CONSTRAINT chk_semester CHECK (semester > 0 AND semester <= 10)
) ENGINE=InnoDB;

-- Subjects table
CREATE TABLE IF NOT EXISTS subjects (
    subject_id INT AUTO_INCREMENT PRIMARY KEY,
    subject_code VARCHAR(20) NOT NULL UNIQUE,
    subject_name VARCHAR(100) NOT NULL,
    credits DECIMAL(3,1) NOT NULL,
    semester INT NOT NULL,
    INDEX idx_subjects_semester (semester),
    CONSTRAINT chk_credits CHECK (credits > 0 AND credits <= 10),
    CONSTRAINT chk_subject_semester CHECK (semester > 0 AND semester <= 10)
) ENGINE=InnoDB;

-- Examinations table
CREATE TABLE IF NOT EXISTS examinations (
    exam_id INT AUTO_INCREMENT PRIMARY KEY,
    exam_name VARCHAR(100) NOT NULL,
    academic_year VARCHAR(10) NOT NULL,
    semester INT NOT NULL,
    exam_date DATE,
    INDEX idx_examinations_semester (semester),
    INDEX idx_examinations_year (academic_year),
    CONSTRAINT chk_exam_semester CHECK (semester > 0 AND semester <= 10)
) ENGINE=InnoDB;

-- Marks table
CREATE TABLE IF NOT EXISTS marks (
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

-- Users table. Created here in its original shape; the accounts migration
-- (database/migrations/001_*) extends it with roles, status and links.
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'admin',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Display schema information
SELECT 'Database schema ready.' AS message;
