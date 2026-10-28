from decimal import Decimal

from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from mysql.connector import Error as MySQLError

from db import (execute_query, execute_update, is_duplicate_error, is_missing_reference_error)
from routes.helpers import client_ip, optional_id
from services import audit
from services.pagination import paginate
from services.result_service import process_marks_with_result
from services.validation import ValidationError, parse_decimal, parse_int

marks_bp = Blueprint('marks', __name__)

MAX_MARKS_LIMIT = Decimal('9999.99')   # the columns are DECIMAL(6,2)

LIST_FROM = """
    FROM marks m
    JOIN students s ON m.student_id = s.student_id
    JOIN subjects sub ON m.subject_id = sub.subject_id
    JOIN examinations e ON m.exam_id = e.exam_id
    WHERE 1 = 1
"""


def _parse_scores(form):
    obtained = parse_decimal('Marks obtained', form.get('marks_obtained'), minimum=0, maximum=MAX_MARKS_LIMIT)
    maximum = parse_decimal('Maximum marks', form.get('maximum_marks'), maximum=MAX_MARKS_LIMIT)
    if maximum <= 0:
        raise ValidationError('Maximum marks must be greater than 0.')
    if obtained > maximum:
        raise ValidationError('Marks obtained cannot exceed maximum marks.')
    return obtained, maximum


def _dropdowns():
    """The lists behind the filter boxes, plus (value, label) pairs for the add form."""
    students = execute_query('SELECT student_id, registration_number, full_name FROM students '
                             'ORDER BY registration_number')
    subjects = execute_query('SELECT subject_id, subject_code, subject_name FROM subjects '
                             'ORDER BY subject_code')
    examinations = execute_query('SELECT exam_id, exam_name, academic_year FROM examinations '
                                 'ORDER BY exam_date DESC, exam_id DESC')
    return {
        'students': students, 'subjects': subjects, 'examinations': examinations,
        'student_options': [(s['student_id'], f"{s['registration_number']} - {s['full_name']}") for s in students],
        'subject_options': [(s['subject_id'], f"{s['subject_code']} - {s['subject_name']}") for s in subjects],
        'exam_options': [(e['exam_id'], f"{e['exam_name']} ({e['academic_year']})") for e in examinations],
    }


@marks_bp.route('/marks')
def list_marks():
    """Per-examination marks, filterable by student, subject and examination."""
    filters = {name: optional_id(name) for name in ('student_id', 'subject_id', 'exam_id')}
    where, params = '', []
    for name, column in (('student_id', 'm.student_id'), ('subject_id', 'm.subject_id'),
                         ('exam_id', 'm.exam_id')):
        if filters[name]:
            where += f' AND {column} = %s'
            params.append(filters[name])
    total = execute_query(f'SELECT COUNT(*) AS n {LIST_FROM}{where}', tuple(params))[0]['n']
    page = paginate(total, request.args.get('page'))
    marks = process_marks_with_result(execute_query(
        'SELECT m.*, s.registration_number, s.full_name, sub.subject_code, sub.subject_name, '
        f'e.exam_name, e.academic_year {LIST_FROM}{where} '
        'ORDER BY e.exam_date DESC, s.registration_number, sub.subject_code LIMIT %s OFFSET %s',
        (*params, page.per_page, page.offset)))
    return render_template('marks.html', marks=marks, page=page, filters=filters, **_dropdowns())


@marks_bp.route('/marks/add', methods=['GET', 'POST'])
def add_mark():
    """Add a per-examination mark."""
    if request.method == 'POST':
        try:
            student_id = parse_int('Student', request.form.get('student_id'), minimum=1)
            subject_id = parse_int('Subject', request.form.get('subject_id'), minimum=1)
            exam_id = parse_int('Examination', request.form.get('exam_id'), minimum=1)
            obtained, maximum = _parse_scores(request.form)
            mark_id = execute_update(
                'INSERT INTO marks (student_id, subject_id, exam_id, marks_obtained, maximum_marks) '
                'VALUES (%s, %s, %s, %s, %s)', (student_id, subject_id, exam_id, obtained, maximum))
            audit.record(g.user, 'legacy_mark.create', 'mark', mark_id,
                         f'student {student_id} subject {subject_id} exam {exam_id}: {obtained}/{maximum}',
                         client_ip())
        except ValidationError as error:
            flash(str(error), 'error')
        except MySQLError as error:
            if is_duplicate_error(error):
                flash('Marks for this student, subject and examination already exist.', 'error')
            elif is_missing_reference_error(error):
                flash('Choose an existing student, subject and examination.', 'error')
            else:
                flash('The marks could not be saved. Please try again.', 'error')
        else:
            flash('Marks added.', 'success')
            return redirect(url_for('marks.list_marks'))
    return render_template('marks.html', action='add', form=request.form, **_dropdowns())


def _find(mark_id):
    rows = execute_query(
        'SELECT m.*, s.registration_number, s.full_name, sub.subject_code, sub.subject_name, '
        'e.exam_name, e.academic_year '
        'FROM marks m JOIN students s ON m.student_id = s.student_id '
        'JOIN subjects sub ON m.subject_id = sub.subject_id '
        'JOIN examinations e ON m.exam_id = e.exam_id WHERE m.mark_id = %s', (mark_id,))
    return rows[0] if rows else None


@marks_bp.route('/marks/<int:mark_id>/edit', methods=['GET', 'POST'])
def edit_mark(mark_id):
    """Change the scores of an existing per-examination mark."""
    mark = _find(mark_id)
    if mark is None:
        flash('Marks record not found.', 'error')
        return redirect(url_for('marks.list_marks'))
    if request.method == 'POST':
        try:
            obtained, maximum = _parse_scores(request.form)
            execute_update('UPDATE marks SET marks_obtained = %s, maximum_marks = %s WHERE mark_id = %s',
                           (obtained, maximum, mark_id))
            audit.record(g.user, 'legacy_mark.update', 'mark', mark_id,
                         f"{mark['registration_number']} {mark['subject_code']}: "
                         f"{mark['marks_obtained']}/{mark['maximum_marks']} -> {obtained}/{maximum}",
                         client_ip())
        except ValidationError as error:
            flash(str(error), 'error')
        except MySQLError:
            flash('The marks could not be saved. Please try again.', 'error')
        else:
            flash('Marks updated.', 'success')
            return redirect(url_for('marks.list_marks'))
    return render_template('marks.html', action='edit', mark=mark, form=request.form)


@marks_bp.route('/marks/<int:mark_id>/delete', methods=['POST'])
def delete_mark(mark_id):
    """Delete a per-examination mark."""
    mark = _find(mark_id)
    if mark is None:
        flash('Marks record not found.', 'error')
        return redirect(url_for('marks.list_marks'))
    try:
        execute_update('DELETE FROM marks WHERE mark_id = %s', (mark_id,))
    except MySQLError:
        flash('The marks could not be deleted. Please try again.', 'error')
    else:
        audit.record(g.user, 'legacy_mark.delete', 'mark', mark_id,
                     f"{mark['registration_number']} {mark['subject_code']}: "
                     f"{mark['marks_obtained']}/{mark['maximum_marks']}", client_ip())
        flash('Marks deleted.', 'success')
    return redirect(url_for('marks.list_marks'))
