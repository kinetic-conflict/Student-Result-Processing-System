from flask import Blueprint, g, render_template

from db import execute_query
from services import access, result_queries

faculty_bp = Blueprint('faculty', __name__, url_prefix='/faculty')


@faculty_bp.route('')
def dashboard():
    """The faculty member's subjects, with how far each mark sheet is filled in."""
    profile = execute_query('SELECT * FROM faculty WHERE faculty_id = %s', (g.user['faculty_id'],))[0]
    subjects = []
    for subject in access.subjects_for(g.user):
        records = result_queries.weighted_results(
            g.user, subject_id=subject['subject_id'], per_page=10_000)['rows']
        subjects.append({
            'subject': subject,
            'cohort': len(access.students_for_subject(g.user, subject['subject_id'])),
            'with_marks': len(records),
            'complete': sum(1 for r in records if r['result']['status'] != 'Incomplete'),
        })
    return render_template('faculty_dashboard.html', profile=profile, subjects=subjects)
