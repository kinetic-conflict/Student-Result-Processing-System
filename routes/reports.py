from flask import Blueprint, render_template, request
from db import execute_query
from services.exam_results import student_exam_results
from services.result_service import process_marks_with_result

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports')
def reports_index():
    """Display reports index page."""
    return render_template('reports.html')

@reports_bp.route('/reports/student')
def student_report():
    """Individual student result report."""
    registration_number = request.args.get('registration_number', '')
    
    if registration_number:
        # Get student information
        student_query = "SELECT * FROM students WHERE registration_number = %s"
        student = execute_query(student_query, (registration_number,))
        
        if student:
            student = student[0]
            
            exams = student_exam_results(student['student_id'])

            return render_template('reports.html', report_type='student', student=student, 
                                 exams=exams, registration_number=registration_number)
        else:
            return render_template('reports.html', report_type='student', error='Student not found')
    
    return render_template('reports.html', report_type='student')

@reports_bp.route('/reports/examination')
def examination_report():
    """Examination-wise result report."""
    exam_id = request.args.get('exam_id')
    
    # Get all examinations
    examinations = execute_query("SELECT * FROM examinations ORDER BY exam_date DESC")
    
    if exam_id:
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
            marks = process_marks_with_result(marks)
            
            # Calculate statistics
            if marks:
                total_students = len(set(m['student_id'] for m in marks))
                total_entries = len(marks)
                avg_percentage = sum(m['percentage'] for m in marks) / len(marks)
                passed = sum(1 for m in marks if m['pass_status'] == 'Pass')
                failed = sum(1 for m in marks if m['pass_status'] == 'Fail')
            else:
                total_students = 0
                total_entries = 0
                avg_percentage = 0
                passed = 0
                failed = 0
            
            return render_template('reports.html', report_type='examination', examination=examination,
                                 marks=marks, examinations=examinations,
                                 stats={'total_students': total_students, 'total_entries': total_entries,
                                       'avg_percentage': round(avg_percentage, 2), 'passed': passed, 'failed': failed})
    
    return render_template('reports.html', report_type='examination', examinations=examinations)

@reports_bp.route('/reports/subject')
def subject_report():
    """Subject-wise performance report."""
    subject_id = request.args.get('subject_id')
    
    # Get all subjects
    subjects = execute_query("SELECT * FROM subjects ORDER BY subject_code")
    
    if subject_id:
        # Get subject details
        subject_query = "SELECT * FROM subjects WHERE subject_id = %s"
        subject = execute_query(subject_query, (subject_id,))
        
        if subject:
            subject = subject[0]
            
            # Get all marks for this subject
            marks_query = """
                SELECT 
                    m.mark_id,
                    s.student_id,
                    s.registration_number,
                    s.full_name,
                    e.exam_name,
                    e.academic_year,
                    m.marks_obtained,
                    m.maximum_marks,
                    (m.marks_obtained / m.maximum_marks * 100) AS percentage
                FROM marks m
                JOIN students s ON m.student_id = s.student_id
                JOIN examinations e ON m.exam_id = e.exam_id
                WHERE m.subject_id = %s
                ORDER BY e.exam_date DESC, s.registration_number
            """
            marks = execute_query(marks_query, (subject_id,))
            marks = process_marks_with_result(marks)
            
            # Calculate statistics
            if marks:
                total_entries = len(marks)
                avg_marks = sum(m['marks_obtained'] for m in marks) / len(marks)
                avg_percentage = sum(m['percentage'] for m in marks) / len(marks)
                highest = max(m['marks_obtained'] for m in marks)
                lowest = min(m['marks_obtained'] for m in marks)
                passed = sum(1 for m in marks if m['pass_status'] == 'Pass')
                failed = sum(1 for m in marks if m['pass_status'] == 'Fail')
            else:
                total_entries = 0
                avg_marks = 0
                avg_percentage = 0
                highest = 0
                lowest = 0
                passed = 0
                failed = 0
            
            return render_template('reports.html', report_type='subject', subject=subject,
                                 marks=marks, subjects=subjects,
                                 stats={'total_entries': total_entries, 'avg_marks': round(avg_marks, 2),
                                       'avg_percentage': round(avg_percentage, 2), 'highest': highest,
                                       'lowest': lowest, 'passed': passed, 'failed': failed})
    
    return render_template('reports.html', report_type='subject', subjects=subjects)

@reports_bp.route('/reports/top-performers')
def top_performers():
    """Top-performing students report."""
    query = """
        SELECT 
            s.student_id,
            s.registration_number,
            s.full_name,
            s.department,
            COUNT(m.mark_id) AS subject_count,
            SUM(m.marks_obtained) AS total_obtained,
            SUM(m.maximum_marks) AS total_maximum,
            (SUM(m.marks_obtained) / SUM(m.maximum_marks) * 100) AS overall_percentage
        FROM marks m
        JOIN students s ON m.student_id = s.student_id
        GROUP BY s.student_id, s.registration_number, s.full_name, s.department
        HAVING overall_percentage >= 85
        ORDER BY overall_percentage DESC
    """
    students = execute_query(query)
    
    return render_template('reports.html', report_type='top_performers', students=students)

@reports_bp.route('/reports/failed-students')
def failed_students():
    """Students who failed report."""
    query = """
        SELECT DISTINCT
            s.student_id,
            s.registration_number,
            s.full_name,
            s.department,
            s.semester
        FROM marks m
        JOIN students s ON m.student_id = s.student_id
        WHERE (m.marks_obtained / m.maximum_marks * 100) < 40
        ORDER BY s.registration_number
    """
    students = execute_query(query)
    
    # Get failing subjects for each student
    for student in students:
        failed_query = """
            SELECT sub.subject_code, sub.subject_name, m.marks_obtained, m.maximum_marks,
                   (m.marks_obtained / m.maximum_marks * 100) AS percentage
            FROM marks m
            JOIN subjects sub ON m.subject_id = sub.subject_id
            WHERE m.student_id = %s AND (m.marks_obtained / m.maximum_marks * 100) < 40
        """
        student['failed_subjects'] = execute_query(failed_query, (student['student_id'],))
    
    return render_template('reports.html', report_type='failed_students', students=students)

@reports_bp.route('/reports/incomplete')
def incomplete_results():
    """Students with incomplete results report."""
    # Assuming each student should have at least 5 subjects
    query = """
        SELECT 
            s.student_id,
            s.registration_number,
            s.full_name,
            s.department,
            s.semester,
            COUNT(m.mark_id) AS subjects_recorded
        FROM students s
        LEFT JOIN marks m ON s.student_id = m.student_id
        GROUP BY s.student_id, s.registration_number, s.full_name, s.department, s.semester
        HAVING subjects_recorded < 5 OR subjects_recorded IS NULL
        ORDER BY s.registration_number
    """
    students = execute_query(query)
    
    return render_template('reports.html', report_type='incomplete', students=students)
