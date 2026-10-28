from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from mysql.connector import Error as MySQLError

from db import execute_query, execute_update, is_duplicate_error, like_contains
from routes.helpers import client_ip
from services import audit, faculty_service
from services.pagination import paginate
from services.validation import ValidationError, clean_text, parse_email, parse_int

faculty_admin_bp = Blueprint('faculty_admin', __name__, url_prefix='/admin/faculty')


def _parse(form):
    return {
        'full_name': clean_text('Full name', form.get('full_name'), 100),
        'email': parse_email('Email', form.get('email')),
        'department': clean_text('Department', form.get('department'), 50, required=False),
    }


def _faculty_or_404(faculty_id):
    rows = execute_query('SELECT * FROM faculty WHERE faculty_id = %s', (faculty_id,))
    if not rows:
        abort(404)
    return rows[0]


@faculty_admin_bp.route('')
def list_faculty():
    """Faculty members with their account state and number of assigned subjects."""
    search = request.args.get('search', '').strip()
    where, params = '', ()
    if search:
        pattern = like_contains(search)
        where, params = (' WHERE f.employee_id LIKE %s OR f.full_name LIKE %s OR f.email LIKE %s',
                         (pattern,) * 3)
    total = execute_query(f'SELECT COUNT(*) AS n FROM faculty f{where}', params)[0]['n']
    page = paginate(total, request.args.get('page'))
    faculty = execute_query(
        'SELECT f.*, (SELECT COUNT(*) FROM faculty_assignments fa WHERE fa.faculty_id = f.faculty_id) '
        'AS subject_count, (SELECT u.username FROM users u WHERE u.faculty_id = f.faculty_id) AS username '
        f'FROM faculty f{where} ORDER BY f.employee_id LIMIT %s OFFSET %s',
        (*params, page.per_page, page.offset))
    return render_template('faculty_admin/list.html', faculty=faculty, page=page, search=search)


@faculty_admin_bp.route('/new', methods=['GET', 'POST'])
def new_faculty():
    if request.method == 'POST':
        try:
            employee_id = clean_text('Employee ID', request.form.get('employee_id'), 20)
            details = _parse(request.form)
            faculty_id = execute_update(
                'INSERT INTO faculty (employee_id, full_name, email, department) VALUES (%s, %s, %s, %s)',
                (employee_id, details['full_name'], details['email'], details['department']))
            audit.record(g.user, 'faculty.create', 'faculty', faculty_id, employee_id, client_ip())
        except ValidationError as error:
            flash(str(error), 'error')
        except MySQLError as error:
            flash('A faculty member with that employee ID or email already exists.'
                  if is_duplicate_error(error) else 'The record could not be saved. Please try again.',
                  'error')
        else:
            flash('Faculty member added. Create their login on the Accounts page.', 'success')
            return redirect(url_for('faculty_admin.list_faculty'))
    return render_template('faculty_admin/form.html', mode='new', form=request.form)


@faculty_admin_bp.route('/<int:faculty_id>/edit', methods=['GET', 'POST'])
def edit_faculty(faculty_id):
    member = _faculty_or_404(faculty_id)
    if request.method == 'POST':
        try:
            details = _parse(request.form)
            execute_update('UPDATE faculty SET full_name = %s, email = %s, department = %s '
                           'WHERE faculty_id = %s',
                           (details['full_name'], details['email'], details['department'], faculty_id))
            audit.record(g.user, 'faculty.update', 'faculty', faculty_id, member['employee_id'],
                         client_ip())
        except ValidationError as error:
            flash(str(error), 'error')
        except MySQLError as error:
            flash('Another faculty member already uses that email.' if is_duplicate_error(error)
                  else 'The record could not be saved. Please try again.', 'error')
        else:
            flash('Faculty member updated.', 'success')
            return redirect(url_for('faculty_admin.list_faculty'))
    return render_template('faculty_admin/form.html', mode='edit', member=member, form=request.form)


def _set_status(faculty_id, active):
    member = _faculty_or_404(faculty_id)
    faculty_service.set_active(faculty_id, active)
    audit.record(g.user, 'faculty.activate' if active else 'faculty.deactivate', 'faculty',
                 faculty_id, member['employee_id'], client_ip())
    flash('Faculty member activated, with their login.' if active
          else 'Faculty member deactivated. Their login is disabled and they are signed out.', 'success')
    return redirect(url_for('faculty_admin.list_faculty'))


@faculty_admin_bp.route('/<int:faculty_id>/deactivate', methods=['POST'])
def deactivate_faculty(faculty_id):
    return _set_status(faculty_id, False)


@faculty_admin_bp.route('/<int:faculty_id>/activate', methods=['POST'])
def activate_faculty(faculty_id):
    return _set_status(faculty_id, True)


@faculty_admin_bp.route('/<int:faculty_id>/assignments')
def assignments(faculty_id):
    return render_template('faculty_admin/assignments.html', member=_faculty_or_404(faculty_id),
                           assigned=faculty_service.assigned_subjects(faculty_id),
                           available=faculty_service.unassigned_subjects(faculty_id))


@faculty_admin_bp.route('/<int:faculty_id>/assignments/add', methods=['POST'])
def add_assignment(faculty_id):
    member = _faculty_or_404(faculty_id)
    try:
        subject_id = parse_int('Subject', request.form.get('subject_id'), minimum=1)
        faculty_service.assign_subject(faculty_id, subject_id)
    except ValidationError as error:
        flash(str(error), 'error')
    else:
        audit.record(g.user, 'faculty.assign', 'faculty', faculty_id,
                     f"{member['employee_id']} <- subject {subject_id}", client_ip())
        flash('Subject assigned.', 'success')
    return redirect(url_for('faculty_admin.assignments', faculty_id=faculty_id))


@faculty_admin_bp.route('/<int:faculty_id>/assignments/<int:assignment_id>/remove', methods=['POST'])
def remove_assignment(faculty_id, assignment_id):
    member = _faculty_or_404(faculty_id)
    if not faculty_service.unassign(faculty_id, assignment_id):
        abort(404)
    audit.record(g.user, 'faculty.unassign', 'faculty', faculty_id,
                 f"{member['employee_id']} -x assignment {assignment_id}", client_ip())
    flash('Assignment removed.', 'success')
    return redirect(url_for('faculty_admin.assignments', faculty_id=faculty_id))
