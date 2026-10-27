from flask import Flask, render_template, session, redirect, url_for, request
from routes.students import students_bp
from routes.subjects import subjects_bp
from routes.examinations import examinations_bp
from routes.marks import marks_bp
from routes.reports import reports_bp
from routes.assessments import assessments_bp
from db import execute_query
from services.result_service import process_marks_with_result

app = Flask(__name__)
app.config.from_object('config.Config')
app.secret_key = app.config['SECRET_KEY']

# Register blueprints
app.register_blueprint(students_bp)
app.register_blueprint(subjects_bp)
app.register_blueprint(examinations_bp)
app.register_blueprint(marks_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(assessments_bp)

@app.route('/')
def dashboard():
    """Display dashboard with statistics."""
    try:
        # Get statistics from database
        total_students = execute_query("SELECT COUNT(*) as count FROM students")[0]['count']
        total_subjects = execute_query("SELECT COUNT(*) as count FROM subjects")[0]['count']
        total_examinations = execute_query("SELECT COUNT(*) as count FROM examinations")[0]['count']
        total_marks = execute_query("SELECT COUNT(*) as count FROM marks")[0]['count']
        
        # Get recent marks entries
        recent_marks_query = """
            SELECT m.*, s.registration_number, s.full_name, 
                   sub.subject_code, sub.subject_name, e.exam_name
            FROM marks m
            JOIN students s ON m.student_id = s.student_id
            JOIN subjects sub ON m.subject_id = sub.subject_id
            JOIN examinations e ON m.exam_id = e.exam_id
            ORDER BY m.created_at DESC
            LIMIT 10
        """
        recent_marks = execute_query(recent_marks_query)
    except Exception as e:
        # Handle database connection errors gracefully
        total_students = 0
        total_subjects = 0
        total_examinations = 0
        total_marks = 0
        recent_marks = []
        print(f"Database error in dashboard: {e}")
    
    return render_template('dashboard.html', 
                         total_students=total_students,
                         total_subjects=total_subjects,
                         total_examinations=total_examinations,
                         total_marks=total_marks,
                         recent_marks=recent_marks)

@app.route('/results')
def results():
    """Result search page."""
    search = request.args.get('search', '')
    filter_type = request.args.get('filter_type', 'registration')
    
    if search:
        if filter_type == 'registration':
            query = """
                SELECT m.*, s.registration_number, s.full_name, s.department,
                       sub.subject_code, sub.subject_name, e.exam_name, e.academic_year
                FROM marks m
                JOIN students s ON m.student_id = s.student_id
                JOIN subjects sub ON m.subject_id = sub.subject_id
                JOIN examinations e ON m.exam_id = e.exam_id
                WHERE s.registration_number LIKE %s
                ORDER BY s.registration_number, sub.subject_code
            """
            params = (f'%{search}%',)
        elif filter_type == 'name':
            query = """
                SELECT m.*, s.registration_number, s.full_name, s.department,
                       sub.subject_code, sub.subject_name, e.exam_name, e.academic_year
                FROM marks m
                JOIN students s ON m.student_id = s.student_id
                JOIN subjects sub ON m.subject_id = sub.subject_id
                JOIN examinations e ON m.exam_id = e.exam_id
                WHERE s.full_name LIKE %s
                ORDER BY s.full_name, sub.subject_code
            """
            params = (f'%{search}%',)
        else:
            query = """
                SELECT m.*, s.registration_number, s.full_name, s.department,
                       sub.subject_code, sub.subject_name, e.exam_name, e.academic_year
                FROM marks m
                JOIN students s ON m.student_id = s.student_id
                JOIN subjects sub ON m.subject_id = sub.subject_id
                JOIN examinations e ON m.exam_id = e.exam_id
                ORDER BY s.registration_number, sub.subject_code
            """
            params = ()
        
        results_data = execute_query(query, params)
        results_data = process_marks_with_result(results_data)
    else:
        results_data = []
    
    return render_template('results.html', results=results_data, search=search, filter_type=filter_type)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
