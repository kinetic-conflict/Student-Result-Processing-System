from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import execute_query, execute_update
from services.result_service import process_marks_with_result

marks_bp = Blueprint('marks', __name__)

@marks_bp.route('/marks')
def list_marks():
    """Display all marks with filtering."""
    student_id = request.args.get('student_id')
    subject_id = request.args.get('subject_id')
    exam_id = request.args.get('exam_id')
    
    query = """
        SELECT m.*, s.registration_number, s.full_name, 
               sub.subject_code, sub.subject_name, 
               e.exam_name, e.academic_year
        FROM marks m
        JOIN students s ON m.student_id = s.student_id
        JOIN subjects sub ON m.subject_id = sub.subject_id
        JOIN examinations e ON m.exam_id = e.exam_id
        WHERE 1=1
    """
    params = []
    
    if student_id:
        query += " AND m.student_id = %s"
        params.append(student_id)
    
    if subject_id:
        query += " AND m.subject_id = %s"
        params.append(subject_id)
    
    if exam_id:
        query += " AND m.exam_id = %s"
        params.append(exam_id)
    
    query += " ORDER BY e.exam_date DESC, s.registration_number, sub.subject_code"
    
    marks = execute_query(query, tuple(params))
    marks = process_marks_with_result(marks)
    
    # Get dropdown options
    students = execute_query("SELECT student_id, registration_number, full_name FROM students ORDER BY registration_number")
    subjects = execute_query("SELECT subject_id, subject_code, subject_name FROM subjects ORDER BY subject_code")
    examinations = execute_query("SELECT exam_id, exam_name, academic_year FROM examinations ORDER BY exam_date DESC")
    
    return render_template('marks.html', marks=marks, students=students, subjects=subjects, 
                         examinations=examinations, filters={'student_id': student_id, 'subject_id': subject_id, 'exam_id': exam_id})

@marks_bp.route('/marks/add', methods=['GET', 'POST'])
def add_mark():
    """Add a new marks record."""
    if request.method == 'POST':
        student_id = request.form['student_id']
        subject_id = request.form['subject_id']
        exam_id = request.form['exam_id']
        marks_obtained = float(request.form['marks_obtained'])
        maximum_marks = float(request.form['maximum_marks'])
        
        # Server-side validation
        if marks_obtained < 0:
            flash('Marks obtained cannot be negative!', 'error')
            return redirect(url_for('marks.add_mark'))
        
        if maximum_marks <= 0:
            flash('Maximum marks must be greater than zero!', 'error')
            return redirect(url_for('marks.add_mark'))
        
        if marks_obtained > maximum_marks:
            flash('Marks obtained cannot exceed maximum marks!', 'error')
            return redirect(url_for('marks.add_mark'))
        
        try:
            query = """
                INSERT INTO marks (student_id, subject_id, exam_id, marks_obtained, maximum_marks)
                VALUES (%s, %s, %s, %s, %s)
            """
            params = (student_id, subject_id, exam_id, marks_obtained, maximum_marks)
            execute_update(query, params)
            flash('Marks added successfully!', 'success')
            return redirect(url_for('marks.list_marks'))
        except Exception as e:
            if 'Duplicate entry' in str(e):
                flash('Marks for this student, subject, and examination already exist!', 'error')
            else:
                flash(f'Error adding marks: {e}', 'error')
    
    # Get dropdown options
    students = execute_query("SELECT student_id, registration_number, full_name FROM students ORDER BY registration_number")
    subjects = execute_query("SELECT subject_id, subject_code, subject_name FROM subjects ORDER BY subject_code")
    examinations = execute_query("SELECT exam_id, exam_name, academic_year FROM examinations ORDER BY exam_date DESC")
    
    return render_template('marks.html', action='add', students=students, subjects=subjects, examinations=examinations)

@marks_bp.route('/marks/<int:mark_id>/edit', methods=['GET', 'POST'])
def edit_mark(mark_id):
    """Edit an existing marks record."""
    if request.method == 'POST':
        marks_obtained = float(request.form['marks_obtained'])
        maximum_marks = float(request.form['maximum_marks'])
        
        # Server-side validation
        if marks_obtained < 0:
            flash('Marks obtained cannot be negative!', 'error')
            return redirect(url_for('marks.edit_mark', mark_id=mark_id))
        
        if maximum_marks <= 0:
            flash('Maximum marks must be greater than zero!', 'error')
            return redirect(url_for('marks.edit_mark', mark_id=mark_id))
        
        if marks_obtained > maximum_marks:
            flash('Marks obtained cannot exceed maximum marks!', 'error')
            return redirect(url_for('marks.edit_mark', mark_id=mark_id))
        
        try:
            query = """
                UPDATE marks 
                SET marks_obtained = %s, maximum_marks = %s
                WHERE mark_id = %s
            """
            params = (marks_obtained, maximum_marks, mark_id)
            execute_update(query, params)
            flash('Marks updated successfully!', 'success')
            return redirect(url_for('marks.list_marks'))
        except Exception as e:
            flash(f'Error updating marks: {e}', 'error')
    
    query = "SELECT * FROM marks WHERE mark_id = %s"
    mark = execute_query(query, (mark_id,))
    
    if mark:
        mark = mark[0]
        # Get related data for display
        student = execute_query("SELECT registration_number, full_name FROM students WHERE student_id = %s", (mark['student_id'],))
        subject = execute_query("SELECT subject_code, subject_name FROM subjects WHERE subject_id = %s", (mark['subject_id'],))
        examination = execute_query("SELECT exam_name, academic_year FROM examinations WHERE exam_id = %s", (mark['exam_id'],))
        
        return render_template('marks.html', mark=mark, student=student[0] if student else None, 
                             subject=subject[0] if subject else None, examination=examination[0] if examination else None, 
                             action='edit')
    else:
        flash('Marks record not found!', 'error')
        return redirect(url_for('marks.list_marks'))

@marks_bp.route('/marks/<int:mark_id>/delete', methods=['POST'])
def delete_mark(mark_id):
    """Delete a marks record."""
    try:
        query = "DELETE FROM marks WHERE mark_id = %s"
        execute_update(query, (mark_id,))
        flash('Marks deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting marks: {e}', 'error')
    
    return redirect(url_for('marks.list_marks'))
