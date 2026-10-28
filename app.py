import os
import sys

from dotenv import load_dotenv
from flask import Flask

import cli
import navigation
import security
import templating
from config import ConfigError, build_config
from errors import register_error_handlers
from routes.admin import admin_bp
from routes.assessments import assessments_bp
from routes.assessment_config import assessment_config_bp
from routes.audit_view import audit_view_bp
from routes.auth import auth_bp
from routes.examinations import examinations_bp
from routes.faculty import faculty_bp
from routes.faculty_admin import faculty_admin_bp
from routes.main import main_bp
from routes.marks import marks_bp
from routes.reports import reports_bp
from routes.results import results_bp
from routes.student import student_bp
from routes.students import students_bp
from routes.subjects import subjects_bp
from routes.users_admin import users_bp
from services.auth_service import ROLE_ADMIN, ROLE_FACULTY, ROLE_STUDENT

# Who may open each blueprint. This is the one place to audit access.
# None means any signed-in user; the login page itself is exempt (security.PUBLIC_ENDPOINTS).
BLUEPRINTS = (
    (auth_bp, None),
    (main_bp, None),
    (admin_bp, (ROLE_ADMIN,)),
    (students_bp, (ROLE_ADMIN,)),
    (subjects_bp, (ROLE_ADMIN,)),
    (examinations_bp, (ROLE_ADMIN,)),
    (marks_bp, (ROLE_ADMIN,)),
    (assessments_bp, (ROLE_ADMIN, ROLE_FACULTY)),
    (results_bp, (ROLE_ADMIN, ROLE_FACULTY)),
    (faculty_bp, (ROLE_FACULTY,)),
    (student_bp, (ROLE_STUDENT,)),
    (reports_bp, (ROLE_ADMIN,)),
    (users_bp, (ROLE_ADMIN,)),
    (faculty_admin_bp, (ROLE_ADMIN,)),
    (assessment_config_bp, (ROLE_ADMIN,)),
    (audit_view_bp, (ROLE_ADMIN,)),
)

# Exceptions to the blueprint rule above, one view at a time.
ENDPOINT_ROLES = {
    'assessments.delete_assessment_mark': (ROLE_ADMIN,),
}


def create_app(settings=None, testing=False):
    """Build the Flask app.

    `settings` is a mapping of environment-style names (see config.py). When it
    is omitted, .env and the process environment are used.
    """
    if settings is None:
        load_dotenv()
        settings = os.environ

    app = Flask(__name__)
    app.config.update(build_config(settings))
    app.config['TESTING'] = testing

    security.init_app(app, {blueprint.name: roles for blueprint, roles in BLUEPRINTS},
                      ENDPOINT_ROLES)
    navigation.init_app(app)
    templating.init_app(app)
    cli.init_app(app)
    register_error_handlers(app)
    for blueprint, _ in BLUEPRINTS:
        app.register_blueprint(blueprint)
    return app


def main():
    try:
        app = create_app()
    except ConfigError as error:
        sys.exit(str(error))
    app.run(debug=app.config['DEBUG'], host=app.config['APP_HOST'], port=app.config['APP_PORT'])


if __name__ == '__main__':
    main()
