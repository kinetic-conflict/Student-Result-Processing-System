"""Synthetic sample assessment marks, added only when someone runs `flask --app app seed-demo`.

Three rules keep it away from real records:
- only students whose email is in the reserved ".example" domain used by the sample seed files;
- only (student, subject) pairs that already have an examination mark, which stands in for
  enrolment because the schema has no enrolment table;
- only marks that are missing: existing marks are never changed or removed.

Nothing is random. Each component is the student's end-semester percentage plus a fixed offset,
rounded to the nearest half mark, so the same data always gives the same marks.
"""
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from db import execute_query, transaction
from services import assessment_config, audit

SYNTHETIC_EMAIL_SUFFIX = '@students.example'

# Percentage points added to the end-semester percentage, one per component in display order.
OFFSETS = (-4, 2, -1, 6, 3, 0)
# Some records are left unfinished on purpose, so the sample shows "missing" and "zero" apart:
# every 7th has no project or end-semester mark yet (no row), every 10th has an assignment scored 0.
UNFINISHED_EVERY, UNFINISHED_CODES = 7, ('PROJECT', 'ENDSEM')
ZERO_EVERY, ZERO_CODE = 10, 'ASSIGN'

ROSTER = (
    'SELECT s.student_id, s.registration_number, sub.subject_id, sub.subject_code, '
    'm.marks_obtained, m.maximum_marks FROM marks m '
    'JOIN students s ON s.student_id = m.student_id '
    'JOIN subjects sub ON sub.subject_id = m.subject_id '
    'JOIN examinations e ON e.exam_id = m.exam_id WHERE s.email LIKE %s '
    'ORDER BY s.registration_number, sub.subject_code, e.exam_date DESC, e.exam_id DESC'
)
EXISTING = (
    'SELECT am.student_id, am.subject_id, am.assessment_id FROM assessment_marks am '
    'JOIN students s ON s.student_id = am.student_id WHERE s.email LIKE %s'
)


@dataclass
class Plan:
    rows: list = field(default_factory=list)   # marks to add
    students: int = 0                          # distinct students those marks belong to
    existing: int = 0                          # sample marks that are already there and stay as they are


def _half_mark(maximum, percentage):
    return (maximum * percentage / 100 * 2).quantize(Decimal(1), rounding=ROUND_HALF_UP) / 2


def _component_marks(position, end_percentage, config):
    """{code: Decimal, or None for "not entered yet"} for the `position`-th roster entry."""
    marks = {}
    for index, item in enumerate(config):
        code = item['code']
        if position % UNFINISHED_EVERY == UNFINISHED_EVERY - 1 and code in UNFINISHED_CODES:
            marks[code] = None
        elif position % ZERO_EVERY == ZERO_EVERY - 1 and code == ZERO_CODE:
            marks[code] = Decimal(0)
        else:
            percentage = min(Decimal(100), max(Decimal(0), end_percentage + OFFSETS[index % len(OFFSETS)]))
            marks[code] = _half_mark(item['max'], percentage)
    return marks


def plan():
    """Work out which marks would be added. Reads only; writes nothing."""
    like = '%' + SYNTHETIC_EMAIL_SUFFIX
    config = assessment_config.load_config()
    ids = {item['code']: item['assessment_id'] for item in config}
    present = {(r['student_id'], r['subject_id'], r['assessment_id']) for r in execute_query(EXISTING, (like,))}

    result, seen = Plan(), set()
    for entry in execute_query(ROSTER, (like,)):
        pair = (entry['student_id'], entry['subject_id'])
        if pair in seen:                 # several examinations: the newest one decides
            continue
        end_percentage = entry['marks_obtained'] / entry['maximum_marks'] * 100
        for code, value in _component_marks(len(seen), end_percentage, config).items():
            if value is None:
                continue
            if pair + (ids[code],) in present:
                result.existing += 1
            else:
                result.rows.append({
                    'student_id': entry['student_id'], 'subject_id': entry['subject_id'],
                    'assessment_id': ids[code], 'code': code, 'value': value,
                    'registration_number': entry['registration_number'], 'subject_code': entry['subject_code']})
        seen.add(pair)
    result.students = len({row['student_id'] for row in result.rows})
    return result


def apply(plan_to_apply):
    """Insert the planned marks and one audit entry, all or nothing. Returns how many were added."""
    if not plan_to_apply.rows:
        return 0
    with transaction() as cursor:
        for row in plan_to_apply.rows:
            cursor.execute(
                'INSERT INTO assessment_marks (student_id, subject_id, assessment_id, marks_obtained) '
                'VALUES (%s, %s, %s, %s)',
                (row['student_id'], row['subject_id'], row['assessment_id'], row['value']))
        audit.record(None, 'demo_data.seed', 'assessment_mark', None,
                     f'{len(plan_to_apply.rows)} synthetic marks for {plan_to_apply.students} students',
                     None, cursor)
    return len(plan_to_apply.rows)
