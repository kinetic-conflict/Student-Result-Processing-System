from decimal import Decimal

from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from mysql.connector import Error as MySQLError

from db import execute_query, execute_update, is_duplicate_error, like_contains, transaction
from routes.helpers import client_ip
from services import audit
from services.pagination import paginate
from services.validation import ValidationError, clean_text, parse_decimal, parse_int

subjects_bp = Blueprint('subjects', __name__)


def _parse_details(form):
    return {
        'subject_name': clean_text('Subject name', form.get('subject_name'), 100),
        'credits': parse_decimal('Credits', form.get('credits'), minimum=Decimal('0.1'), maximum=10, places=1),
        'semester': parse_int('Semester', form.get('semester'), minimum=1, maximum=10),
    }


def _find(subject_id):
    rows = execute_query('SELECT * FROM subjects WHERE subject_id = %s', (subject_id,))
    return rows[0] if rows else None


@subjects_bp.route('/subjects')
def list_subjects():
    """All subjects, searchable by code or name."""
    search = request.args.get('search', '').strip()
    where, params = '', ()
    if search:
        pattern = like_contains(search)
        where, params = ' WHERE subject_code LIKE %s OR subject_name LIKE %s', (pattern, pattern)
    total = execute_query(f'SELECT COUNT(*) AS n FROM subjects{where}', params)[0]['n']
    page = paginate(total, request.args.get('page'))
    subjects = execute_query(
        f'SELECT * FROM subjects{where} ORDER BY subject_code LIMIT %s OFFSET %s',
        (*params, page.per_page, page.offset))
    return render_template('subjects.html', subjects=subjects, search=search, page=page)


@subjects_bp.route('/subjects/add', methods=['GET', 'POST'])
def add_subject():
    """Add a new subject."""
    if request.method == 'POST':
        try:
            code = clean_text('Subject code', request.form.get('subject_code'), 20)
            details = _parse_details(request.form)
            subject_id = execute_update(
                'INSERT INTO subjects (subject_code, subject_name, credits, semester) '
                'VALUES (%s, %s, %s, %s)',
                (code, details['subject_name'], details['credits'], details['semester']))
            audit.record(g.user, 'subject.create', 'subject', subject_id, code, client_ip())
        except ValidationError as error:
            flash(str(error), 'error')
        except MySQLError as error:
            flash('That subject code already exists.' if is_duplicate_error(error)
                  else 'The subject could not be saved. Please try again.', 'error')
        else:
            flash('Subject added.', 'success')
            return redirect(url_for('subjects.list_subjects'))
    return render_template('subjects.html', action='add', form=request.form)


@subjects_bp.route('/subjects/<int:subject_id>/edit', methods=['GET', 'POST'])
def edit_subject(subject_id):
    """Edit subject information."""
    subject = _find(subject_id)
    if subject is None:
        flash('Subject not found.', 'error')
        return redirect(url_for('subjects.list_subjects'))
    if request.method == 'POST':
        try:
            details = _parse_details(request.form)
            execute_update(
                'UPDATE subjects SET subject_name = %s, credits = %s, semester = %s '
                'WHERE subject_id = %s',
                (details['subject_name'], details['credits'], details['semester'], subject_id))
            audit.record(g.user, 'subject.update', 'subject', subject_id,
                         subject['subject_code'], client_ip())
        except ValidationError as error:
            flash(str(error), 'error')
        except MySQLError:
            flash('The subject could not be saved. Please try again.', 'error')
        else:
            flash('Subject updated.', 'success')
            return redirect(url_for('subjects.list_subjects'))
    return render_template('subjects.html', action='edit', subject=subject, form=request.form)


@subjects_bp.route('/subjects/<int:subject_id>/delete', methods=['POST'])
def delete_subject(subject_id):
    """Delete a subject that has no marks. Faculty assignments to it are removed with it."""
    subject = _find(subject_id)
    if subject is None:
        flash('Subject not found.', 'error')
        return redirect(url_for('subjects.list_subjects'))
    try:
        with transaction() as cursor:
            # Lock the subject so a mark cannot be added between the check and the delete.
            cursor.execute('SELECT subject_id FROM subjects WHERE subject_id = %s FOR UPDATE', (subject_id,))
            cursor.execute('SELECT (SELECT COUNT(*) FROM marks WHERE subject_id = %s) + '
                           '(SELECT COUNT(*) FROM assessment_marks WHERE subject_id = %s) AS n',
                           (subject_id, subject_id))
            if cursor.fetchone()['n']:
                flash('This subject cannot be deleted because it has marks recorded.', 'error')
                return redirect(url_for('subjects.list_subjects'))
            cursor.execute('DELETE FROM subjects WHERE subject_id = %s', (subject_id,))
            audit.record(g.user, 'subject.delete', 'subject', subject_id, subject['subject_code'],
                         client_ip(), cursor)
    except MySQLError:
        flash('The subject could not be deleted. Please try again.', 'error')
    else:
        flash('Subject deleted.', 'success')
    return redirect(url_for('subjects.list_subjects'))
