from flask import Blueprint, g, render_template, request

from db import execute_query, like_contains
from services import access
from services.pagination import paginate
from services.result_service import process_marks_with_result

results_bp = Blueprint('results', __name__)

SEARCH_COLUMNS = {'registration': 's.registration_number', 'name': 's.full_name'}

RESULT_FROM = """
    FROM marks m
    JOIN students s ON m.student_id = s.student_id
    JOIN subjects sub ON m.subject_id = sub.subject_id
    JOIN examinations e ON m.exam_id = e.exam_id
    WHERE {column} LIKE %s
"""


@results_bp.route('/results')
def search():
    """Per-examination results found by registration number or name, within the user's scope."""
    term = request.args.get('search', '').strip()
    filter_type = request.args.get('filter_type', 'registration')
    if filter_type not in SEARCH_COLUMNS:
        filter_type = 'registration'

    rows, page = [], None
    if term:
        fragment, scope_params = access.scope_filter(g.user)
        source = RESULT_FROM.format(column=SEARCH_COLUMNS[filter_type]) + fragment
        params = (like_contains(term), *scope_params)
        total = execute_query(f'SELECT COUNT(*) AS n {source}', params)[0]['n']
        page = paginate(total, request.args.get('page'))
        rows = process_marks_with_result(execute_query(
            'SELECT m.*, s.registration_number, s.full_name, s.department, sub.subject_code, '
            f'sub.subject_name, e.exam_name, e.academic_year {source} '
            f'ORDER BY {SEARCH_COLUMNS[filter_type]}, sub.subject_code LIMIT %s OFFSET %s',
            (*params, page.per_page, page.offset)))
    return render_template('results.html', results=rows, page=page, search=term,
                           filter_type=filter_type)
