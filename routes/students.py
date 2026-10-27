from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import execute_query, execute_update

students_bp = Blueprint('students', __name__)

@students_bp.route('/students')
def list_students():
    """Display all students with search functionality."""
    search = request.args.get('search', '')
    
    if search:
        query = """
            SELECT * FROM students 
            WHERE registration_number LIKE %s OR full_name LIKE %s
            ORDER BY registration_number
        """
        params = (f'%{search}%', f'%{search}%')
    else:
        query = "SELECT * FROM students ORDER BY registration_number"
        params = ()
    
    students = execute_query(query, params)
    return render_template('students.html', students=students, search=search)

@students_bp.route('/students/add', methods=['GET', 'POST'])
def add_student():
    """Add a new student."""
    if request.method == 'POST':
        registration_number = request.form['registration_number']
        full_name = request.form['full_name']
        email = request.form.get('email')
        department = request.form['department']
        semester = request.form['semester']
        academic_year = request.form['academic_year']
        
        try:
            query = """
                INSERT INTO students (registration_number, full_name, email, department, semester, academic_year)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            params = (registration_number, full_name, email or None, department, semester, academic_year)
            execute_update(query, params)
            flash('Student added successfully!', 'success')
            return redirect(url_for('students.list_students'))
        except Exception as e:
            if 'Duplicate entry' in str(e):
                flash('Registration number already exists!', 'error')
            else:
                flash(f'Error adding student: {e}', 'error')
    
    return render_template('students.html', action='add')

@students_bp.route('/students/<int:student_id>')
def view_student(student_id):
    """View student details."""
    query = "SELECT * FROM students WHERE student_id = %s"
    student = execute_query(query, (student_id,))
    
    if student:
        student = student[0]
        
        # Get marks for this student
        marks_query = """
            SELECT m.*, s.subject_code, s.subject_name, e.exam_name, e.academic_year
            FROM marks m
            JOIN subjects s ON m.subject_id = s.subject_id
            JOIN examinations e ON m.exam_id = e.exam_id
            WHERE m.student_id = %s
            ORDER BY e.exam_date DESC, s.subject_code
        """
        marks = execute_query(marks_query, (student_id,))
        
        return render_template('students.html', student=student, marks=marks, action='view')
    else:
        flash('Student not found!', 'error')
        return redirect(url_for('students.list_students'))

@students_bp.route('/students/<int:student_id>/edit', methods=['GET', 'POST'])
def edit_student(student_id):
    """Edit student information."""
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form.get('email')
        department = request.form['department']
        semester = request.form['semester']
        academic_year = request.form['academic_year']
        
        try:
            query = """
                UPDATE students 
                SET full_name = %s, email = %s, department = %s, semester = %s, academic_year = %s
                WHERE student_id = %s
            """
            params = (full_name, email or None, department, semester, academic_year, student_id)
            execute_update(query, params)
            flash('Student updated successfully!', 'success')
            return redirect(url_for('students.list_students'))
        except Exception as e:
            flash(f'Error updating student: {e}', 'error')
    
    query = "SELECT * FROM students WHERE student_id = %s"
    student = execute_query(query, (student_id,))
    
    if student:
        return render_template('students.html', student=student[0], action='edit')
    else:
        flash('Student not found!', 'error')
        return redirect(url_for('students.list_students'))

@students_bp.route('/students/<int:student_id>/delete', methods=['POST'])
def delete_student(student_id):
    """Delete a student."""
    try:
        query = "DELETE FROM students WHERE student_id = %s"
        execute_update(query, (student_id,))
        flash('Student deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting student: {e}', 'error')
    
    return redirect(url_for('students.list_students'))
