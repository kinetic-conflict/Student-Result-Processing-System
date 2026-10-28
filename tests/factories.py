"""Builders for synthetic test rows. Nothing here is real data."""
from db import execute_update
from services import auth_service

PASSWORD = 'Correct-Horse-9'  # test-only; the app itself ships no default password


def make_student(registration_number='S001', full_name='Student One', semester=3, email=None):
    return execute_update(
        'INSERT INTO students (registration_number, full_name, email, department, semester, academic_year) '
        "VALUES (%s, %s, %s, 'Computer Science', %s, '2024-2025')",
        (registration_number, full_name, email, semester))


def make_subject(subject_code='SUB301', subject_name='Subject', semester=3, credits=3.0):
    return execute_update(
        'INSERT INTO subjects (subject_code, subject_name, credits, semester) VALUES (%s, %s, %s, %s)',
        (subject_code, subject_name, credits, semester))


def make_faculty(employee_id='F001', full_name='Faculty One', email=None):
    return execute_update(
        'INSERT INTO faculty (employee_id, full_name, email, department) '
        "VALUES (%s, %s, %s, 'Computer Science')",
        (employee_id, full_name, email))


def assign(faculty_id, subject_id):
    return execute_update(
        'INSERT INTO faculty_assignments (faculty_id, subject_id) VALUES (%s, %s)',
        (faculty_id, subject_id))


def make_user(username, role, password=PASSWORD, **links):
    return auth_service.create_user(
        username, role, password=password, must_change_password=False, **links)


def record_mark(student_id, subject_id, code, marks):
    """Insert one assessment mark directly, bypassing every app rule."""
    return execute_update(
        'INSERT INTO assessment_marks (student_id, subject_id, assessment_id, marks_obtained) '
        'SELECT %s, %s, assessment_id, %s FROM assessments WHERE assessment_code = %s',
        (student_id, subject_id, marks, code))


def record_all_marks(student_id, subject_id, marks_by_code):
    for code, marks in marks_by_code.items():
        record_mark(student_id, subject_id, code, marks)


def make_exam(exam_name='Mid Term', academic_year='2024-2025', semester=3):
    return execute_update(
        'INSERT INTO examinations (exam_name, academic_year, semester, exam_date) '
        "VALUES (%s, %s, %s, '2024-10-15')", (exam_name, academic_year, semester))


def make_legacy_mark(student_id, subject_id, exam_id, obtained=70, maximum=100):
    return execute_update(
        'INSERT INTO marks (student_id, subject_id, exam_id, marks_obtained, maximum_marks) '
        'VALUES (%s, %s, %s, %s, %s)', (student_id, subject_id, exam_id, obtained, maximum))
