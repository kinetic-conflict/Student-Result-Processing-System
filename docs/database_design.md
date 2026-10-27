# Database Design Documentation

## Overview

The Student Result Processing System uses a normalized relational database schema designed in MySQL 8.x. The database enforces data integrity through constraints, foreign keys, and indexes for optimal query performance. The system now includes a 6-component weighted assessment system for accurate grade calculation.

## ER Diagram

```
┌─────────────┐
│   students  │
├─────────────┤
│ student_id  │───┐
│ reg_no      │   │
│ full_name   │   │
│ email       │   │
│ department  │   │
│ semester    │   │
│ acad_year   │   │
└─────────────┘   │
                  │
                  │ 1
                  │
                  │ N
                  │
         ┌────────▼────────┐
         │ assessment_marks│
         ├─────────────────┤
         │ ass_mark_id     │───┐
         │ student_id      │   │
         │ subject_id      │   │
         │ assessment_id   │───┼───┐
         │ marks_obtained  │   │   │
         └─────────────────┘   │   │
                                │   │
                ┌───────────────┼───┼──────────────┐
                │               │   │              │
                │ N             │ N │              │ N
                │               │   │              │
        ┌───────▼──────┐ ┌─────▼──────┐ ┌───────▼──────┐
        │   subjects   │ │assessments│ │   marks (legacy)│
        ├──────────────┤ ├────────────┤ ├───────────────┤
        │ subject_id   │ │assess_id   │ │ mark_id        │
        │ subject_code │ │assess_code │ │ student_id     │
        │ subject_name │ │assess_name │ │ subject_id     │
        │ credits      │ │max_marks   │ │ exam_id        │
        │ semester     │ │weight_%    │ │ marks_obtained │
        └──────────────┘ └────────────┘ │ maximum_marks │
                                 └───────────────┘
                                                
┌─────────────┐           ┌─────────────┐
│examinations  │           │    users    │
├─────────────┤           ├─────────────┤
│ exam_id      │           │ user_id     │
│ exam_name    │           │ username    │
│ acad_year    │           │ password    │
│ semester     │           │ role        │
│ exam_date    │           └─────────────┘
└─────────────┘
```

## Table Descriptions

### 1. students

Stores student information with VIT-style registration numbers.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| student_id | INT | PRIMARY KEY, AUTO_INCREMENT | Unique student identifier |
| registration_number | VARCHAR(20) | UNIQUE, NOT NULL | VIT-style registration (e.g., 23BCE1042) |
| full_name | VARCHAR(100) | NOT NULL | Student's full name |
| email | VARCHAR(100) | UNIQUE, NULLABLE | VIT student email (firstname.lastname2025@vitstudent.ac.in) |
| department | VARCHAR(50) | NULLABLE | Department/branch (Bioengineering, IT, etc.) |
| semester | INT | NULLABLE, CHECK (1-10) | Current semester |
| academic_year | VARCHAR(10) | NULLABLE | Academic year (e.g., 2024-2025) |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |

**Indexes**:
- PRIMARY KEY on student_id
- UNIQUE index on registration_number
- Index on full_name
- Index on semester

**Constraints**:
- `chk_semester`: semester > 0 AND semester <= 10

### 2. subjects

Stores subject information with VIT-style course codes.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| subject_id | INT | PRIMARY KEY, AUTO_INCREMENT | Unique subject identifier |
| subject_code | VARCHAR(20) | UNIQUE, NOT NULL | VIT course code (e.g., CSE3001) |
| subject_name | VARCHAR(100) | NOT NULL | Subject name |
| credits | DECIMAL(3,1) | NOT NULL, CHECK (0.1-10) | Credit points |
| semester | INT | NOT NULL, CHECK (1-10) | Semester in which subject is offered |

**Indexes**:
- PRIMARY KEY on subject_id
- UNIQUE index on subject_code
- Index on semester

**Constraints**:
- `chk_credits`: credits > 0 AND credits <= 10
- `chk_subject_semester`: semester > 0 AND semester <= 10

### 3. examinations

Stores examination information.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| exam_id | INT | PRIMARY KEY, AUTO_INCREMENT | Unique examination identifier |
| exam_name | VARCHAR(100) | NOT NULL | Examination name |
| academic_year | VARCHAR(10) | NOT NULL | Academic year |
| semester | INT | NOT NULL, CHECK (1-10) | Semester |
| exam_date | DATE | NULLABLE | Examination date |

**Indexes**:
- PRIMARY KEY on exam_id
- Index on semester
- Index on academic_year

**Constraints**:
- `chk_exam_semester`: semester > 0 AND semester <= 10

### 4. marks (Legacy Table)

