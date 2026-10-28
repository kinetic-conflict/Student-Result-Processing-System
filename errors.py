"""User-facing error pages. Technical detail goes to the log, never to the page."""
from flask import current_app, render_template, request
from mysql.connector import Error as MySQLError

from db import DatabaseUnavailable

LOCK_CONFLICTS = (1205, 1213)   # lock wait timeout, deadlock

TITLES = {
    400: 'Request not accepted',
    403: 'Access denied',
    404: 'Page not found',
    405: 'Action not allowed',
    409: 'Please try again',
    413: 'Request too large',
    500: 'Something went wrong',
    503: 'Database unavailable',
}
MESSAGES = {
    400: 'The request could not be processed. If you were filling in a form, '
         'reload the page and try again.',
    403: 'You do not have permission to open this page.',
    404: 'That page does not exist.',
    405: 'That action is not allowed on this page.',
    409: 'Another change was being saved at the same moment. Please try again.',
    413: 'That request was too large to accept.',
    500: 'An unexpected error occurred. It has been logged.',
}


def _page(status, message=None):
    return render_template('error.html', status=status, title=TITLES[status],
                           message=message or MESSAGES.get(status, '')), status


def register_error_handlers(app):
    for status in (400, 403, 404, 405, 413):
        app.register_error_handler(status, lambda error, status=status: _page(status))

    @app.errorhandler(DatabaseUnavailable)
    def database_unavailable(error):
        return _page(503, str(error))

    @app.errorhandler(MySQLError)
    def database_error(error):
        current_app.logger.exception('Database error on %s %s', request.method, request.path)
        if getattr(error, 'errno', None) in LOCK_CONFLICTS:
            return _page(409)
        return _page(500)

    @app.errorhandler(500)
    def server_error(error):
        return _page(500)
