"""Faculty status, subject assignments and deletion."""
from db import execute_query, is_duplicate_error, transaction
from services import audit
from services.validation import ValidationError


def set_active(faculty_id, active):
    """Activate or deactivate a faculty member together with their login account."""
    flag = 1 if active else 0
    with transaction() as cursor:
        cursor.execute('UPDATE faculty SET is_active = %s WHERE faculty_id = %s', (flag, faculty_id))
        cursor.execute('UPDATE users SET is_active = %s, session_version = session_version + 1 '
                       'WHERE faculty_id = %s', (flag, faculty_id))


def delete_faculty(faculty_id, actor, ip=None):
    """Permanently delete a faculty member, their login and their subject assignments.

    Marks, assessment marks and results have no link to faculty, so nothing that belongs to a
    student is touched. The login goes first because `users.faculty_id` refuses to leave a login
    pointing at a missing faculty row. Everything, including the audit entry, is one transaction:
    on any failure all of it is rolled back. Returns what was removed.
    Raises LookupError when there is no such faculty member.
    """
    with transaction() as cursor:
        cursor.execute('SELECT employee_id, full_name FROM faculty WHERE faculty_id = %s FOR UPDATE',
                       (faculty_id,))
        member = cursor.fetchone()
        if member is None:
            raise LookupError('That faculty member does not exist.')
        cursor.execute('SELECT user_id, username FROM users WHERE faculty_id = %s FOR UPDATE',
                       (faculty_id,))
        login = cursor.fetchone()
        cursor.execute('DELETE FROM faculty_assignments WHERE faculty_id = %s', (faculty_id,))
        assignments = cursor.rowcount
        if login:
            cursor.execute('DELETE FROM users WHERE user_id = %s', (login['user_id'],))
        cursor.execute('DELETE FROM faculty WHERE faculty_id = %s', (faculty_id,))
        removed = {'employee_id': member['employee_id'], 'full_name': member['full_name'],
                   'username': login['username'] if login else None, 'assignments': assignments}
        audit.record(actor, 'faculty.delete', 'faculty', faculty_id,
                     f"{removed['employee_id']} {removed['full_name']}; "
                     f"{'login ' + removed['username'] if login else 'no login'}; "
                     f'{assignments} subject assignment(s) removed', ip, cursor)
    return removed


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
