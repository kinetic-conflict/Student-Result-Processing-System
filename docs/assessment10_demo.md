> **Note:** every page now requires sign-in. Create an administrator with `flask --app app create-admin`, sign in at
> `/login`, and note that some screens described below have moved (see the menu). Code excerpts show the original
> version of the project.

# Assessment 10 Demonstration Guide
## Complete Project Workflow and Functional Validation

### Objective
Demonstrate a complete end-to-end workflow from adding a student to generating reports, including input validation, error handling, and verification that all operations work correctly with the MySQL database.

### Prerequisites
- MySQL Server running with `student_result_db` database
- Flask application running
- MySQL Workbench open
- Clean database state (or use unique test identifiers)

### Video Script (Approximately 10-12 minutes)

#### Part 1: Introduction (30 seconds)

**Action**: Show the application dashboard

**Script**:
"In this demonstration, I'll show the complete end-to-end workflow of the Student Result Processing System. I'll demonstrate adding a student, creating subjects and examinations, entering marks, retrieving results, generating reports, and verifying all operations in MySQL. This workflow shows how the application handles real data with proper validation and database integration."

#### Part 2: Add a Student (1 minute)

**Action**: Go to Students page and click Add New Student

**Script**:
"I'll start by adding a new student. I'll go to the Students page and click 'Add New Student'. I'll enter:
- Registration Number: 2024CS100 (unique for this demo)
- Full Name: Demo Student
- Email: demo@student.edu
- Department: Computer Science
- Semester: 3
- Academic Year: 2024-2025

I'll click 'Add Student'."

**Action**: Submit form

**Script**:
"The student is added successfully. The application validates that the registration number is unique before inserting into the database."

#### Part 3: Create Subjects (1 minute)

**Action**: Go to Subjects page and add subjects

**Script**:
"Now I need to create subjects for this student. I'll go to the Subjects page and add three subjects:

Subject 1:
- Subject Code: DEMO301
- Subject Name: Demo Subject 1
- Credits: 4.0
- Semester: 3

Subject 2:
- Subject Code: DEMO302
- Subject Name: Demo Subject 2
- Credits: 4.0
- Semester: 3

Subject 3:
- Subject Code: DEMO303
- Subject Name: Demo Subject 3
- Credits: 4.0
- Semester: 3

All three subjects are added successfully. The application validates that subject codes are unique and credits are within valid range (0.1-10)."

#### Part 4: Create Examination (1 minute)

**Action**: Go to Examinations page and add examination

**Script**:
"Next, I'll create an examination for entering marks. I'll go to the Examinations page and add:
- Examination Name: Demo End Semester
- Academic Year: 2024-2025
- Semester: 3
- Exam Date: 2024-12-20

The examination is created successfully."

#### Part 5: Enter Marks for Subject 1 (1 minute)

**Action**: Go to Marks page and enter marks for first subject

**Script**:
"Now I'll enter marks for the student. I'll go to the Marks page and click 'Enter New Marks'. For the first subject:
- Student: 2024CS100 - Demo Student
- Subject: DEMO301 - Demo Subject 1
- Examination: Demo End Semester 2024-2025
- Marks Obtained: 85
- Maximum Marks: 100

I'll click 'Save Marks'. The marks are saved successfully."

#### Part 6: Enter Marks for Subject 2 (30 seconds)

**Action**: Enter marks for second subject

**Script**:
"I'll enter marks for the second subject:
- Student: 2024CS100 - Demo Student
- Subject: DEMO302 - Demo Subject 2
- Examination: Demo End Semester 2024-2025
- Marks Obtained: 76
- Maximum Marks: 100

Marks saved successfully."

#### Part 7: Enter Marks for Subject 3 (30 seconds)

**Action**: Enter marks for third subject

**Script**:
"And for the third subject:
- Student: 2024CS100 - Demo Student
- Subject: DEMO303 - Demo Subject 3
- Examination: Demo End Semester 2024-2025
- Marks Obtained: 92
- Maximum Marks: 100

Marks saved successfully."

#### Part 8: Retrieve Student's Complete Result (1 minute)

**Action**: Go to Reports and select Student Report

**Script**:
"Now let me retrieve the student's complete result. I'll go to Reports and select 'Student Result Report'. I'll enter the registration number 2024CS100 and click Search."

**Action**: View the result

**Script**:
"The report shows the student's details and marks for all three subjects:
- Demo Subject 1: 85/100 (85.00% - Grade A - Pass)
- Demo Subject 2: 76/100 (76.00% - Grade B - Pass)
- Demo Subject 3: 92/100 (92.00% - Grade A+ - Pass)

