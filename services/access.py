"""Which students and subjects a user may see or change.

Every data query that depends on who is asking goes through `scope_filter`, and
every mark write is checked with `can_write_marks`. Changing the rule here
changes it everywhere.

Rules:
- admin: everything.
- faculty: a subject they are assigned to, for students whose semester equals
  that subject's semester. (The schema has no classes or sections, so the
  semester is the cohort. Assigned faculty must be active.)
- student: only their own rows, and never any write.
"""
from db import execute_query
from services.auth_service import ROLE_ADMIN, ROLE_FACULTY, ROLE_STUDENT

FACULTY_SCOPE = (
    ' AND {student}.semester = {subject}.semester'
    ' AND EXISTS (SELECT 1 FROM faculty_assignments fa'
    ' JOIN faculty f ON f.faculty_id = fa.faculty_id'
    ' WHERE fa.faculty_id = %s AND f.is_active = 1 AND fa.subject_id = {subject}.subject_id)'
)


def scope_filter(user, student='s', subject='sub'):
    """An ` AND ...` SQL fragment and its parameters, to append to a WHERE clause.

    `student` and `subject` are the table aliases the query uses. The fragment
    uses only the aliases given, so it is safe to place in a larger query.
    """
    role = user['role']
    if role == ROLE_ADMIN:
        return '', ()
    if role == ROLE_STUDENT:
        return f' AND {student}.student_id = %s', (user['student_id'],)
    if role == ROLE_FACULTY:
        return FACULTY_SCOPE.format(student=student, subject=subject), (user['faculty_id'],)
    return ' AND 1 = 0', ()


def can_write_marks(user, student_id, subject_id):
    """True when `user` may enter or change marks for this student in this subject."""
    if user['role'] not in (ROLE_ADMIN, ROLE_FACULTY):
        return False
    fragment, params = scope_filter(user)
    rows = execute_query(
        'SELECT 1 FROM students s JOIN subjects sub ON sub.subject_id = %s '
        'WHERE s.student_id = %s' + fragment,
        (subject_id, student_id, *params))
    return bool(rows)


def students_for_subject(user, subject_id):
    """The students of a subject's semester that `user` may see, in registration order."""
    fragment, params = scope_filter(user)
    return execute_query(
        'SELECT s.* FROM students s JOIN subjects sub ON sub.subject_id = %s '
        'WHERE s.semester = sub.semester' + fragment + ' ORDER BY s.registration_number',
        (subject_id, *params))


def subjects_for(user):
    """Subjects `user` can enter marks for: all of them for admins, assigned ones for faculty."""
    if user['role'] == ROLE_ADMIN:
        return execute_query('SELECT * FROM subjects ORDER BY subject_code')
    if user['role'] == ROLE_FACULTY:
        return execute_query(
            'SELECT sub.* FROM subjects sub '
            'JOIN faculty_assignments fa ON fa.subject_id = sub.subject_id '
            'JOIN faculty f ON f.faculty_id = fa.faculty_id '
            'WHERE fa.faculty_id = %s AND f.is_active = 1 ORDER BY sub.subject_code',
            (user['faculty_id'],))
    return []


def students_for(user):
    """Every student `user` may see in at least one subject, each listed once."""
    if user['role'] == ROLE_ADMIN:
        return execute_query('SELECT * FROM students ORDER BY registration_number')
    fragment, params = scope_filter(user)
    return execute_query(
        'SELECT DISTINCT s.* FROM students s JOIN subjects sub ON 1 = 1 WHERE 1 = 1'
        + fragment + ' ORDER BY s.registration_number', params)


def can_manage_subject(user, subject_id):
    """True when `user` may open the mark-entry sheet for this subject."""
    if user['role'] == ROLE_ADMIN:
        return True
    return any(subject['subject_id'] == subject_id for subject in subjects_for(user))
