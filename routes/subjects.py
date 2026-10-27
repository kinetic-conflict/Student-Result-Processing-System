from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import execute_query, execute_update

subjects_bp = Blueprint('subjects', __name__)

@subjects_bp.route('/subjects')
def list_subjects():
    """Display all subjects with search functionality."""
    search = request.args.get('search', '')
    
    if search:
        query = """
            SELECT * FROM subjects 
            WHERE subject_code LIKE %s OR subject_name LIKE %s
            ORDER BY subject_code
        """
        params = (f'%{search}%', f'%{search}%')
    else:
        query = "SELECT * FROM subjects ORDER BY subject_code"
        params = ()
    
    subjects = execute_query(query, params)
    return render_template('subjects.html', subjects=subjects, search=search)

@subjects_bp.route('/subjects/add', methods=['GET', 'POST'])
def add_subject():
    """Add a new subject."""
    if request.method == 'POST':
        subject_code = request.form['subject_code']
        subject_name = request.form['subject_name']
        credits = request.form['credits']
        semester = request.form['semester']
        
        try:
            query = """
                INSERT INTO subjects (subject_code, subject_name, credits, semester)
                VALUES (%s, %s, %s, %s)
            """
            params = (subject_code, subject_name, credits, semester)
            execute_update(query, params)
            flash('Subject added successfully!', 'success')
            return redirect(url_for('subjects.list_subjects'))
        except Exception as e:
            if 'Duplicate entry' in str(e):
                flash('Subject code already exists!', 'error')
            else:
                flash(f'Error adding subject: {e}', 'error')
    
    return render_template('subjects.html', action='add')

@subjects_bp.route('/subjects/<int:subject_id>/edit', methods=['GET', 'POST'])
def edit_subject(subject_id):
    """Edit subject information."""
    if request.method == 'POST':
        subject_name = request.form['subject_name']
        credits = request.form['credits']
        semester = request.form['semester']
        
        try:
            query = """
                UPDATE subjects 
                SET subject_name = %s, credits = %s, semester = %s
                WHERE subject_id = %s
            """
            params = (subject_name, credits, semester, subject_id)
            execute_update(query, params)
            flash('Subject updated successfully!', 'success')
            return redirect(url_for('subjects.list_subjects'))
        except Exception as e:
            flash(f'Error updating subject: {e}', 'error')
    
    query = "SELECT * FROM subjects WHERE subject_id = %s"
    subject = execute_query(query, (subject_id,))
    
    if subject:
        return render_template('subjects.html', subject=subject[0], action='edit')
    else:
        flash('Subject not found!', 'error')
        return redirect(url_for('subjects.list_subjects'))

@subjects_bp.route('/subjects/<int:subject_id>/delete', methods=['POST'])
def delete_subject(subject_id):
    """Delete a subject."""
    try:
        # Check if subject has associated marks
        check_query = "SELECT COUNT(*) as count FROM marks WHERE subject_id = %s"
        result = execute_query(check_query, (subject_id,))
        
        if result and result[0]['count'] > 0:
            flash('Cannot delete subject: It has associated marks records!', 'error')
        else:
            query = "DELETE FROM subjects WHERE subject_id = %s"
            execute_update(query, (subject_id,))
            flash('Subject deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting subject: {e}', 'error')
    
    return redirect(url_for('subjects.list_subjects'))