The total row shows:
- Total Obtained: 253
- Total Maximum: 300
- Overall Percentage: 84.33%
- Status: Pass

This calculation is done by the backend using the formula: (total_obtained / total_maximum) * 100. All subjects are above the 40% passing threshold, so the overall status is Pass."

#### Part 9: Generate Examination-wise Report (1 minute)

**Action**: Go to Examination-wise Report

**Script**:
"Let me generate an examination-wise report. I'll select 'Examination-wise Report' and choose the 'Demo End Semester' examination."

**Action**: View the report

**Script**:
"The report shows statistics for this examination:
- Students Appeared: 1
- Total Entries: 3
- Average Percentage: 84.33%
- Passed: 3 / Failed: 0

It also lists all marks entries for this examination with percentages, grades, and pass/fail status."

#### Part 10: Demonstrate Input Validation - Invalid Marks (1 minute)

**Action**: Try to enter marks greater than maximum

**Script**:
"Now let me demonstrate input validation. I'll try to enter invalid marks - marks obtained greater than maximum marks. I'll enter:
- Marks Obtained: 150
- Maximum Marks: 100

When I click 'Save Marks', the application rejects this input with an error message: 'Marks obtained cannot exceed maximum marks!'. This validation happens both on the server side and through database constraints."

#### Part 11: Demonstrate Duplicate Entry Rejection (1 minute)

**Action**: Try to enter duplicate marks

**Script**:
"Let me try to enter duplicate marks for the same student, subject, and examination. I'll select the same combination again and enter marks."

**Action**: Attempt to submit duplicate

**Script**:
"The application rejects this with an error: 'Marks for this student, subject, and examination already exist!'. This is enforced by a unique constraint on (student_id, subject_id, exam_id) in the database, preventing duplicate entries."

#### Part 12: Demonstrate Incomplete Results Handling (1 minute)

**Action**: View incomplete results report

**Script**:
"Let me show how the system handles incomplete results. I'll go to Reports and select 'Incomplete Results'. This report shows students who have fewer than 5 subjects recorded. The demonstration student has only 3 subjects, so they appear in this report with status 'Incomplete'. The system correctly identifies that not all required marks have been entered."

#### Part 13: Verify Final Records in MySQL (1 minute)

**Action**: Switch to MySQL Workbench

**Script**:
"Now let me verify all the data in MySQL Workbench. First, I'll check the student:

```sql
SELECT * FROM students WHERE registration_number = '2024CS100';
```

The student record is present with all the details we entered."

**Action**: Verify subjects

**Script**:
"Now the subjects:
```sql
SELECT * FROM subjects WHERE subject_code LIKE 'DEMO%';
```

All three demo subjects are present."

**Action**: Verify examination

**Script**:
"The examination:
```sql
SELECT * FROM examinations WHERE exam_name = 'Demo End Semester';
```

The examination record is present."

**Action**: Verify marks

**Script**:
"And the marks:
```sql
SELECT m.*, s.subject_code, s.subject_name 
FROM marks m
JOIN subjects s ON m.subject_id = s.subject_id
WHERE m.student_id = (SELECT student_id FROM students WHERE registration_number = '2024CS100');
```

All three marks entries are present with the correct values (85, 76, 92)."

#### Part 14: Verify Calculation Accuracy (1 minute)

**Action**: Execute calculation query in MySQL

**Script**:
"Let me verify the calculation accuracy directly in MySQL:

```sql
SELECT 
    SUM(marks_obtained) AS total_obtained,
    SUM(maximum_marks) AS total_maximum,
    (SUM(marks_obtained) / SUM(maximum_marks) * 100) AS overall_percentage
FROM marks
WHERE student_id = (SELECT student_id FROM students WHERE registration_number = '2024CS100');
```

The result shows:
- Total Obtained: 253
- Total Maximum: 300
- Overall Percentage: 84.33%

This matches exactly what the application displayed, proving the calculations are accurate and not hardcoded."

#### Part 15: Conclusion (30 seconds)

**Action**: Show the application dashboard

**Script**:
"In this complete end-to-end workflow demonstration, I've shown:

1. Adding a student with unique registration number
2. Creating subjects with validation for unique codes and valid credits
3. Creating an examination
4. Entering marks for multiple subjects
5. Retrieving the student's complete result with automatic percentage and grade calculation
6. Generating examination-wise reports with statistics
7. Input validation rejecting invalid marks (greater than maximum)
8. Duplicate entry rejection through database constraints
9. Incomplete result handling
10. Verification of all data in MySQL Workbench
11. Verification that calculations match database values

