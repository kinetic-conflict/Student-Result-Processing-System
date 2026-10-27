import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.result_service import (
    calculate_grade, 
    calculate_pass_status, 
    calculate_student_result, 
    process_marks_with_result,
    calculate_student_result_with_assessments,
    calculate_weighted_score
)

class TestResultService(unittest.TestCase):
    """Test result calculation logic."""
    
    def test_calculate_grade(self):
        """Test grade calculation with VIT grading (S for 90+)."""
        self.assertEqual(calculate_grade(95), 'S')
        self.assertEqual(calculate_grade(90), 'S')
        self.assertEqual(calculate_grade(85), 'A')
        self.assertEqual(calculate_grade(80), 'A')
        self.assertEqual(calculate_grade(75), 'B')
        self.assertEqual(calculate_grade(70), 'B')
        self.assertEqual(calculate_grade(65), 'C')
        self.assertEqual(calculate_grade(60), 'C')
        self.assertEqual(calculate_grade(55), 'D')
        self.assertEqual(calculate_grade(50), 'D')
        self.assertEqual(calculate_grade(45), 'E')
        self.assertEqual(calculate_grade(40), 'E')
        self.assertEqual(calculate_grade(35), 'F')
    
    def test_calculate_pass_status(self):
        """Test pass/fail status calculation (40% threshold)."""
        self.assertEqual(calculate_pass_status(40), 'Pass')
        self.assertEqual(calculate_pass_status(39.99), 'Fail')
        self.assertEqual(calculate_pass_status(100), 'Pass')
        self.assertEqual(calculate_pass_status(0), 'Fail')
        self.assertEqual(calculate_pass_status(85), 'Pass')
    
    def test_calculate_weighted_score(self):
        """Test weighted score calculation."""
        # CAT1: 42/50 with 15% weight
        # Percentage: 84%, Weighted: 84 * 0.15 = 12.6
        score = calculate_weighted_score(42, 50, 15)
        self.assertAlmostEqual(score, 12.6, places=2)
        
        # End Semester: 78/100 with 25% weight
        # Percentage: 78%, Weighted: 78 * 0.25 = 19.5
        score = calculate_weighted_score(78, 100, 25)
        self.assertAlmostEqual(score, 19.5, places=2)
        
        # Edge case: zero maximum marks
        score = calculate_weighted_score(50, 0, 15)
        self.assertEqual(score, 0.0)
    
    def test_calculate_student_result_pass(self):
        """Test overall result calculation for passing student (legacy)."""
        marks_data = [
            {'marks_obtained': 85, 'maximum_marks': 100},
            {'marks_obtained': 76, 'maximum_marks': 100},
            {'marks_obtained': 92, 'maximum_marks': 100}
        ]
        result = calculate_student_result(marks_data)
        
        self.assertEqual(result['total_obtained'], 253)
        self.assertEqual(result['total_maximum'], 300)
        self.assertAlmostEqual(result['overall_percentage'], 84.33, places=2)
        self.assertEqual(result['status'], 'Pass')
    
    def test_calculate_student_result_fail(self):
        """Test overall result calculation for failing student (legacy)."""
        marks_data = [
            {'marks_obtained': 85, 'maximum_marks': 100},
            {'marks_obtained': 35, 'maximum_marks': 100},  # Below 40%
            {'marks_obtained': 92, 'maximum_marks': 100}
        ]
        result = calculate_student_result(marks_data)
        
        self.assertEqual(result['total_obtained'], 212)
        self.assertEqual(result['total_maximum'], 300)
        self.assertAlmostEqual(result['overall_percentage'], 70.67, places=2)
        self.assertEqual(result['status'], 'Fail')
    
    def test_calculate_student_result_with_assessments(self):
        """Test weighted assessment calculation."""
        assessment_data = {
            'CAT1': 42,      # 42/50 = 84%, weighted: 12.6
            'CAT2': 38,      # 38/50 = 76%, weighted: 11.4
            'CAT3': 45,      # 45/50 = 90%, weighted: 13.5
            'ASSIGN': 40,    # 40/50 = 80%, weighted: 8.0
            'PROJECT': 85,   # 85/100 = 85%, weighted: 17.0
            'ENDSEM': 78     # 78/100 = 78%, weighted: 19.5
        }
        # Total weighted: 12.6 + 11.4 + 13.5 + 8.0 + 17.0 + 19.5 = 82.0
        result = calculate_student_result_with_assessments(assessment_data)
        
        self.assertEqual(result['total_weighted_score'], 82.0)
        self.assertEqual(result['grade'], 'A')  # 82% is A grade
        self.assertEqual(result['status'], 'Pass')
        self.assertEqual(len(result['assessment_breakdown']), 6)
    
    def test_calculate_student_result_with_assessments_incomplete(self):
        """Test weighted assessment calculation with incomplete data."""
        assessment_data = {
            'CAT1': 42,
            'CAT2': 38,
            # Missing other assessments
        }
        result = calculate_student_result_with_assessments(assessment_data)
        
        self.assertEqual(result['status'], 'Incomplete')
        self.assertEqual(result['grade'], 'N/A')
    
    def test_calculate_student_result_with_assessments_s_grade(self):
        """Test S grade (90+)."""
        assessment_data = {
            'CAT1': 48,      # 48/50 = 96%
            'CAT2': 47,      # 47/50 = 94%
            'CAT3': 49,      # 49/50 = 98%
            'ASSIGN': 48,    # 48/50 = 96%
            'PROJECT': 95,   # 95/100 = 95%
            'ENDSEM': 92     # 92/100 = 92%
        }
        result = calculate_student_result_with_assessments(assessment_data)
        
        self.assertGreaterEqual(result['total_weighted_score'], 90)
        self.assertEqual(result['grade'], 'S')
        self.assertEqual(result['status'], 'Pass')
    
    def test_process_marks_with_result(self):
        """Test marks processing with calculated fields."""
        marks_records = [
            {'marks_obtained': 85, 'maximum_marks': 100},
            {'marks_obtained': 76, 'maximum_marks': 100},
            {'marks_obtained': 35, 'maximum_marks': 100}
        ]
        processed = process_marks_with_result(marks_records)
        
        self.assertEqual(len(processed), 3)
        self.assertEqual(processed[0]['percentage'], 85.0)
        self.assertEqual(processed[0]['grade'], 'A')  # Changed from A+ to A
        self.assertEqual(processed[0]['pass_status'], 'Pass')
        
        self.assertEqual(processed[1]['percentage'], 76.0)
        self.assertEqual(processed[1]['grade'], 'B')
        self.assertEqual(processed[1]['pass_status'], 'Pass')
        
        self.assertEqual(processed[2]['percentage'], 35.0)
        self.assertEqual(processed[2]['grade'], 'F')
        self.assertEqual(processed[2]['pass_status'], 'Fail')

if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
