"""Small helpers every template can use: number formatting and page links."""
from decimal import Decimal

from flask import request, url_for


def marks(value):
    """Show a mark without trailing zeros (40.00 -> 40); None shows as a dash."""
    if value is None:
        return '—'
    if isinstance(value, Decimal):
        return format(value.normalize(), 'f')
    return str(value)


def page_url(number):
    """The current page's URL with `page` set, keeping every other filter."""
    arguments = {key: value for key, value in request.args.items()
                 if key not in ('page', 'endpoint') and not key.startswith('_')}
    arguments['page'] = number
    return url_for(request.endpoint, **(request.view_args or {}), **arguments)


def init_app(app):
    app.jinja_env.filters['marks'] = marks
    app.context_processor(lambda: {'page_url': page_url})
