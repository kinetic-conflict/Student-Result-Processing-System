from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from routes.helpers import client_ip
from services import audit, auth_service
from services.pagination import paginate
from services.validation import ValidationError, parse_int

users_bp = Blueprint('users', __name__, url_prefix='/admin/users')


def _account_or_404(user_id):
    user = auth_service.get_user(user_id)
    if user is None:
        abort(404)
    return user


def _credentials_page(rows, title, skipped=()):
    """Show temporary passwords exactly once, in the response to the request that made them.

    They are never flashed (a flash lives in the session cookie, which the browser can read),
    never logged and never audited.
    """
    return render_template('users/credentials.html', rows=rows, title=title, skipped=skipped)


@users_bp.route('')
def list_users():
    """All login accounts, filterable by role and searchable."""
    search = request.args.get('search', '').strip()
    role = request.args.get('role', '')
    page = paginate(auth_service.count_users(search, role), request.args.get('page'))
    return render_template('users/list.html', users=auth_service.list_users(
        search, role, page.per_page, page.offset), page=page, search=search, role=role,
        roles=auth_service.ROLES, waiting_students=len(auth_service.unlinked_students()),
        waiting_faculty=len(auth_service.unlinked_faculty()))


@users_bp.route('/new', methods=['GET', 'POST'])
def create_user():
    """Create an account for an admin, a faculty member or a student, with a temporary password."""
    if request.method == 'POST':
        form = request.form
        role = form.get('role', '')
        try:
            student_id = parse_int('Student', form.get('student_id'), minimum=1, required=False) \
                if role == auth_service.ROLE_STUDENT else None
            faculty_id = parse_int('Faculty member', form.get('faculty_id'), minimum=1, required=False) \
                if role == auth_service.ROLE_FACULTY else None
            temporary = auth_service.generate_temporary_password()
            username = form.get('username', '').strip()
            user_id = auth_service.create_user(
                username, role, email=form.get('email'), student_id=student_id,
                faculty_id=faculty_id, password=temporary, must_change_password=True)
        except ValidationError as error:
            flash(str(error), 'error')
        else:
            audit.record(g.user, 'user.create', 'user', user_id, f'{username} ({role})', client_ip())
            return _credentials_page([(username, '', temporary)], 'Account created')
    return render_template(
        'users/form.html', mode='new', form=request.form,
        role_options=[(role, role.capitalize()) for role in auth_service.ROLES],
        student_options=[(s['student_id'], f"{s['registration_number']} - {s['full_name']}")
                         for s in auth_service.unlinked_students()],
        faculty_options=[(f['faculty_id'], f"{f['employee_id']} - {f['full_name']}")
                         for f in auth_service.unlinked_faculty()])


@users_bp.route('/bulk', methods=['POST'])
def create_accounts_in_bulk():
    """Create accounts for every student or faculty member who does not have one."""
    role = request.form.get('role')
    if role not in (auth_service.ROLE_STUDENT, auth_service.ROLE_FACULTY):
        abort(400)
    created, skipped = auth_service.create_accounts_for(role)
    audit.record(g.user, 'user.bulk_create', 'user', None,
                 f'{len(created)} {role} account(s) created, {len(skipped)} skipped', client_ip())
    return _credentials_page(created, 'Accounts created', skipped)


@users_bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
def edit_user(user_id):
    """Change an account's login name and email."""
    user = _account_or_404(user_id)
    if request.method == 'POST':
        try:
            auth_service.update_account(user_id, request.form.get('username'), request.form.get('email'))
        except ValidationError as error:
            flash(str(error), 'error')
        else:
            audit.record(g.user, 'user.update', 'user', user_id, request.form.get('username', ''),
                         client_ip())
            flash('Account updated.', 'success')
            return redirect(url_for('users.list_users'))
    return render_template('users/form.html', mode='edit', user=user, form=request.form)


def _set_status(user_id, active):
    user = _account_or_404(user_id)
    if not active and user_id == g.user['user_id']:
        flash('You cannot deactivate your own account.', 'error')
        return redirect(url_for('users.list_users'))
    try:
        auth_service.set_active(user_id, active)
    except ValidationError as error:
        flash(str(error), 'error')
    else:
        audit.record(g.user, 'user.activate' if active else 'user.deactivate', 'user', user_id,
                     user['username'], client_ip())
        flash('Account activated.' if active else 'Account deactivated and signed out.', 'success')
    return redirect(url_for('users.list_users'))


@users_bp.route('/<int:user_id>/deactivate', methods=['POST'])
def deactivate_user(user_id):
    return _set_status(user_id, False)


@users_bp.route('/<int:user_id>/activate', methods=['POST'])
def activate_user(user_id):
    return _set_status(user_id, True)


@users_bp.route('/<int:user_id>/reset-password', methods=['POST'])
def reset_password(user_id):
    """Replace the password with a new temporary one, shown once, and sign the user out."""
    user = _account_or_404(user_id)
    temporary = auth_service.generate_temporary_password()
    auth_service.set_password(user_id, temporary, must_change_password=True)
    audit.record(g.user, 'user.reset_password', 'user', user_id, user['username'], client_ip())
    return _credentials_page([(user['username'], '', temporary)], 'Password reset')
