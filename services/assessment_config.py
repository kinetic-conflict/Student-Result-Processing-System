"""The assessment components (CAT1, End Semester, ...) and their maximums and weights.

The `assessments` table is the single source of truth. Calculations receive it
through `for_calculation`; nothing else holds these numbers.
"""
from decimal import Decimal

from db import execute_query, transaction
from services.validation import ValidationError

MAX_MARKS_LIMIT = Decimal('9999.99')   # column is DECIMAL(6,2)
TOTAL_WEIGHT = Decimal(100)


def load_config():
    """All components in display order, with Decimal maximums and weights."""
    return execute_query(
        'SELECT assessment_id, assessment_code AS code, assessment_name AS name, '
        'maximum_marks AS max, weight_percentage AS weight '
        'FROM assessments ORDER BY assessment_id')


def for_calculation(config):
    """The shape result_service expects: ordered {'code', 'max', 'weight'}."""
    return [{'code': a['code'], 'max': a['max'], 'weight': a['weight']} for a in config]


def update_config(values):
    """Change maximums and weights. `values` maps assessment_id -> (maximum, weight).

    Every component must be supplied, weights must total exactly 100, and no
    maximum may fall below a mark that is already recorded. All or nothing.
    Returns a list of human-readable changes for the audit log.
    """
    with transaction() as cursor:
        cursor.execute('SELECT assessment_id, assessment_code, maximum_marks, weight_percentage '
                       'FROM assessments ORDER BY assessment_id FOR UPDATE')
        current = {row['assessment_id']: row for row in cursor.fetchall()}
        if set(values) != set(current):
            raise ValidationError('Provide a maximum and a weight for every assessment component.')

        for assessment_id, (maximum, weight) in values.items():
            code = current[assessment_id]['assessment_code']
            if not 0 < maximum <= MAX_MARKS_LIMIT:
                raise ValidationError(f'Maximum marks for {code} must be greater than 0 '
                                      f'and at most {MAX_MARKS_LIMIT}.')
            if not 0 < weight <= TOTAL_WEIGHT:
                raise ValidationError(f'Weight for {code} must be greater than 0 and at most 100.')
            cursor.execute('SELECT MAX(marks_obtained) AS highest FROM assessment_marks '
                           'WHERE assessment_id = %s', (assessment_id,))
            highest = cursor.fetchone()['highest']
            if highest is not None and maximum < highest:
                raise ValidationError(f'{code}: marks already recorded go up to {highest}, '
                                      'so the maximum cannot be lower than that.')

        total = sum((weight for _, weight in values.values()), Decimal(0))
        if total != TOTAL_WEIGHT:
            raise ValidationError(f'Weights must add up to 100 (they add up to {total}).')

        changes = []
        for assessment_id, (maximum, weight) in values.items():
            row = current[assessment_id]
            if (maximum, weight) == (row['maximum_marks'], row['weight_percentage']):
                continue
            cursor.execute('UPDATE assessments SET maximum_marks = %s, weight_percentage = %s '
                           'WHERE assessment_id = %s', (maximum, weight, assessment_id))
            changes.append(f"{row['assessment_code']}: max {row['maximum_marks']} -> {maximum}, "
                           f"weight {row['weight_percentage']} -> {weight}")
        return changes
