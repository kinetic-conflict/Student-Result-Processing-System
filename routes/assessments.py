from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import execute_query, execute_update
from services.result_service import calculate_student_result_with_assessments

assessments_bp = Blueprint('assessments', __name__)

@assessments_bp.route('/assessments')
def list_assessment_marks():
    """Display all assessment marks with filtering."""
    student_id = request.args.get('student_id')
    subject_id = request.args.get('subject_id')
    
    query = """
        SELECT am.*, s.registration_number, s.full_name, 
               sub.subject_code, sub.subject_name,
               a.assessment_code, a.assessment_name, a.maximum_marks, a.weight_percentage
        FROM assessment_marks am
        JOIN students s ON am.student_id = s.student_id
        JOIN subjects sub ON am.subject_id = sub.subject_id
        JOIN assessments a ON am.assessment_id = a.assessment_id
        WHERE 1=1
    """
    params = []
    
    if student_id:
        query += " AND am.student_id = %s"
        params.append(student_id)
    
    if subject_id:
        query += " AND am.subject_id = %s"
        params.append(subject_id)
    
    query += " ORDER BY s.registration_number, sub.subject_code, a.assessment_id"
    
    assessment_marks = execute_query(query, tuple(params))
    
    # Get dropdown options
    students = execute_query("SELECT student_id, registration_number, full_name FROM students ORDER BY registration_number")
    subjects = execute_query("SELECT subject_id, subject_code, subject_name FROM subjects ORDER BY subject_code")
    
    return render_template('assessments.html', assessment_marks=assessment_marks, students=students, subjects=subjects,
                         filters={'student_id': student_id, 'subject_id': subject_id})

@assessments_bp.route('/assessments/enter', methods=['GET', 'POST'])
def enter_assessment_marks():
    """Enter assessment marks for a student-subject combination."""
    if request.method == 'POST':
        student_id = request.form['student_id']
        subject_id = request.form['subject_id']
        
        # Get all 6 assessment marks
        assessment_marks = {}
        for code in ['CAT1', 'CAT2', 'CAT3', 'ASSIGN', 'PROJECT', 'ENDSEM']:
            marks = request.form.get(f'marks_{code}')
            if marks and marks.strip():
                assessment_marks[code] = float(marks)
            else:
                assessment_marks[code] = None
        
        try:
            # Insert or update each assessment mark
            assessments = execute_query("SELECT assessment_id, assessment_code FROM assessments")
            
            for assessment in assessments:
                code = assessment['assessment_code']
                assessment_id = assessment['assessment_id']
                marks = assessment_marks.get(code)
                
                if marks is not None:
                    # Check if record exists
                    existing = execute_query(
                        "SELECT assessment_mark_id FROM assessment_marks WHERE student_id = %s AND subject_id = %s AND assessment_id = %s",
                        (student_id, subject_id, assessment_id)
                    )
                    
                    if existing:
                        # Update existing record
                        execute_update(
                            "UPDATE assessment_marks SET marks_obtained = %s WHERE student_id = %s AND subject_id = %s AND assessment_id = %s",
                            (marks, student_id, subject_id, assessment_id)
                        )
                    else:
                        # Insert new record
                        execute_update(
                            "INSERT INTO assessment_marks (student_id, subject_id, assessment_id, marks_obtained) VALUES (%s, %s, %s, %s)",
                            (student_id, subject_id, assessment_id, marks)
                        )
            
            flash('Assessment marks saved successfully!', 'success')
            return redirect(url_for('assessments.list_assessment_marks'))
        except Exception as e:
            flash(f'Error saving assessment marks: {e}', 'error')
    
    # Get dropdown options
    students = execute_query("SELECT student_id, registration_number, full_name FROM students ORDER BY registration_number")
    subjects = execute_query("SELECT subject_id, subject_code, subject_name FROM subjects ORDER BY subject_code")
    assessments = execute_query("SELECT * FROM assessments ORDER BY assessment_id")
    
    return render_template('assessments.html', action='enter', students=students, subjects=subjects, assessments=assessments)

