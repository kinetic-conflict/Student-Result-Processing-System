import unicodedata

from flask import (Blueprint, current_app, flash, g, redirect, render_template, request,
                   session, url_for)

import security
from services import auth_service
from services.validation import ValidationError

auth_bp = Blueprint('auth', __name__)

BAD_LOGIN = 'Invalid username or password.'
TOO_MANY_LOGINS = 'Too many failed attempts. Wait a few minutes and try again.'


def _fold(name):
    """Lower-case and strip accents, as the database's collation does when it matches names."""
    decomposed = unicodedata.normalize('NFKD', name)
    return ''.join(char for char in decomposed if not unicodedata.combining(char)).casefold()


def _render_login(error=None, status=200, username=''):
    return render_template('login.html', error=error, username=username,
                           next=request.args.get('next', '')), status


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Sign in with a username or email and a password."""
    if g.user is not None:
        return redirect(security.home_url(g.user))
    if request.method == 'GET':
        return _render_login()

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    if not username or not password:
        return _render_login('Enter your username or email and your password.', username=username)

    per_account, per_address = security.login_throttles()
    address = security.client_address()
    account_key = f'{_fold(username)}|{address}'
    if per_account.is_blocked(account_key) or per_address.is_blocked(address):
        current_app.logger.warning('Login throttled for address %s', address)
        return _render_login(TOO_MANY_LOGINS, status=429, username=username)

    user = auth_service.authenticate(username, password)
    if user is None:
        per_account.record_failure(account_key)
        per_address.record_failure(address)
        return _render_login(BAD_LOGIN, username=username)

    per_account.reset(account_key)
    security.login_user(user)
    if user['must_change_password']:
        return redirect(url_for('auth.change_password'))
    return redirect(security.safe_next_url(request.args.get('next')) or security.home_url(user))


@auth_bp.route('/logout', methods=['POST'])
def logout():
    security.logout_user()
    flash('You have been signed out.', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/account/password', methods=['GET', 'POST'])
def change_password():
    """Let a signed-in user choose a new password (required after a temporary one)."""
    if request.method == 'POST':
        current = request.form.get('current_password', '')
        new = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')
        attempts, _ = security.login_throttles()
        attempt_key = f"password|{g.user['user_id']}"
        try:
            if attempts.is_blocked(attempt_key):
                raise ValidationError('Too many incorrect attempts. Wait a few minutes and try again.')
            if not auth_service.verify_password(g.user['user_id'], current):
                attempts.record_failure(attempt_key)
                raise ValidationError('Your current password is incorrect.')
            if new != confirm:
                raise ValidationError('The new passwords do not match.')
            if new == current:
                raise ValidationError('The new password must be different from the current one.')
            auth_service.set_password(g.user['user_id'], new, must_change_password=False)
        except ValidationError as error:
            flash(str(error), 'error')
        else:
            attempts.reset(attempt_key)
            security.refresh_session(g.user['user_id'])
            flash('Your password has been changed.', 'success')
            return redirect(security.home_url(g.user))
    return render_template('change_password.html', forced=bool(g.user['must_change_password']))
