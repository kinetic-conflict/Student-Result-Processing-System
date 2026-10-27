def calculate_grade(percentage):
    """Calculate grade based on percentage."""
    if percentage >= 90:
        return 'S'  # Outstanding (VIT uses S for 90+)
    elif percentage >= 80:
        return 'A'
    elif percentage >= 70:
        return 'B'
    elif percentage >= 60:
        return 'C'
    elif percentage >= 50:
        return 'D'
    elif percentage >= 40:
        return 'E'
    else:
        return 'F'

def calculate_pass_status(percentage):
    """Determine pass/fail status based on 40% threshold."""
    return 'Pass' if percentage >= 40 else 'Fail'

def calculate_weighted_score(marks_obtained, maximum_marks, weight_percentage):
    """
    Calculate weighted score for an assessment component.
    
    Args:
        marks_obtained: Marks obtained by student
        maximum_marks: Maximum possible marks for this assessment
        weight_percentage: Weight of this assessment in final grade (e.g., 15 for 15%)
    
    Returns:
        Weighted contribution to final score
    """
    if maximum_marks == 0:
        return 0.0
    percentage = (marks_obtained / maximum_marks) * 100
    weighted_score = (percentage * weight_percentage) / 100
    return round(weighted_score, 2)

def calculate_weighted_total(assessment_marks):
    """
    Calculate total weighted score from all assessment components.
    
    Args:
        assessment_marks: List of dictionaries with keys:
            - marks_obtained
            - maximum_marks
            - weight_percentage
    
    Returns:
        Total weighted score (out of 100)
    """
    total_weighted = 0.0
    for assessment in assessment_marks:
        weighted = calculate_weighted_score(
            assessment['marks_obtained'],
            assessment['maximum_marks'],
            assessment['weight_percentage']
        )
        total_weighted += weighted
    return round(total_weighted, 2)

def calculate_student_result(marks_data):
    """
    Calculate overall result for a student (legacy function for backward compatibility).
    
    Args:
        marks_data: List of dictionaries containing marks information
                   Each dict should have: marks_obtained, maximum_marks
    
    Returns:
        Dictionary with total_obtained, total_maximum, overall_percentage, status
    """
    if not marks_data:
        return {
            'total_obtained': 0,
            'total_maximum': 0,
            'overall_percentage': 0,
            'status': 'Incomplete'
        }
    
    total_obtained = sum(m['marks_obtained'] for m in marks_data)
    total_maximum = sum(m['maximum_marks'] for m in marks_data)
    
    if total_maximum == 0:
        return {
            'total_obtained': total_obtained,
            'total_maximum': total_maximum,
            'overall_percentage': 0,
            'status': 'Incomplete'
        }
    
    overall_percentage = (total_obtained / total_maximum) * 100
    
    # Check if all subjects are above passing threshold
    all_passed = all((m['marks_obtained'] / m['maximum_marks'] * 100) >= 40 for m in marks_data)
    
    status = 'Pass' if all_passed else 'Fail'
    
    return {
        'total_obtained': round(total_obtained, 2),
        'total_maximum': round(total_maximum, 2),
        'overall_percentage': round(overall_percentage, 2),
        'status': status
    }

def calculate_student_result_with_assessments(assessment_data):
    """
    Calculate overall result for a student using weighted assessment system.
    
    Args:
        assessment_data: Dictionary with assessment codes as keys and marks as values
                        Example: {'CAT1': 42, 'CAT2': 38, 'CAT3': 45, 'ASSIGN': 40, 
                                  'PROJECT': 85, 'ENDSEM': 78}
    
    Returns:
        Dictionary with:
        - assessment_breakdown: Individual assessment scores with weights
        - total_weighted_score: Overall weighted score out of 100
        - grade: Final grade (S, A, B, C, D, E, F)
        - status: Pass/Fail
    """
    # Assessment configuration
    assessments_config = {
        'CAT1': {'max': 50, 'weight': 15},
        'CAT2': {'max': 50, 'weight': 15},
        'CAT3': {'max': 50, 'weight': 15},
        'ASSIGN': {'max': 50, 'weight': 10},
        'PROJECT': {'max': 100, 'weight': 20},
        'ENDSEM': {'max': 100, 'weight': 25}
    }
    
    assessment_breakdown = []
    total_weighted = 0.0
    total_weight_percentage = 0.0
    incomplete = False
    
    for code, marks in assessment_data.items():
        if code in assessments_config:
            config = assessments_config[code]
            max_marks = config['max']
            weight = config['weight']
            
            if marks is None or marks < 0:
                incomplete = True
                percentage = 0
                weighted_score = 0
            else:
                percentage = (marks / max_marks) * 100
                weighted_score = calculate_weighted_score(marks, max_marks, weight)
                total_weighted += weighted_score
                total_weight_percentage += weight
            
            assessment_breakdown.append({
                'code': code,
                'marks_obtained': marks if marks is not None else 0,
                'maximum_marks': max_marks,
                'percentage': round(percentage, 2),
                'weight_percentage': weight,
                'weighted_score': round(weighted_score, 2)
            })
    
    # Check if all assessments are complete
    if incomplete or len(assessment_breakdown) < 6:
        status = 'Incomplete'
        grade = 'N/A'
    else:
        total_weighted = round(total_weighted, 2)
        grade = calculate_grade(total_weighted)
        status = calculate_pass_status(total_weighted)
    
    return {
        'assessment_breakdown': assessment_breakdown,
        'total_weighted_score': total_weighted,
        'grade': grade,
        'status': status
    }

def process_marks_with_result(marks_records):
    """
    Process marks records and add calculated fields.
    
    Args:
        marks_records: List of mark records from database
    
    Returns:
        List of mark records with percentage, grade, and pass_status added
    """
    processed = []
    for mark in marks_records:
        percentage = (mark['marks_obtained'] / mark['maximum_marks']) * 100
        grade = calculate_grade(percentage)
        pass_status = calculate_pass_status(percentage)
        
        mark['percentage'] = round(percentage, 2)
        mark['grade'] = grade
        mark['pass_status'] = pass_status
        processed.append(mark)
    
    return processed