@assessments_bp.route('/assessments/calculate', methods=['GET', 'POST'])
def calculate_result():
    """Calculate and display result for a student-subject combination."""
    if request.method == 'POST':
        student_id = request.form['student_id']
        subject_id = request.form['subject_id']
        
        # Get all assessment marks for this student-subject
        query = """
            SELECT am.marks_obtained, a.assessment_code, a.maximum_marks, a.weight_percentage
            FROM assessment_marks am
            JOIN assessments a ON am.assessment_id = a.assessment_id
            WHERE am.student_id = %s AND am.subject_id = %s
            ORDER BY a.assessment_id
        """
        marks_data = execute_query(query, (student_id, subject_id))
        
        # Convert to dictionary format for calculation
        assessment_dict = {row['assessment_code']: row['marks_obtained'] for row in marks_data}
        
        # Calculate result
        result = calculate_student_result_with_assessments(assessment_dict)
        
        # Get student and subject info
        student = execute_query("SELECT * FROM students WHERE student_id = %s", (student_id,))
        subject = execute_query("SELECT * FROM subjects WHERE subject_id = %s", (subject_id,))
        
        return render_template('assessments.html', action='calculate', result=result,
                             student=student[0] if student else None,
                             subject=subject[0] if subject else None,
                             student_id=student_id, subject_id=subject_id)
    
    # Get dropdown options
    students = execute_query("SELECT student_id, registration_number, full_name FROM students ORDER BY registration_number")
    subjects = execute_query("SELECT subject_id, subject_code, subject_name FROM subjects ORDER BY subject_code")
    
    return render_template('assessments.html', action='calculate', students=students, subjects=subjects)

@assessments_bp.route('/assessments/<int:assessment_mark_id>/edit', methods=['GET', 'POST'])
def edit_assessment_mark(assessment_mark_id):
    """Edit an existing assessment mark."""
    if request.method == 'POST':
        marks_obtained = float(request.form['marks_obtained'])
        
        if marks_obtained < 0:
            flash('Marks cannot be negative!', 'error')
            return redirect(url_for('assessments.edit_assessment_mark', assessment_mark_id=assessment_mark_id))
        
        try:
            # Get maximum marks for this assessment
            query = """
                SELECT maximum_marks 
                FROM assessment_marks am
                JOIN assessments a ON am.assessment_id = a.assessment_id
                WHERE am.assessment_mark_id = %s
            """
            result = execute_query(query, (assessment_mark_id,))
            
            if result:
                max_marks = result[0]['maximum_marks']
                if marks_obtained > max_marks:
                    flash(f'Marks cannot exceed maximum marks ({max_marks})!', 'error')
                    return redirect(url_for('assessments.edit_assessment_mark', assessment_mark_id=assessment_mark_id))
            
            execute_update(
                "UPDATE assessment_marks SET marks_obtained = %s WHERE assessment_mark_id = %s",
                (marks_obtained, assessment_mark_id)
            )
            flash('Assessment mark updated successfully!', 'success')
            return redirect(url_for('assessments.list_assessment_marks'))
        except Exception as e:
            flash(f'Error updating assessment mark: {e}', 'error')
    
    query = """
        SELECT am.*, s.registration_number, s.full_name, 
               sub.subject_code, sub.subject_name,
               a.assessment_code, a.assessment_name, a.maximum_marks, a.weight_percentage
        FROM assessment_marks am
        JOIN students s ON am.student_id = s.student_id
        JOIN subjects sub ON am.subject_id = sub.subject_id
        JOIN assessments a ON am.assessment_id = a.assessment_id
        WHERE am.assessment_mark_id = %s
    """
    mark = execute_query(query, (assessment_mark_id,))
    
    if mark:
        return render_template('assessments.html', action='edit', mark=mark[0])
    else:
        flash('Assessment mark not found!', 'error')
        return redirect(url_for('assessments.list_assessment_marks'))

@assessments_bp.route('/assessments/<int:assessment_mark_id>/delete', methods=['POST'])
def delete_assessment_mark(assessment_mark_id):
    """Delete an assessment mark."""
    try:
        execute_update("DELETE FROM assessment_marks WHERE assessment_mark_id = %s", (assessment_mark_id,))
        flash('Assessment mark deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting assessment mark: {e}', 'error')
    
    return redirect(url_for('assessments.list_assessment_marks'))
