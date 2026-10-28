-- Migration 002: turn the unused `users` table into the login table.
-- Existing rows keep their username, hash and role; new columns take safe defaults
-- (active, no forced password change, no linked student or faculty record).
-- Fails, and changes nothing, if an existing row has a role other than
-- admin, faculty or student.

ALTER TABLE users
    ADD COLUMN email VARCHAR(100) NULL AFTER username,
    ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1,
    ADD COLUMN must_change_password TINYINT(1) NOT NULL DEFAULT 0,
    ADD COLUMN session_version INT NOT NULL DEFAULT 1,
    ADD COLUMN student_id INT NULL,
    ADD COLUMN faculty_id INT NULL,
    ADD COLUMN last_login_at DATETIME NULL,
    ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    ADD CONSTRAINT uq_users_email UNIQUE (email),
    ADD CONSTRAINT uq_users_student UNIQUE (student_id),
    ADD CONSTRAINT uq_users_faculty UNIQUE (faculty_id),
    ADD CONSTRAINT fk_users_student FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_users_faculty FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id) ON DELETE RESTRICT,
    ADD CONSTRAINT chk_users_role_links CHECK (
        (role = 'admin' AND student_id IS NULL AND faculty_id IS NULL)
        OR (role = 'student' AND student_id IS NOT NULL AND faculty_id IS NULL)
        OR (role = 'faculty' AND faculty_id IS NOT NULL AND student_id IS NULL)
    );