The application successfully demonstrates real database integration, proper validation, accurate calculations, and comprehensive reporting. All data flows from the frontend through Flask to MySQL, and all results are retrieved from the database in real-time."

### Reproducible Calculation Example

**Test Data**:
- Student: 2024CS100 - Demo Student
- Subject 1: 85/100
- Subject 2: 76/100
- Subject 3: 92/100

**Expected Results**:
- Total Obtained: 253
- Total Maximum: 300
- Overall Percentage: 84.33%
- Subject Grades: A, B, A+
- Overall Status: Pass

**Verification Query**:
```sql
SELECT 
    SUM(marks_obtained) AS total_obtained,
    SUM(maximum_marks) AS total_maximum,
    ROUND(SUM(marks_obtained) / SUM(maximum_marks) * 100, 2) AS overall_percentage
FROM marks
WHERE student_id = (SELECT student_id FROM students WHERE registration_number = '2024CS100');
```

### Key MySQL Queries for Verification

**Verify Student**:
```sql
SELECT * FROM students WHERE registration_number = '2024CS100';
```

**Verify Subjects**:
```sql
SELECT * FROM subjects WHERE subject_code LIKE 'DEMO%';
```

**Verify Examination**:
```sql
SELECT * FROM examinations WHERE exam_name = 'Demo End Semester';
```

**Verify Marks**:
```sql
SELECT m.*, s.subject_code, s.subject_name 
FROM marks m
JOIN subjects s ON m.subject_id = s.subject_id
WHERE m.student_id = (SELECT student_id FROM students WHERE registration_number = '2024CS100');
```

**Verify Calculation**:
```sql
SELECT 
    SUM(marks_obtained) AS total_obtained,
    SUM(maximum_marks) AS total_maximum,
    ROUND(SUM(marks_obtained) / SUM(maximum_marks) * 100, 2) AS overall_percentage
FROM marks
WHERE student_id = (SELECT student_id FROM students WHERE registration_number = '2024CS100');
```

### Tips for Recording

1. **Consistency**: Use the same test student (2024CS100) throughout
2. **Clarity**: Ensure form inputs and validation messages are visible
3. **Verification**: Always show MySQL verification after each major operation
4. **Pacing**: Take time to explain each step clearly
5. **Accuracy**: Verify calculations match exactly between application and MySQL

### What to Emphasize

- The workflow is complete and reproducible
- All validation happens at both application and database level
- Calculations are accurate and verified in MySQL
- Reports are generated from real database data
- Error handling prevents invalid data entry
- The system handles edge cases (incomplete results, duplicates)
- Database constraints enforce data integrity

### What to Avoid

- Using the demonstration student from seed data (2024CS001) - create a new one
- Skipping verification steps
- Not showing error messages clearly
- Using different identifiers inconsistently
- Rushing through the workflow

### Test Scenario Summary

1. **Add Student**: 2024CS100 - Demo Student
2. **Add Subjects**: DEMO301, DEMO302, DEMO303
3. **Add Examination**: Demo End Semester 2024-2025
4. **Enter Marks**: 85/100, 76/100, 92/100
5. **Expected Result**: 253/300, 84.33%, Pass
6. **Validation Tests**:
   - Try marks > maximum (should fail)
   - Try duplicate entry (should fail)
7. **Reports**:
   - Student report
   - Examination report
   - Incomplete results
8. **MySQL Verification**: All data present and calculations accurate

### Verification Checklist

Before recording, ensure:
- [ ] Can add a new student with unique registration number
- [ ] Can add subjects with unique codes
- [ ] Can add an examination
- [ ] Can enter marks for multiple subjects
- [ ] Student report shows correct totals and percentage
- [ ] Examination report shows correct statistics
- [ ] Invalid marks (negative or > maximum) are rejected
- [ ] Duplicate marks entries are rejected
- [ ] Incomplete results are identified correctly
- [ ] All data can be verified in MySQL Workbench
- [ ] Calculations in application match MySQL calculations
- [ ] Reports are generated from database data, not hardcoded

### Cleanup After Demo

After recording, you may want to clean up the test data:

```sql
DELETE FROM marks WHERE student_id = (SELECT student_id FROM students WHERE registration_number = '2024CS100');
DELETE FROM subjects WHERE subject_code LIKE 'DEMO%';
DELETE FROM examinations WHERE exam_name = 'Demo End Semester';
DELETE FROM students WHERE registration_number = '2024CS100';
```
