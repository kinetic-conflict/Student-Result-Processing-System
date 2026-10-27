from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import execute_query, execute_update

examinations_bp = Blueprint('examinations', __name__)

@examinations_bp.route('/examinations')
def list_examinations():
    """Display all examinations."""
    query = "SELECT * FROM examinations ORDER BY exam_date DESC, exam_name"
    examinations = execute_query(query)
    return render_template('examinations.html', examinations=examinations)

@examinations_bp.route('/examinations/add', methods=['GET', 'POST'])
def add_examination():
    """Add a new examination."""
    if request.method == 'POST':
        exam_name = request.form['exam_name']
        academic_year = request.form['academic_year']
        semester = request.form['semester']
        exam_date = request.form.get('exam_date')
        
        try:
            query = """
                INSERT INTO examinations (exam_name, academic_year, semester, exam_date)
                VALUES (%s, %s, %s, %s)
            """
            params = (exam_name, academic_year, semester, exam_date or None)
            execute_update(query, params)
            flash('Examination added successfully!', 'success')
            return redirect(url_for('examinations.list_examinations'))
        except Exception as e:
            flash(f'Error adding examination: {e}', 'error')
    
    return render_template('examinations.html', action='add')

@examinations_bp.route('/examinations/<int:exam_id>/edit', methods=['GET', 'POST'])
def edit_examination(exam_id):
    """Edit examination information."""
    if request.method == 'POST':
        exam_name = request.form['exam_name']
        academic_year = request.form['academic_year']
        semester = request.form['semester']
        exam_date = request.form.get('exam_date')
        
        try:
            query = """
                UPDATE examinations 
                SET exam_name = %s, academic_year = %s, semester = %s, exam_date = %s
                WHERE exam_id = %s
            """
            params = (exam_name, academic_year, semester, exam_date or None, exam_id)
            execute_update(query, params)
            flash('Examination updated successfully!', 'success')
            return redirect(url_for('examinations.list_examinations'))
        except Exception as e:
            flash(f'Error updating examination: {e}', 'error')
    
    query = "SELECT * FROM examinations WHERE exam_id = %s"
    examination = execute_query(query, (exam_id,))
    
    if examination:
        return render_template('examinations.html', examination=examination[0], action='edit')
    else:
        flash('Examination not found!', 'error')
        return redirect(url_for('examinations.list_examinations'))

@examinations_bp.route('/examinations/<int:exam_id>/results')
def examination_results(exam_id):
    """View examination-wise results."""
    # Get examination details
    exam_query = "SELECT * FROM examinations WHERE exam_id = %s"
    examination = execute_query(exam_query, (exam_id,))
    
    if examination:
        examination = examination[0]
        
        # Get all marks for this examination
        marks_query = """
            SELECT 
                m.mark_id,
                s.student_id,
                s.registration_number,
                s.full_name,
                sub.subject_code,
                sub.subject_name,
                m.marks_obtained,
                m.maximum_marks,
                (m.marks_obtained / m.maximum_marks * 100) AS percentage
            FROM marks m
            JOIN students s ON m.student_id = s.student_id
            JOIN subjects sub ON m.subject_id = sub.subject_id
            WHERE m.exam_id = %s
            ORDER BY s.registration_number, sub.subject_code
        """
        marks = execute_query(marks_query, (exam_id,))
        
        return render_template('examinations.html', examination=examination, marks=marks, action='results')
    else:
        flash('Examination not found!', 'error')
        return redirect(url_for('examinations.list_examinations'))
