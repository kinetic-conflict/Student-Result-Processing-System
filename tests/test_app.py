import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from decimal import Decimal

from services.result_service import (
    calculate_grade, 
    calculate_pass_status, 
    calculate_student_result, 
    process_marks_with_result,
    calculate_student_result_with_assessments,
    calculate_weighted_score
)

# The stock assessment set, as migration_add_assessments.sql inserts it. Production code
# reads these from the assessments table; tests pass them in.
STOCK = [
    {'code': 'CAT1', 'max': 50, 'weight': 15},
    {'code': 'CAT2', 'max': 50, 'weight': 15},
    {'code': 'CAT3', 'max': 50, 'weight': 15},
    {'code': 'ASSIGN', 'max': 50, 'weight': 10},
    {'code': 'PROJECT', 'max': 100, 'weight': 20},
    {'code': 'ENDSEM', 'max': 100, 'weight': 25},
]


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
        result = calculate_student_result_with_assessments(assessment_data, STOCK)
        
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
        result = calculate_student_result_with_assessments(assessment_data, STOCK)
        
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
        result = calculate_student_result_with_assessments(assessment_data, STOCK)
        
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

class TestAssessmentCalculation(unittest.TestCase):
    """Behaviour the first version got wrong or never exercised."""

    FULL = {'CAT1': 42, 'CAT2': 38, 'CAT3': 45, 'ASSIGN': 40, 'PROJECT': 85, 'ENDSEM': 78}

    def test_database_decimals_do_not_crash_the_calculation(self):
        marks = {code: Decimal(str(value)) for code, value in self.FULL.items()}
        result = calculate_student_result_with_assessments(marks, STOCK)
        self.assertEqual(result['total_weighted_score'], 82.0)
        self.assertEqual(result['grade'], 'A')

    def test_weights_and_maximums_come_from_the_configuration_passed_in(self):
        two_part = [{'code': 'MID', 'max': 20, 'weight': 40}, {'code': 'END', 'max': 80, 'weight': 60}]
        result = calculate_student_result_with_assessments({'MID': 10, 'END': 60}, two_part)
        # 10/20 * 40 = 20.0 and 60/80 * 60 = 45.0
        self.assertEqual(result['total_weighted_score'], 65.0)
        self.assertEqual(result['grade'], 'C')
        self.assertEqual([b['code'] for b in result['assessment_breakdown']], ['MID', 'END'])

    def test_a_missing_component_makes_the_result_incomplete_without_a_total(self):
        marks = dict(self.FULL)
        del marks['PROJECT']
        result = calculate_student_result_with_assessments(marks, STOCK)
        self.assertEqual(result['status'], 'Incomplete')
        self.assertEqual(result['grade'], 'N/A')
        self.assertIsNone(result['total_weighted_score'])
        project = [b for b in result['assessment_breakdown'] if b['code'] == 'PROJECT'][0]
        self.assertIsNone(project['marks_obtained'])
        self.assertIsNone(project['weighted_score'])
        self.assertEqual(len(result['assessment_breakdown']), 6)

    def test_an_explicit_none_is_the_same_as_missing(self):
        marks = dict(self.FULL, ENDSEM=None)
        self.assertEqual(calculate_student_result_with_assessments(marks, STOCK)['status'], 'Incomplete')

    def test_marks_above_the_maximum_or_below_zero_never_produce_a_grade(self):
        for bad in (51, -1):
            marks = dict(self.FULL, CAT1=bad)
            result = calculate_student_result_with_assessments(marks, STOCK)
            self.assertEqual(result['status'], 'Incomplete', bad)

    def test_halves_round_up_consistently(self):
        # 0.15 / 50 * 15 = 0.045 exactly; binary floats would round this down
        self.assertEqual(calculate_weighted_score(Decimal('0.15'), 50, 15), 0.05)
        self.assertEqual(calculate_weighted_score(Decimal('0.25'), 50, 15), 0.08)

    def test_the_grade_follows_the_rounded_percentage_that_is_shown(self):
        record = {'marks_obtained': Decimal('179.99'), 'maximum_marks': Decimal('200')}
        processed = process_marks_with_result([record])[0]
        self.assertEqual(processed['percentage'], 90.0)    # 89.995 rounds half up
        self.assertEqual(processed['grade'], 'S')
        self.assertEqual(processed['pass_status'], 'Pass')

    def test_legacy_totals_accept_decimals(self):
        marks = [{'marks_obtained': Decimal('85.50'), 'maximum_marks': Decimal('100')},
                 {'marks_obtained': Decimal('40.00'), 'maximum_marks': Decimal('100')}]
        result = calculate_student_result(marks)
        self.assertEqual(result['total_obtained'], 125.5)
        self.assertEqual(result['overall_percentage'], 62.75)
        self.assertEqual(result['status'], 'Pass')

    def test_legacy_status_is_incomplete_without_marks(self):
        self.assertEqual(calculate_student_result([])['status'], 'Incomplete')


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