Stores marks obtained by students in subjects for examinations (legacy system for backward compatibility).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| mark_id | INT | PRIMARY KEY, AUTO_INCREMENT | Unique marks record identifier |
| student_id | INT | NOT NULL, FOREIGN KEY | Reference to students.student_id |
| subject_id | INT | NOT NULL, FOREIGN KEY | Reference to subjects.subject_id |
| exam_id | INT | NOT NULL, FOREIGN KEY | Reference to examinations.exam_id |
| marks_obtained | DECIMAL(6,2) | NOT NULL, CHECK (>=0) | Marks obtained by student |
| maximum_marks | DECIMAL(6,2) | NOT NULL, CHECK (>0) | Maximum possible marks |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |
| updated_at | TIMESTAMP | ON UPDATE CURRENT_TIMESTAMP | Last update timestamp |

**Foreign Keys**:
- `fk_marks_student`: student_id → students.student_id (ON DELETE CASCADE)
- `fk_marks_subject`: subject_id → subjects.subject_id (ON DELETE CASCADE)
- `fk_marks_exam`: exam_id → examinations.exam_id (ON DELETE CASCADE)

**Unique Constraint**:
- `uq_student_subject_exam`: UNIQUE (student_id, subject_id, exam_id)

### 5. assessments (NEW)

Defines the 6 assessment components with their weights.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| assessment_id | INT | PRIMARY KEY, AUTO_INCREMENT | Unique assessment identifier |
| assessment_code | VARCHAR(20) | UNIQUE, NOT NULL | Assessment code (CAT1, CAT2, CAT3, ASSIGN, PROJECT, ENDSEM) |
| assessment_name | VARCHAR(50) | NOT NULL | Full assessment name |
| maximum_marks | DECIMAL(6,2) | NOT NULL, CHECK (>0) | Maximum marks for this assessment |
| weight_percentage | DECIMAL(5,2) | NOT NULL, CHECK (0-100) | Weight in final grade (e.g., 15 for 15%) |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |

**Assessment Components**:
1. CAT1: Continuous Assessment Test 1 - 50 marks, 15% weight
2. CAT2: Continuous Assessment Test 2 - 50 marks, 15% weight
3. CAT3: Continuous Assessment Test 3 - 50 marks, 15% weight
4. ASSIGN: Assignment - 50 marks, 10% weight
5. PROJECT: Project - 100 marks, 20% weight
6. ENDSEM: End Semester Examination - 100 marks, 25% weight

**Total Weight**: 100%

**Constraints**:
- `chk_weight`: weight_percentage > 0 AND weight_percentage <= 100
- `chk_max_marks`: maximum_marks > 0

### 6. assessment_marks (NEW)

Stores individual assessment scores for students.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| assessment_mark_id | INT | PRIMARY KEY, AUTO_INCREMENT | Unique assessment mark identifier |
| student_id | INT | NOT NULL, FOREIGN KEY | Reference to students.student_id |
| subject_id | INT | NOT NULL, FOREIGN KEY | Reference to subjects.subject_id |
| assessment_id | INT | NOT NULL, FOREIGN KEY | Reference to assessments.assessment_id |
| marks_obtained | DECIMAL(6,2) | NOT NULL, CHECK (>=0) | Marks obtained in this assessment |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |
| updated_at | TIMESTAMP | ON UPDATE CURRENT_TIMESTAMP | Last update timestamp |

**Foreign Keys**:
- `fk_assessment_marks_student`: student_id → students.student_id (ON DELETE CASCADE)
- `fk_assessment_marks_subject`: subject_id → subjects.subject_id (ON DELETE CASCADE)
- `fk_assessment_marks_assessment`: assessment_id → assessments.assessment_id (ON DELETE CASCADE)

**Unique Constraint**:
- `uq_student_subject_assessment`: UNIQUE (student_id, subject_id, assessment_id)
  - Prevents duplicate assessment entries for same student, subject, and assessment type

**Constraints**:
- `chk_assessment_marks_obtained`: marks_obtained >= 0
- `chk_assessment_not_exceed_max`: marks_obtained <= (maximum_marks from assessments table)

### 7. users

Stores user accounts for authentication (optional feature).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| user_id | INT | PRIMARY KEY, AUTO_INCREMENT | Unique user identifier |
| username | VARCHAR(50) | UNIQUE, NOT NULL | Username |
| password_hash | VARCHAR(255) | NOT NULL | Hashed password |
| role | VARCHAR(20) | NOT NULL, DEFAULT 'admin' | User role (admin, faculty, etc.) |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Account creation timestamp |

## Relationships

### One-to-Many Relationships

1. **students → assessment_marks**: One student can have many assessment marks
   - Foreign key: assessment_marks.student_id → students.student_id
   - Cascade delete: Deleting a student deletes all associated assessment marks

