from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

import templating
from db import execute_query
from routes.helpers import client_ip, optional_id
from services import access, assessment_config, marks_service, result_queries
from services.marks_service import AccessDenied
from services.pagination import paginate
from services.result_service import calculate_student_result_with_assessments
from services.validation import ValidationError, parse_decimal, parse_int

assessments_bp = Blueprint('assessments', __name__, url_prefix='/assessments')

MARK_LIST_SELECT = """
    SELECT am.assessment_mark_id, am.marks_obtained,
           s.registration_number, s.full_name, sub.subject_code, sub.subject_name,
           a.assessment_code, a.assessment_name, a.maximum_marks, a.weight_percentage
    FROM assessment_marks am
    JOIN students s ON am.student_id = s.student_id
    JOIN subjects sub ON am.subject_id = sub.subject_id
    JOIN assessments a ON am.assessment_id = a.assessment_id
    WHERE 1 = 1
"""


def _id_or_none(raw):
    try:
        return parse_int('id', raw, minimum=1, required=False)
    except ValidationError:
        return None


def _existing_marks(student_id, subject_id):
    rows = execute_query(
        'SELECT a.assessment_code AS code, am.marks_obtained AS marks FROM assessment_marks am '
        'JOIN assessments a ON a.assessment_id = am.assessment_id '
        'WHERE am.student_id = %s AND am.subject_id = %s', (student_id, subject_id))
    return {row['code']: row['marks'] for row in rows}


def _parse_mark(label, raw):
    """Syntax and decimal places only. The allowed range is checked in one place: marks_service."""
    return parse_decimal(label, raw, places=2, required=False)


@assessments_bp.route('')
def list_assessment_marks():
    """Every recorded component mark the user may see, one row per mark."""
    where, params = '', []
    for name, column in (('student_id', 'am.student_id'), ('subject_id', 'am.subject_id')):
        value = optional_id(name)
        if value:
            where += f' AND {column} = %s'
            params.append(value)
    fragment, scope_params = access.scope_filter(g.user)
    where += fragment
    params += scope_params

    total = execute_query('SELECT COUNT(*) AS n FROM assessment_marks am '
                          'JOIN students s ON am.student_id = s.student_id '
                          'JOIN subjects sub ON am.subject_id = sub.subject_id '
                          f'WHERE 1 = 1{where}', tuple(params))[0]['n']
    page = paginate(total, request.args.get('page'))
    rows = execute_query(
        MARK_LIST_SELECT + where + ' ORDER BY s.registration_number, sub.subject_code, a.assessment_id'
        ' LIMIT %s OFFSET %s', (*params, page.per_page, page.offset))
    return render_template('assessments/list.html', rows=rows, page=page,
                           students=access.students_for(g.user), subjects=access.subjects_for(g.user),
                           filters={'student_id': optional_id('student_id'),
                                    'subject_id': optional_id('subject_id')})


@assessments_bp.route('/results')
def results():
    """Weighted result per student and subject, with each component mark."""
    subject_id = optional_id('subject_id')
    search = request.args.get('search', '').strip()
    listing = result_queries.weighted_results(
        g.user, subject_id=subject_id, search=search or None, raw_page=request.args.get('page'))
    return render_template('assessments/results.html', listing=listing,
                           config=assessment_config.load_config(),
                           subjects=access.subjects_for(g.user),
                           filters={'subject_id': subject_id, 'search': search})


@assessments_bp.route('/enter', methods=['GET', 'POST'])
def enter_assessment_marks():
    """Enter or correct all component marks for one student in one subject."""
    config = assessment_config.load_config()
    form = request.form if request.method == 'POST' else request.args
    entered = {item['code']: form.get(f"marks_{item['code']}", '') for item in config}
    student_id, subject_id = form.get('student_id', ''), form.get('subject_id', '')

    if request.method == 'POST':
        try:
            student_id = parse_int('Student', student_id, minimum=1)
            subject_id = parse_int('Subject', subject_id, minimum=1)
            marks = {item['code']: _parse_mark(item['code'], entered[item['code']]) for item in config}
            changed = marks_service.save_marks(g.user, subject_id, {student_id: marks},
                                               ip=client_ip())
        except ValidationError as error:
            flash(str(error), 'error')
        except AccessDenied:
            abort(403)
        else:
            flash(f'Saved {changed} mark(s).' if changed else 'No changes to save.', 'success')
            return redirect(url_for('assessments.calculate_result',
                                    student_id=student_id, subject_id=subject_id))
    elif _id_or_none(student_id) and _id_or_none(subject_id) and access.can_write_marks(
            g.user, _id_or_none(student_id), _id_or_none(subject_id)):
        saved = _existing_marks(_id_or_none(student_id), _id_or_none(subject_id))
        entered = {code: '' if code not in saved else templating.marks(saved[code]) for code in entered}
    return render_template('assessments/enter.html', config=config, entered=entered,
                           students=access.students_for(g.user), subjects=access.subjects_for(g.user),
                           selected={'student_id': str(student_id), 'subject_id': str(subject_id)})


