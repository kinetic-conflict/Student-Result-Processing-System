"""Writing assessment marks. The only place marks are created, changed or deleted.

Every write checks access first (services/access.py), validates against the
assessment settings, then happens in one transaction together with its audit
entries: all of it or none of it.
"""
from decimal import Decimal

from db import execute_query, transaction
from services import access, assessment_config, audit
from services.auth_service import ROLE_ADMIN
from services.validation import ValidationError

MARK_PLACES = 2   # the column is DECIMAL(6,2)


class AccessDenied(PermissionError):
    """The user may not change these marks (or cannot be told they exist)."""


def _plain(number):
    return format(Decimal(number).normalize(), 'f')


def _check_value(label, code, value, maximum):
    if -value.as_tuple().exponent > MARK_PLACES:
        raise ValidationError(f'{label}: {code} can have at most {MARK_PLACES} decimal places.')
    if not 0 <= value <= maximum:
        raise ValidationError(f'{label}: {code} must be between 0 and {_plain(maximum)}.')


def _registrations(student_ids):
    placeholders = ', '.join(['%s'] * len(student_ids))
    rows = execute_query(f'SELECT student_id, registration_number FROM students '
                         f'WHERE student_id IN ({placeholders})', tuple(student_ids))
    return {row['student_id']: row['registration_number'] for row in rows}


def save_marks(user, subject_id, entries, ip=None):
    """Save marks for one subject. `entries` is {student_id: {assessment_code: Decimal or None}}.

    A None value means "leave as it is". Returns how many marks actually changed.
    Raises AccessDenied or ValidationError before anything is written.
    """
    config = {item['code']: item for item in assessment_config.load_config()}
    wanted = {student_id: {code: value for code, value in marks.items() if value is not None}
              for student_id, marks in entries.items()}
    wanted = {student_id: marks for student_id, marks in wanted.items() if marks}
    if not wanted:
        raise ValidationError('No marks were entered.')

    for student_id in wanted:
        if not access.can_write_marks(user, student_id, subject_id):
            raise AccessDenied('You may not enter marks for this student and subject.')
    registrations = _registrations(list(wanted))
    for student_id, marks in wanted.items():
        for code, value in marks.items():
            if code not in config:
                raise ValidationError(f'{code} is not an assessment component.')
            _check_value(registrations[student_id], code, value, config[code]['max'])

    changed = 0
    with transaction() as cursor:
        # Re-read the maximums with a shared lock: an administrator lowering one now has to wait
        # until this save commits, so a mark above the new maximum cannot slip in.
        cursor.execute('SELECT assessment_id, assessment_code, maximum_marks FROM assessments FOR SHARE')
        locked = {row['assessment_code']: row for row in cursor.fetchall()}
        for student_id, marks in wanted.items():
            for code, value in marks.items():
                if code not in locked:
                    raise ValidationError(f'{code} is not an assessment component.')
                _check_value(registrations[student_id], code, value, locked[code]['maximum_marks'])
        for student_id, marks in wanted.items():
            for code, value in marks.items():
                assessment_id = locked[code]['assessment_id']
                cursor.execute(
                    'SELECT assessment_mark_id, marks_obtained FROM assessment_marks '
                    'WHERE student_id = %s AND subject_id = %s AND assessment_id = %s FOR UPDATE',
                    (student_id, subject_id, assessment_id))
                existing = cursor.fetchone()
                if existing is None:
                    cursor.execute(
                        'INSERT INTO assessment_marks (student_id, subject_id, assessment_id, '
                        'marks_obtained) VALUES (%s, %s, %s, %s)',
                        (student_id, subject_id, assessment_id, value))
                    mark_id, detail = cursor.lastrowid, f'{registrations[student_id]} {code}: new {_plain(value)}'
                elif existing['marks_obtained'] != value:
                    cursor.execute('UPDATE assessment_marks SET marks_obtained = %s '
                                   'WHERE assessment_mark_id = %s', (value, existing['assessment_mark_id']))
                    mark_id = existing['assessment_mark_id']
                    detail = (f'{registrations[student_id]} {code}: '
                              f'{_plain(existing["marks_obtained"])} -> {_plain(value)}')
                else:
                    continue
                audit.record(user, 'mark.save', 'assessment_mark', mark_id, detail, ip, cursor)
                changed += 1
    return changed


def _load_mark(user, assessment_mark_id):
    rows = execute_query(
        'SELECT am.assessment_mark_id, am.student_id, am.subject_id, am.marks_obtained, '
        'a.assessment_code AS code, a.maximum_marks AS max, s.registration_number, sub.subject_code '
        'FROM assessment_marks am JOIN assessments a ON a.assessment_id = am.assessment_id '
        'JOIN students s ON s.student_id = am.student_id '
        'JOIN subjects sub ON sub.subject_id = am.subject_id WHERE am.assessment_mark_id = %s',
        (assessment_mark_id,))
    if not rows:
        if user['role'] == ROLE_ADMIN:
            raise LookupError('That mark does not exist.')
        raise AccessDenied('You may not change this mark.')   # same answer as a hidden mark
    return rows[0]


def get_mark(user, assessment_mark_id):
    """One mark with its student, subject and assessment, if `user` may change it."""
    mark = _load_mark(user, assessment_mark_id)
    if not access.can_write_marks(user, mark['student_id'], mark['subject_id']):
        raise AccessDenied('You may not change this mark.')
    return mark


def change_mark(user, assessment_mark_id, value, ip=None):
    """Replace one existing mark. Returns False when the value was already stored."""
    mark = get_mark(user, assessment_mark_id)
    _check_value(mark['registration_number'], mark['code'], value, mark['max'])   # early, friendly failure
    with transaction() as cursor:
        # The row and its maximum are read again under lock, so concurrent edits queue up
        # and the audit entry records the value that was really replaced.
        cursor.execute(
            'SELECT am.marks_obtained, a.maximum_marks FROM assessment_marks am '
            'JOIN assessments a ON a.assessment_id = am.assessment_id '
            'WHERE am.assessment_mark_id = %s FOR UPDATE OF am FOR SHARE OF a', (assessment_mark_id,))
        current = cursor.fetchone()
        if current is None:
            raise LookupError('That mark no longer exists.')
        _check_value(mark['registration_number'], mark['code'], value, current['maximum_marks'])
        if value == current['marks_obtained']:
            return False
        cursor.execute('UPDATE assessment_marks SET marks_obtained = %s WHERE assessment_mark_id = %s',
                       (value, assessment_mark_id))
        audit.record(user, 'mark.save', 'assessment_mark', assessment_mark_id,
                     f'{mark["registration_number"]} {mark["code"]}: '
                     f'{_plain(current["marks_obtained"])} -> {_plain(value)}', ip, cursor)
    return True


def delete_mark(user, assessment_mark_id, ip=None):
    """Remove one mark. Administrators only."""
    if user['role'] != ROLE_ADMIN:
        raise AccessDenied('Only administrators may delete marks.')
    mark = _load_mark(user, assessment_mark_id)
    with transaction() as cursor:
        cursor.execute('DELETE FROM assessment_marks WHERE assessment_mark_id = %s', (assessment_mark_id,))
        if cursor.rowcount == 0:      # someone else removed it first: nothing to record
            raise LookupError('That mark no longer exists.')
        audit.record(user, 'mark.delete', 'assessment_mark', assessment_mark_id,
                     f'{mark["registration_number"]} {mark["code"]}: removed {_plain(mark["marks_obtained"])}',
                     ip, cursor)
