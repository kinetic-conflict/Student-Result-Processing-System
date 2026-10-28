"""Legacy per-examination marks, grouped and totalled for one student."""
from db import execute_query
from services.result_service import calculate_student_result, process_marks_with_result

STUDENT_MARKS = """
    SELECT m.*, s.subject_code, s.subject_name, s.credits,
           e.exam_name, e.academic_year, e.semester
    FROM marks m
    JOIN subjects s ON m.subject_id = s.subject_id
    JOIN examinations e ON m.exam_id = e.exam_id
    WHERE m.student_id = %s
    ORDER BY e.exam_date DESC, e.exam_id DESC, s.subject_code
"""


def student_exam_results(student_id):
    """A list of examinations, newest first, each with its `marks` and overall `result`."""
    exams = {}
    for mark in process_marks_with_result(execute_query(STUDENT_MARKS, (student_id,))):
        exam = exams.setdefault(mark['exam_id'], {
            'exam_id': mark['exam_id'], 'exam_name': mark['exam_name'],
            'academic_year': mark['academic_year'], 'semester': mark['semester'], 'marks': []})
        exam['marks'].append(mark)
    for exam in exams.values():
        exam['result'] = calculate_student_result(exam['marks'])
    return list(exams.values())
