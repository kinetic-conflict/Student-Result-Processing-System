from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from mysql.connector import Error as MySQLError

from db import execute_query, execute_update
from routes.helpers import client_ip
from services import audit
from services.result_service import process_marks_with_result
from services.validation import (ValidationError, clean_text, parse_academic_year, parse_date,
                                 parse_int)

examinations_bp = Blueprint('examinations', __name__)


def _parse(form):
    return (
        clean_text('Examination name', form.get('exam_name'), 100),
        parse_academic_year('Academic year', form.get('academic_year'), required=True),
        parse_int('Semester', form.get('semester'), minimum=1, maximum=10),
        parse_date('Exam date', form.get('exam_date'), required=False),
    )


def _ensure_new(values, exam_id=0):
    """One examination per name, academic year and semester (the database compares names ignoring case).

    `exam_id` is the examination being edited, so saving it again unchanged is not a clash.
    """
    name, year, semester, _ = values
    if execute_query('SELECT 1 FROM examinations WHERE exam_name = %s AND academic_year = %s '
                     'AND semester = %s AND exam_id <> %s', (name, year, semester, exam_id)):
        raise ValidationError('An examination with this name, academic year and semester already exists.')


def _find(exam_id):
    rows = execute_query('SELECT * FROM examinations WHERE exam_id = %s', (exam_id,))
    return rows[0] if rows else None


@examinations_bp.route('/examinations')
def list_examinations():
    """All examinations, newest first."""
    return render_template('examinations.html', examinations=execute_query(
        'SELECT * FROM examinations ORDER BY exam_date DESC, exam_name'))


@examinations_bp.route('/examinations/add', methods=['GET', 'POST'])
def add_examination():
    """Add a new examination."""
    if request.method == 'POST':
        try:
            values = _parse(request.form)
            _ensure_new(values)
            exam_id = execute_update(
                'INSERT INTO examinations (exam_name, academic_year, semester, exam_date) '
                'VALUES (%s, %s, %s, %s)', values)
            audit.record(g.user, 'examination.create', 'examination', exam_id, values[0], client_ip())
        except ValidationError as error:
            flash(str(error), 'error')
        except MySQLError:
            flash('The examination could not be saved. Please try again.', 'error')
        else:
            flash('Examination added.', 'success')
            return redirect(url_for('examinations.list_examinations'))
    return render_template('examinations.html', action='add', form=request.form)


@examinations_bp.route('/examinations/<int:exam_id>/edit', methods=['GET', 'POST'])
def edit_examination(exam_id):
    """Edit examination information."""
    examination = _find(exam_id)
    if examination is None:
        flash('Examination not found.', 'error')
        return redirect(url_for('examinations.list_examinations'))
    if request.method == 'POST':
        try:
            values = _parse(request.form)
            _ensure_new(values, exam_id)
            execute_update(
                'UPDATE examinations SET exam_name = %s, academic_year = %s, semester = %s, '
                'exam_date = %s WHERE exam_id = %s', (*values, exam_id))
            audit.record(g.user, 'examination.update', 'examination', exam_id, values[0], client_ip())
        except ValidationError as error:
            flash(str(error), 'error')
        except MySQLError:
            flash('The examination could not be saved. Please try again.', 'error')
        else:
            flash('Examination updated.', 'success')
            return redirect(url_for('examinations.list_examinations'))
    return render_template('examinations.html', action='edit', examination=examination, form=request.form)


@examinations_bp.route('/examinations/<int:exam_id>/results')
def examination_results(exam_id):
    """Every mark recorded for one examination."""
    examination = _find(exam_id)
    if examination is None:
        flash('Examination not found.', 'error')
        return redirect(url_for('examinations.list_examinations'))
    marks = process_marks_with_result(execute_query(
        'SELECT m.mark_id, s.student_id, s.registration_number, s.full_name, sub.subject_code, '
        'sub.subject_name, m.marks_obtained, m.maximum_marks '
        'FROM marks m JOIN students s ON m.student_id = s.student_id '
        'JOIN subjects sub ON m.subject_id = sub.subject_id WHERE m.exam_id = %s '
        'ORDER BY s.registration_number, sub.subject_code', (exam_id,)))
    return render_template('examinations.html', action='results', examination=examination, marks=marks)
