"""The Flask side of authentication: sessions, CSRF, route guards, response headers.

Account rules (hashing, lookup, status) live in services/auth_service.py.
Which roles may reach which blueprint is declared in one place: BLUEPRINTS in app.py.
"""
import hmac
import secrets
import time
from urllib.parse import urlsplit

from flask import abort, current_app, g, redirect, request, session, url_for
from markupsafe import Markup

from services import auth_service
from services.login_throttle import LoginThrottle

PUBLIC_ENDPOINTS = frozenset({'auth.login', 'static'})
PASSWORD_CHANGE_ENDPOINTS = frozenset({'auth.change_password', 'auth.logout', 'static'})
HOME_ENDPOINTS = {
    auth_service.ROLE_ADMIN: 'admin.dashboard',
    auth_service.ROLE_FACULTY: 'faculty.dashboard',
    auth_service.ROLE_STUDENT: 'student.dashboard',
}
SAFE_METHODS = frozenset({'GET', 'HEAD', 'OPTIONS'})
SESSION_MAX_AGE_SECONDS = 12 * 3600  # absolute cap, however active the user is

CONTENT_SECURITY_POLICY = '; '.join([
    "default-src 'self'",
    "script-src 'self' https://cdn.jsdelivr.net",
    "style-src 'self' https://cdn.jsdelivr.net",
    "font-src 'self' https://cdn.jsdelivr.net",
    "img-src 'self' data:",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
])


# ---- CSRF -------------------------------------------------------------------

def csrf_token():
    if '_csrf' not in session:
        session['_csrf'] = secrets.token_urlsafe(32)
    return session['_csrf']


def csrf_input():
    return Markup('<input type="hidden" name="csrf_token" value="%s">') % csrf_token()


def _check_csrf():
    if request.method in SAFE_METHODS:
        return
    sent = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token') or ''
    expected = session.get('_csrf', '')
    # compare bytes: compare_digest raises on non-ASCII text
    if not expected or not hmac.compare_digest(sent.encode(), expected.encode()):
        abort(400)


# ---- who is signed in -------------------------------------------------------

def login_user(user):
    """Start a fresh session. Clearing first defeats session fixation."""
    session.clear()
    session.permanent = True
    session['uid'] = user['user_id']
    session['sv'] = user['session_version']
    session['iat'] = int(time.time())


def logout_user():
    if g.get('user'):
        auth_service.revoke_sessions(g.user['user_id'])
    session.clear()


def refresh_session(user_id):
    """Re-sync the cookie after a deliberate version bump (e.g. the user's own password change)."""
    session['sv'] = auth_service.get_user(user_id)['session_version']


def home_url(user):
    return url_for(HOME_ENDPOINTS[user['role']])


def safe_next_url(target):
    """`target` if it is a path on this site, else None. Blocks open redirects."""
    if not target or not target.startswith('/') or target.startswith('//') or '\\' in target:
        return None
    if any(char.isspace() or not char.isprintable() for char in target):
        return None   # control characters and spaces: some browsers and servers read them oddly
    parts = urlsplit(target)
    return target if not parts.scheme and not parts.netloc else None


def _load_user():
    g.user = None
    if request.endpoint == 'static':
        return
    uid = session.get('uid')
    if not uid:
        return
    user = auth_service.get_user(uid)
    fresh = time.time() - session.get('iat', 0) <= SESSION_MAX_AGE_SECONDS
    if user and user['is_active'] and fresh and session.get('sv') == user['session_version']:
        g.user = user
    else:
        session.clear()


def _require_login():
    endpoint = request.endpoint
    if endpoint is None or endpoint in PUBLIC_ENDPOINTS:
        return
    if g.user is None:
        target = request.full_path.rstrip('?') if request.method in {'GET', 'HEAD'} else None
        return redirect(url_for('auth.login', next=target))
    if g.user['must_change_password'] and endpoint not in PASSWORD_CHANGE_ENDPOINTS:
        return redirect(url_for('auth.change_password'))


def allowed_roles(app, endpoint):
    """Roles allowed at `endpoint`: its own entry if it has one, else its blueprint's.
    None means any signed-in user."""
    rules = app.extensions['access_rules']
    if endpoint in rules['endpoints']:
        return rules['endpoints'][endpoint]
    # a blueprint missing from the registry is open to nobody, not to everybody
    return rules['blueprints'].get(endpoint.split('.')[0], ())


def _require_role():
    """Reject signed-in users whose role is not allowed at this endpoint."""
    if request.endpoint is None or request.endpoint in PUBLIC_ENDPOINTS or g.user is None:
        return
    roles = allowed_roles(current_app, request.endpoint)
    if roles is not None and g.user['role'] not in roles:
        abort(403)


# ---- login throttling -------------------------------------------------------

def login_throttles():
    return current_app.extensions['login_throttles']


def client_address():
    return request.remote_addr or 'unknown'


# ---- response headers -------------------------------------------------------

def _set_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['Content-Security-Policy'] = CONTENT_SECURITY_POLICY
    if request.endpoint != 'static':
        response.headers['Cache-Control'] = 'no-store'
    return response


def init_app(app, blueprint_roles, endpoint_roles=None):
    """Declare who may go where.

    `blueprint_roles` maps blueprint name -> allowed roles (None = any signed-in user; a name that
    is missing means nobody).
    `endpoint_roles` maps "blueprint.view" -> roles and overrides its blueprint.
    """
    config = app.config
    app.extensions['access_rules'] = {'blueprints': blueprint_roles,
                                      'endpoints': endpoint_roles or {}}
    window = config['LOGIN_WINDOW_SECONDS']
    app.extensions['login_throttles'] = (
        LoginThrottle(config['LOGIN_MAX_FAILURES'], window),         # per account + address
        LoginThrottle(config['LOGIN_MAX_FAILURES_PER_IP'], window),  # per address
    )
    app.before_request(_check_csrf)
    app.before_request(_load_user)
    app.before_request(_require_login)
    app.before_request(_require_role)
    app.after_request(_set_headers)
    app.context_processor(lambda: {'csrf_input': csrf_input, 'csrf_token': csrf_token,
                                   'current_user': g.get('user')})
