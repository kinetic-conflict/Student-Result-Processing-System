"""Faculty status and subject assignments."""
from db import execute_query, is_duplicate_error, transaction
from services.validation import ValidationError


def set_active(faculty_id, active):
    """Activate or deactivate a faculty member together with their login account."""
    flag = 1 if active else 0
    with transaction() as cursor:
        cursor.execute('UPDATE faculty SET is_active = %s WHERE faculty_id = %s', (flag, faculty_id))
        cursor.execute('UPDATE users SET is_active = %s, session_version = session_version + 1 '
                       'WHERE faculty_id = %s', (flag, faculty_id))


def assigned_subjects(faculty_id):
    return execute_query(
        'SELECT fa.assignment_id, sub.* FROM faculty_assignments fa '
        'JOIN subjects sub ON sub.subject_id = fa.subject_id WHERE fa.faculty_id = %s '
        'ORDER BY sub.subject_code', (faculty_id,))


def unassigned_subjects(faculty_id):
    return execute_query(
        'SELECT * FROM subjects WHERE subject_id NOT IN '
        '(SELECT subject_id FROM faculty_assignments WHERE faculty_id = %s) ORDER BY subject_code',
        (faculty_id,))


def assign_subject(faculty_id, subject_id):
    """Let a faculty member enter marks for a subject. Returns the assignment id."""
    if not execute_query('SELECT 1 FROM faculty WHERE faculty_id = %s', (faculty_id,)):
        raise ValidationError('That faculty member does not exist.')
    if not execute_query('SELECT 1 FROM subjects WHERE subject_id = %s', (subject_id,)):
        raise ValidationError('That subject does not exist.')
    try:
        with transaction() as cursor:
            cursor.execute('INSERT INTO faculty_assignments (faculty_id, subject_id) VALUES (%s, %s)',
                           (faculty_id, subject_id))
            return cursor.lastrowid
    except Exception as error:
        if is_duplicate_error(error):
            raise ValidationError('That subject is already assigned to this faculty member.') from error
        raise


def unassign(faculty_id, assignment_id):
    """Remove an assignment. Returns False when it does not belong to this faculty member."""
    with transaction() as cursor:
        cursor.execute('DELETE FROM faculty_assignments WHERE assignment_id = %s AND faculty_id = %s',
                       (assignment_id, faculty_id))
        return cursor.rowcount > 0