2. **subjects → assessment_marks**: One subject can have many assessment marks
   - Foreign key: assessment_marks.subject_id → subjects.subject_id
   - Cascade delete: Deleting a subject deletes all associated assessment marks

3. **assessments → assessment_marks**: One assessment type can have many marks records
   - Foreign key: assessment_marks.assessment_id → assessments.assessment_id
   - Cascade delete: Deleting an assessment type deletes all associated marks

### Many-to-Many Relationship (Resolved)

The relationship between students and subjects is many-to-many through assessment_marks:
- A student can have assessment marks in multiple subjects
- A subject can have assessment marks from multiple students
- This is resolved by the assessment_marks table with foreign keys to both

## Weighted Assessment Calculation

### Formula

For each assessment component:
```
weighted_score = (marks_obtained / maximum_marks) * weight_percentage
```

Total weighted score:
```
total_weighted_score = Σ weighted_score (for all 6 assessments)
```

### Example Calculation

Student scores:
- CAT1: 42/50 (84%) → weighted: 84 * 0.15 = 12.6
- CAT2: 38/50 (76%) → weighted: 76 * 0.15 = 11.4
- CAT3: 45/50 (90%) → weighted: 90 * 0.15 = 13.5
- ASSIGN: 40/50 (80%) → weighted: 80 * 0.10 = 8.0
- PROJECT: 85/100 (85%) → weighted: 85 * 0.20 = 17.0
- ENDSEM: 78/100 (78%) → weighted: 78 * 0.25 = 19.5

**Total Weighted Score**: 12.6 + 11.4 + 13.5 + 8.0 + 17.0 + 19.5 = 82.0/100

**Grade**: A (80-89%)
**Status**: Pass (≥40%)

## Grading System (VIT Style)

| Percentage | Grade | Description |
|------------|-------|-------------|
| 90-100% | S | Outstanding |
| 80-89% | A | Excellent |
| 70-79% | B | Very Good |
| 60-69% | C | Good |
| 50-59% | D | Satisfactory |
| 40-49% | E | Pass |
| Below 40% | F | Fail |

**Pass Threshold**: 40% per subject and overall

## Normalization

The database follows Third Normal Form (3NF):
1. **First Normal Form (1NF)**: All columns contain atomic values
2. **Second Normal Form (2NF)**: All non-key attributes are fully dependent on the primary key
3. **Third Normal Form (3NF)**: No transitive dependencies

## Data Integrity

### Entity Integrity
- Primary keys ensure each record is uniquely identifiable
- AUTO_INCREMENT generates unique IDs

### Referential Integrity
- Foreign key constraints ensure references to valid records
- CASCADE delete maintains consistency when parent records are deleted

### Domain Integrity
- CHECK constraints enforce valid data ranges
- NOT NULL constraints ensure required fields are filled
- UNIQUE constraints prevent duplicate values

### Business Logic Integrity
- Unique constraints prevent duplicate entries
- CHECK constraints ensure marks are valid (non-negative, not exceeding maximum)
- Assessment weights sum to 100%

## Migration Strategy

The migration script `migration_add_assessments.sql`:
1. Creates the new `assessments` table
2. Creates the new `assessment_marks` table
3. Inserts the 6 assessment components
4. Migrates existing marks from the legacy `marks` table to `assessment_marks` as ENDSEM marks
5. Uses `INSERT IGNORE` to prevent errors on re-execution
6. Preserves all existing data

## Sample Data

The seed data includes:
- 33 students (8 original + 25 VIT-style)
- 28 subjects (8 original + 20 VIT-style)
- 6 examinations (4 original + 2 new)
- 6 assessment components
- Assessment marks for demonstration

### VIT-Style Students Examples

Registration numbers follow the pattern: YYXXXXXXX
- YY: Admission year (23, 24, 25)
- XXX: Program code (BCE, BIT, BDS, BAI, BEC, BME)
- XXXXX: Unique identifier

Examples:
- 23BCE1042: 2023 Bioengineering student
- 24BIT0237: 2024 Information Technology student
- 25BAI0493: 2025 Artificial Intelligence student

Email pattern: firstname.lastnameYYYY@vitstudent.ac.in
- YYYY matches admission year

## Security Considerations

1. **Parameterized Queries**: All database queries use parameterized statements
2. **Password Hashing**: User passwords are hashed before storage
3. **Environment Variables**: Database credentials stored in environment variables
4. **Least Privilege**: Use dedicated MySQL user with limited privileges in production

## Performance Considerations

1. **Indexes**: Strategic indexing on frequently queried columns
2. **Foreign Keys**: Properly indexed for faster JOIN operations
3. **Query Optimization**: Complex queries use appropriate WHERE clauses and JOINs
4. **Connection Pooling**: Database connections properly closed after use
