from flask import Blueprint, render_template

from db import execute_query

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

COUNTS = {
    'students': 'SELECT COUNT(*) FROM students',
    'subjects': 'SELECT COUNT(*) FROM subjects',
    'examinations': 'SELECT COUNT(*) FROM examinations',
    'faculty': 'SELECT COUNT(*) FROM faculty',
    'accounts': 'SELECT COUNT(*) FROM users',
    'exam-marks': 'SELECT COUNT(*) FROM marks',
    'assessment-marks': 'SELECT COUNT(*) FROM assessment_marks',
}

# Work waiting for an administrator, as counts only (no personal data on the dashboard).
ATTENTION = {
    'students-without-login': ('Students without a login',
                               'SELECT COUNT(*) FROM students s WHERE NOT EXISTS '
                               '(SELECT 1 FROM users u WHERE u.student_id = s.student_id)', 'users.list_users'),
    'faculty-without-subjects': ('Faculty with no subjects assigned',
                                 'SELECT COUNT(*) FROM faculty f WHERE f.is_active = 1 AND NOT EXISTS '
                                 '(SELECT 1 FROM faculty_assignments fa WHERE fa.faculty_id = f.faculty_id)',
                                 'faculty_admin.list_faculty'),
    'subjects-without-faculty': ('Subjects nobody teaches',
                                 'SELECT COUNT(*) FROM subjects sub WHERE NOT EXISTS '
                                 '(SELECT 1 FROM faculty_assignments fa WHERE fa.subject_id = sub.subject_id)',
                                 'faculty_admin.list_faculty'),
}

RECENT_MARKS = """
    SELECT m.*, s.registration_number, s.full_name,
           sub.subject_code, sub.subject_name, e.exam_name
    FROM marks m
    JOIN students s ON m.student_id = s.student_id
    JOIN subjects sub ON m.subject_id = sub.subject_id
    JOIN examinations e ON m.exam_id = e.exam_id
    ORDER BY m.created_at DESC
    LIMIT 10
"""


@admin_bp.route('')
def dashboard():
    """Summary counts, work needing attention, and the latest marks entries."""
    def count(sql):
        return next(iter(execute_query(sql)[0].values()))

    counts = {key: count(sql) for key, sql in COUNTS.items()}
    attention = [{'key': key, 'label': label, 'count': count(sql), 'endpoint': endpoint}
                 for key, (label, sql, endpoint) in ATTENTION.items()]
    return render_template('dashboard.html', counts=counts, attention=attention,
                           recent_marks=execute_query(RECENT_MARKS))
