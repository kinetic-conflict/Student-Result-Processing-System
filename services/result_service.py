"""Result calculations. Pure functions: no database, no Flask.

Rules (from the README, the original code and its tests):
- Grade bands: S >= 90, A >= 80, B >= 70, C >= 60, D >= 50, E >= 40, F below 40.
- Pass mark: 40%.
- A weighted assessment result needs every configured component, each within
  0..maximum. Anything else is "Incomplete" and gets no total and no grade.

All arithmetic is exact (Decimal) and every figure is rounded half-up to two
places once, so the number shown is the number graded. Results are returned
as floats for display.
"""
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal('0.01')
PASS_PERCENTAGE = 40


def _dec(value):
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _round2(value):
    return float(value.quantize(CENT, rounding=ROUND_HALF_UP))


def calculate_grade(percentage):
    """Calculate grade based on percentage."""
    if percentage >= 90:
        return 'S'  # Outstanding (VIT uses S for 90+)
    elif percentage >= 80:
        return 'A'
    elif percentage >= 70:
        return 'B'
    elif percentage >= 60:
        return 'C'
    elif percentage >= 50:
        return 'D'
    elif percentage >= 40:
        return 'E'
    else:
        return 'F'


def calculate_pass_status(percentage):
    """Determine pass/fail status based on the 40% threshold."""
    return 'Pass' if percentage >= PASS_PERCENTAGE else 'Fail'


def calculate_percentage(marks_obtained, maximum_marks):
    maximum = _dec(maximum_marks)
    if maximum == 0:
        return 0.0
    return _round2(_dec(marks_obtained) / maximum * 100)


def calculate_weighted_score(marks_obtained, maximum_marks, weight_percentage):
    """Contribution of one component to the final score, e.g. 42/50 at 15% -> 12.6."""
    maximum = _dec(maximum_marks)
    if maximum == 0:
        return 0.0
    return _round2(_dec(marks_obtained) / maximum * _dec(weight_percentage))


def calculate_student_result(marks_data):
    """Overall result across legacy per-exam marks.

    Each item needs `marks_obtained` and `maximum_marks`. The result passes only
    if every subject reaches the pass mark.
    """
    total_maximum = sum((_dec(m['maximum_marks']) for m in marks_data), Decimal(0))
    if not marks_data or total_maximum == 0:
        return {'total_obtained': 0, 'total_maximum': 0, 'overall_percentage': 0,
                'status': 'Incomplete'}

    total_obtained = sum((_dec(m['marks_obtained']) for m in marks_data), Decimal(0))
    all_passed = all(
        calculate_pass_status(calculate_percentage(m['marks_obtained'], m['maximum_marks'])) == 'Pass'
        for m in marks_data)
    return {
        'total_obtained': _round2(total_obtained),
        'total_maximum': _round2(total_maximum),
        'overall_percentage': _round2(total_obtained / total_maximum * 100),
        'status': 'Pass' if all_passed else 'Fail',
    }


def calculate_student_result_with_assessments(assessment_data, config):
    """Weighted result for one student in one subject.

    Args:
        assessment_data: {assessment_code: marks or None}
        config: ordered list of {'code', 'max', 'weight'}, normally the rows of
                the `assessments` table (see services/assessment_config.py)

    Returns:
        assessment_breakdown: one entry per configured component (None where
            the mark is missing or out of range)
        total_weighted_score: out of 100, or None while incomplete
        grade / status: S..F and Pass/Fail, or 'N/A' / 'Incomplete'
    """
    breakdown = []
    total = Decimal(0)
    complete = True

    for item in config:
        marks = assessment_data.get(item['code'])
        maximum = _dec(item['max'])
        entry = {'code': item['code'], 'maximum_marks': _round2(maximum),
                 'weight_percentage': _round2(_dec(item['weight']))}

        if marks is not None and 0 <= _dec(marks) <= maximum:
            weighted = calculate_weighted_score(marks, maximum, item['weight'])
            total += _dec(weighted)
            entry.update(marks_obtained=_round2(_dec(marks)),
                         percentage=calculate_percentage(marks, maximum),
                         weighted_score=weighted)
        else:
            complete = False
            entry.update(marks_obtained=None, percentage=None, weighted_score=None)
        breakdown.append(entry)

    if not complete:
        return {'assessment_breakdown': breakdown, 'total_weighted_score': None,
                'grade': 'N/A', 'status': 'Incomplete'}

    total_score = _round2(total)
    return {'assessment_breakdown': breakdown, 'total_weighted_score': total_score,
            'grade': calculate_grade(total_score), 'status': calculate_pass_status(total_score)}


def process_marks_with_result(marks_records):
    """Add `percentage`, `grade` and `pass_status` to each legacy mark record."""
    for mark in marks_records:
        percentage = calculate_percentage(mark['marks_obtained'], mark['maximum_marks'])
        mark['percentage'] = percentage
        mark['grade'] = calculate_grade(percentage)
        mark['pass_status'] = calculate_pass_status(percentage)
    return marks_records
