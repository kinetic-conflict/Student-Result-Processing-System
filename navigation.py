"""Which pages each role sees in the top menu. Adding a page is one new entry."""
from flask import g, request, url_for

NAV_ITEMS = {
    'admin': [
        ('Dashboard', 'admin.dashboard'),
        ('Students', 'students.list_students'),
        ('Subjects', 'subjects.list_subjects'),
        ('Examinations', 'examinations.list_examinations'),
        ('Marks', 'marks.list_marks'),
        ('Assessments', 'assessments.list_assessment_marks'),
        ('Results', 'results.search'),
        ('Reports', 'reports.reports_index'),
        ('Administration', [
            ('Accounts', 'users.list_users'),
            ('Faculty', 'faculty_admin.list_faculty'),
            ('Assessment settings', 'assessment_config.settings'),
            ('Audit log', 'audit_view.entries'),
        ]),
    ],
    'faculty': [
        ('My subjects', 'faculty.dashboard'),
        ('Enter marks', 'assessments.enter_assessment_marks'),
        ('Marks', 'assessments.list_assessment_marks'),
        ('Results', 'assessments.results'),
    ],
    'student': [
        ('My results', 'student.dashboard'),
        ('Marksheet', 'student.marksheet'),
    ],
}


def _entry(label, endpoint):
    return {'label': label, 'url': url_for(endpoint),
            'active': request.blueprint == endpoint.split('.')[0]}


def nav_items():
    """Menu entries for the signed-in user. A group has `children` instead of a url."""
    user = g.get('user')
    if user is None:
        return []
    items = []
    for label, target in NAV_ITEMS[user['role']]:
        if isinstance(target, list):
            children = [_entry(child_label, endpoint) for child_label, endpoint in target]
            items.append({'label': label, 'children': children,
                          'active': any(child['active'] for child in children)})
        else:
            items.append(_entry(label, target))
    return items


def init_app(app):
    app.context_processor(lambda: {'nav_items': nav_items()})