@assessments_bp.route('/subjects/<int:subject_id>', methods=['GET', 'POST'])
def subject_grid(subject_id):
    """Mark-entry sheet: every student in the subject's cohort against every component."""
    if not access.can_manage_subject(g.user, subject_id):
        abort(403)
    subject = execute_query('SELECT * FROM subjects WHERE subject_id = %s', (subject_id,))
    if not subject:
        abort(404)
    config = assessment_config.load_config()
    students = access.students_for_subject(g.user, subject_id)
    typed = {}

    if request.method == 'POST':
        try:
            entries = {}
            for student in students:
                row = entries[student['student_id']] = {}
                for item in config:
                    field = f"m_{student['student_id']}_{item['code']}"
                    typed[field] = request.form.get(field, '')
                    row[item['code']] = _parse_mark(
                        f"{student['registration_number']} {item['code']}", typed[field])
            changed = marks_service.save_marks(g.user, subject_id, entries, ip=client_ip())
        except ValidationError as error:
            flash(str(error), 'error')
        except AccessDenied:
            abort(403)
        else:
            flash(f'Saved {changed} mark(s).' if changed else 'No changes to save.', 'success')
            return redirect(url_for('assessments.subject_grid', subject_id=subject_id))

    saved = _cohort_marks(subject_id, [s['student_id'] for s in students])
    calculation = [{'code': a['code'], 'max': a['max'], 'weight': a['weight']} for a in config]
    rows = []
    for student in students:
        marks = saved.get(student['student_id'], {})
        rows.append({'student': student, 'marks': marks,
                     'result': calculate_student_result_with_assessments(marks, calculation)})
    return render_template('assessments/grid.html', subject=subject[0], config=config, rows=rows,
                           typed=typed)


def _cohort_marks(subject_id, student_ids):
    if not student_ids:
        return {}
    placeholders = ', '.join(['%s'] * len(student_ids))
    saved = {}
    for row in execute_query(
            'SELECT am.student_id, a.assessment_code AS code, am.marks_obtained AS marks '
            'FROM assessment_marks am JOIN assessments a ON a.assessment_id = am.assessment_id '
            f'WHERE am.subject_id = %s AND am.student_id IN ({placeholders})',
            (subject_id, *student_ids)):
        saved.setdefault(row['student_id'], {})[row['code']] = row['marks']
    return saved


@assessments_bp.route('/calculate')
def calculate_result():
    """Show how one student's weighted result for one subject is made up."""
    config = assessment_config.load_config()
    student_id, subject_id = optional_id('student_id'), optional_id('subject_id')
    if not (student_id and subject_id):
        return render_template('assessments/calculate.html', result=None, config=config,
                               students=access.students_for(g.user),
                               subjects=access.subjects_for(g.user))
    if not access.can_write_marks(g.user, student_id, subject_id):
        abort(403)
    student = execute_query('SELECT * FROM students WHERE student_id = %s', (student_id,))[0]
    subject = execute_query('SELECT * FROM subjects WHERE subject_id = %s', (subject_id,))[0]
    calculation = [{'code': a['code'], 'max': a['max'], 'weight': a['weight']} for a in config]
    result = calculate_student_result_with_assessments(_existing_marks(student_id, subject_id), calculation)
    return render_template('assessments/calculate.html', result=result, student=student, subject=subject,
                           config=config, students=access.students_for(g.user),
                           subjects=access.subjects_for(g.user))


@assessments_bp.route('/<int:assessment_mark_id>/edit', methods=['GET', 'POST'])
def edit_assessment_mark(assessment_mark_id):
    """Correct a single recorded mark."""
    try:
        mark = marks_service.get_mark(g.user, assessment_mark_id)
    except AccessDenied:
        abort(403)
    except LookupError:
        abort(404)

    typed = None
    if request.method == 'POST':
        typed = request.form.get('marks_obtained', '')
        try:
            value = parse_decimal(mark['code'], typed, places=2)
            marks_service.change_mark(g.user, assessment_mark_id, value, ip=client_ip())
        except ValidationError as error:
            flash(str(error), 'error')
        except AccessDenied:
            abort(403)
        except LookupError:
            abort(404)
        else:
            flash('Assessment mark updated.', 'success')
            return redirect(url_for('assessments.list_assessment_marks'))
    return render_template('assessments/edit.html', mark=mark, typed=typed)


@assessments_bp.route('/<int:assessment_mark_id>/delete', methods=['POST'])
def delete_assessment_mark(assessment_mark_id):
    """Remove one mark. Administrators only (see ENDPOINT_ROLES in app.py)."""
    try:
        marks_service.delete_mark(g.user, assessment_mark_id, ip=client_ip())
    except AccessDenied:
        abort(403)
    except LookupError:
        abort(404)
    flash('Assessment mark deleted.', 'success')
    return redirect(url_for('assessments.list_assessment_marks'))
