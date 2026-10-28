"""Weighted assessment results, listed for whoever is asking.

One read path for every role: the scope filter decides which rows a user can
reach, so a student, a faculty member and an administrator calling the same
function see different data without any caller special-casing roles.
"""
from db import execute_query, like_contains
from services import access, assessment_config
from services.pagination import paginate
from services.result_service import calculate_student_result_with_assessments

PAIRS_FROM = (
    'FROM students s JOIN subjects sub ON EXISTS ('
    'SELECT 1 FROM assessment_marks am WHERE am.student_id = s.student_id '
    'AND am.subject_id = sub.subject_id) WHERE 1 = 1'
)


def weighted_results(user, subject_id=None, student_id=None, search=None,
                     raw_page=None, per_page=25):
    """One page of (student, subject) records that have at least one mark.

    Returns {'rows': [...], 'page': Page}. Each row carries the raw `marks` by
    assessment code and the calculated `result`.
    """
    where, params = '', []
    if subject_id:
        where += ' AND sub.subject_id = %s'
        params.append(subject_id)
    if student_id:
        where += ' AND s.student_id = %s'
        params.append(student_id)
    if search:
        pattern = like_contains(search)
        where += ' AND (s.registration_number LIKE %s OR s.full_name LIKE %s)'
        params += [pattern, pattern]
    fragment, scope_params = access.scope_filter(user)
    where += fragment
    params += scope_params

    total = execute_query(f'SELECT COUNT(*) AS n {PAIRS_FROM}{where}', tuple(params))[0]['n']
    page = paginate(total, raw_page, per_page)
    pairs = execute_query(
        'SELECT s.student_id, s.registration_number, s.full_name, '
        'sub.subject_id, sub.subject_code, sub.subject_name, sub.credits, sub.semester '
        f'{PAIRS_FROM}{where} ORDER BY s.registration_number, sub.subject_code LIMIT %s OFFSET %s',
        (*params, page.per_page, page.offset))
    return {'rows': _attach_results(pairs), 'page': page}


def _attach_results(pairs):
    if not pairs:
        return []
    condition = ' OR '.join(['(am.student_id = %s AND am.subject_id = %s)'] * len(pairs))
    values = [value for pair in pairs for value in (pair['student_id'], pair['subject_id'])]
    marks_by_pair = {}
    for row in execute_query(
            'SELECT am.student_id, am.subject_id, a.assessment_code AS code, am.marks_obtained '
            'FROM assessment_marks am JOIN assessments a ON a.assessment_id = am.assessment_id '
            f'WHERE {condition}', tuple(values)):
        marks_by_pair.setdefault((row['student_id'], row['subject_id']), {})[row['code']] = row['marks_obtained']

    config = assessment_config.for_calculation(assessment_config.load_config())
    for pair in pairs:
        pair['marks'] = marks_by_pair.get((pair['student_id'], pair['subject_id']), {})
        pair['result'] = calculate_student_result_with_assessments(pair['marks'], config)
    return pairs
