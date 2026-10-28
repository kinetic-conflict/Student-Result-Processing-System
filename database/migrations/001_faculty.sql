-- Migration 001: faculty records and their subject assignments.
-- Additive only. Creates two new tables and changes nothing that exists.

CREATE TABLE IF NOT EXISTS faculty (
    faculty_id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL UNIQUE,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    department VARCHAR(50),
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Which subjects a faculty member may enter marks for. Faculty are not
-- deleted (they are deactivated), so only assignment rows cascade away.
CREATE TABLE IF NOT EXISTS faculty_assignments (
    assignment_id INT AUTO_INCREMENT PRIMARY KEY,
    faculty_id INT NOT NULL,
    subject_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_assignment_faculty FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id) ON DELETE CASCADE,
    CONSTRAINT fk_assignment_subject FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE,
    CONSTRAINT uq_faculty_subject UNIQUE (faculty_id, subject_id)
) ENGINE=InnoDB;
