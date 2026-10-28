from flask import Blueprint, g, render_template

from db import execute_query
from services import assessment_config, result_queries
from services.exam_results import student_exam_results

student_bp = Blueprint('student', __name__, url_prefix='/me')


def _own_record():
    """The signed-in student's data. The id comes from the account, never from the request."""
    student_id = g.user['student_id']
    return {
        'profile': execute_query('SELECT * FROM students WHERE student_id = %s', (student_id,))[0],
        'subject_results': result_queries.weighted_results(g.user, per_page=10_000)['rows'],
        'exam_results': student_exam_results(student_id),
        'config': assessment_config.load_config(),
    }


@student_bp.route('')
def dashboard():
    """The student's own profile and results."""
    return render_template('student_dashboard.html', **_own_record())


@student_bp.route('/marksheet')
def marksheet():
    """A print-ready statement of the student's own results."""
    return render_template('marksheet.html', **_own_record())
