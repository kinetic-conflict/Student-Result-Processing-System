from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from mysql.connector import Error as MySQLError

from db import execute_query, execute_update, is_duplicate_error, is_referenced_error, like_contains
from routes.helpers import client_ip
from services import audit
from services.exam_results import student_exam_results
from services.pagination import paginate
from services.validation import (ValidationError, clean_text, parse_academic_year, parse_email,
                                 parse_int)

students_bp = Blueprint('students', __name__)


def _parse_details(form):
    """The editable fields. The registration number is chosen once, at creation."""
    return {
        'full_name': clean_text('Full name', form.get('full_name'), 100),
        'email': parse_email('Email', form.get('email')),
        'department': clean_text('Department', form.get('department'), 50, required=False),
        'semester': parse_int('Semester', form.get('semester'), minimum=1, maximum=10, required=False),
        'academic_year': parse_academic_year('Academic year', form.get('academic_year')),
    }


def _find(student_id):
    rows = execute_query('SELECT * FROM students WHERE student_id = %s', (student_id,))
    return rows[0] if rows else None


@students_bp.route('/students')
def list_students():
    """All students, searchable by registration number or name."""
    search = request.args.get('search', '').strip()
    where, params = '', ()
    if search:
        pattern = like_contains(search)
        where, params = ' WHERE registration_number LIKE %s OR full_name LIKE %s', (pattern, pattern)
    total = execute_query(f'SELECT COUNT(*) AS n FROM students{where}', params)[0]['n']
    page = paginate(total, request.args.get('page'))
    students = execute_query(
        f'SELECT * FROM students{where} ORDER BY registration_number LIMIT %s OFFSET %s',
        (*params, page.per_page, page.offset))
    return render_template('students.html', students=students, search=search, page=page)


@students_bp.route('/students/add', methods=['GET', 'POST'])
def add_student():
    """Add a new student."""
    if request.method == 'POST':
        try:
            registration = clean_text('Registration number', request.form.get('registration_number'), 20)
            details = _parse_details(request.form)
            student_id = execute_update(
                'INSERT INTO students (registration_number, full_name, email, department, semester, '
                'academic_year) VALUES (%s, %s, %s, %s, %s, %s)',
                (registration, details['full_name'], details['email'], details['department'],
                 details['semester'], details['academic_year']))
            audit.record(g.user, 'student.create', 'student', student_id, registration, client_ip())
        except ValidationError as error:
            flash(str(error), 'error')
        except MySQLError as error:
            flash('A student with that registration number or email already exists.'
                  if is_duplicate_error(error) else 'The student could not be saved. Please try again.',
                  'error')
        else:
            flash('Student added.', 'success')
            return redirect(url_for('students.list_students'))
    return render_template('students.html', action='add', form=request.form)


@students_bp.route('/students/<int:student_id>')
def view_student(student_id):
    """One student with their examination results."""
    student = _find(student_id)
    if student is None:
        flash('Student not found.', 'error')
        return redirect(url_for('students.list_students'))
    return render_template('students.html', action='view', student=student,
                           exams=student_exam_results(student_id))


@students_bp.route('/students/<int:student_id>/edit', methods=['GET', 'POST'])
def edit_student(student_id):
    """Edit student information."""
    student = _find(student_id)
    if student is None:
        flash('Student not found.', 'error')
        return redirect(url_for('students.list_students'))
    if request.method == 'POST':
        try:
            details = _parse_details(request.form)
            execute_update(
                'UPDATE students SET full_name = %s, email = %s, department = %s, semester = %s, '
                'academic_year = %s WHERE student_id = %s',
                (details['full_name'], details['email'], details['department'], details['semester'],
                 details['academic_year'], student_id))
            audit.record(g.user, 'student.update', 'student', student_id,
                         student['registration_number'], client_ip())
        except ValidationError as error:
            flash(str(error), 'error')
        except MySQLError as error:
            flash('Another student already uses that email.' if is_duplicate_error(error)
                  else 'The student could not be saved. Please try again.', 'error')
        else:
            flash('Student updated.', 'success')
            return redirect(url_for('students.list_students'))
    return render_template('students.html', action='edit', student=student, form=request.form)


@students_bp.route('/students/<int:student_id>/delete', methods=['POST'])
def delete_student(student_id):
    """Delete a student and, by cascade, all of their marks."""
    student = _find(student_id)
    if student is None:
        flash('Student not found.', 'error')
        return redirect(url_for('students.list_students'))
    try:
        execute_update('DELETE FROM students WHERE student_id = %s', (student_id,))
    except MySQLError as error:
        flash('This student has a login account, so the record cannot be deleted. '
              'Deactivate the account instead.' if is_referenced_error(error)
              else 'The student could not be deleted. Please try again.', 'error')
    else:
        audit.record(g.user, 'student.delete', 'student', student_id,
                     student['registration_number'], client_ip())
        flash('Student deleted.', 'success')
    return redirect(url_for('students.list_students'))
