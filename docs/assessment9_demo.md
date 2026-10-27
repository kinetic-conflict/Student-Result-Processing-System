# Assessment 9 Demonstration Guide
## Database Operations and Back-End Implementation

### Objective
Demonstrate the Flask backend implementation, database connection, and SQL operations (INSERT, SELECT, UPDATE, DELETE, JOIN, WHERE, ORDER BY, GROUP BY, aggregates, subqueries, transactions).

### Prerequisites
- MySQL Server running with `student_result_db` database
- Flask application running
- MySQL Workbench open
- Code editor (VS Code or similar) ready to show backend code

### Video Script (Approximately 8-10 minutes)

#### Part 1: Backend Architecture Overview (1 minute)

**Action**: Show the project structure in VS Code

**Script**:
"In this demonstration, I'll show the backend implementation and database operations of the Student Result Processing System. The backend is built with Flask and uses mysql-connector-python to connect to MySQL.

Let me show you the project structure. The main application file is `app.py`, which initializes Flask and registers route blueprints. Database connectivity is handled in `db.py`, which provides functions for executing queries. Business logic is separated into route modules in the `routes/` folder - students, subjects, examinations, marks, and reports. Result calculation logic is in `services/result_service.py`."

#### Part 2: Database Connection Implementation (1 minute)

**Action**: Show db.py file

**Script**:
"Let me show you the database connection implementation. In `db.py`, we have the `get_db_connection()` function that creates a connection to MySQL using credentials from environment variables:

```python
connection = mysql.connector.connect(
    host=Config.DB_HOST,
    port=Config.DB_PORT,
    user=Config.DB_USER,
    password=Config.DB_PASSWORD,
    database=Config.DB_NAME
)
```

The `execute_query()` function handles SELECT operations and returns results as dictionaries. The `execute_update()` function handles INSERT, UPDATE, and DELETE operations. All functions use parameterized queries to prevent SQL injection."

#### Part 3: Route Handler Example (1 minute)

**Action**: Show routes/students.py

**Script**:
"Let me show you a route handler example. In `routes/students.py`, the `add_student()` function handles POST requests to add a new student:

```python
query = """
    INSERT INTO students (registration_number, full_name, email, department, semester, academic_year)
    VALUES (%s, %s, %s, %s, %s, %s)
"""
params = (registration_number, full_name, email or None, department, semester, academic_year)
execute_update(query, params)
```

This demonstrates parameterized SQL where user input is passed as parameters, not concatenated into the query string, which prevents SQL injection attacks."

#### Part 4: INSERT Operation (1 minute)

**Action**: Add a student through the frontend

**Script**:
"Now let me demonstrate the INSERT operation. I'll add a new student through the frontend with registration number 2024CS998."

**Action**: Fill form and submit

**Script**:
"The frontend sends the data to Flask, which executes an INSERT query. Let me verify this in MySQL Workbench."

**Action**: Execute verification query in MySQL Workbench

**Script**:
"In MySQL Workbench, I'll execute:
```sql
SELECT * FROM students WHERE registration_number = '2024CS998';
```
The query returns the student record, confirming the INSERT operation was successful."

#### Part 5: SELECT Operation (1 minute)

**Action**: Retrieve student through frontend

**Script**:
"Now let me demonstrate the SELECT operation. I'll search for student 2024CS001 through the frontend."

**Action**: Perform search

**Script**:
"The application retrieves the student data from MySQL. Let me show the corresponding SELECT query in MySQL Workbench:

```sql
SELECT * FROM students WHERE registration_number = '2024CS001';
```
This demonstrates that SELECT operations work correctly to retrieve data from the database."

#### Part 6: UPDATE Operation (1 minute)

**Action**: Edit a marks record

**Script**:
"Let me demonstrate the UPDATE operation. I'll go to the Marks page and edit an existing marks record. I'll change the marks obtained from 85 to 90."

**Action**: Edit marks and save

**Script**:
"The application executes an UPDATE query in MySQL. Let me verify this change."

**Action**: Execute verification query in MySQL Workbench

**Script**:
"In MySQL Workbench:
```sql
SELECT mark_id, marks_obtained, updated_at FROM marks WHERE mark_id = 1;
```
The marks_obtained is now 90, and the updated_at timestamp shows when the change was made. This confirms the UPDATE operation worked correctly."

#### Part 7: DELETE Operation (1 minute)

**Action**: Delete a test marks record

**Script**:
"Now let me demonstrate the DELETE operation. I'll delete a test marks record. First, let me create a test record to delete safely."

**Action**: Create a test marks record (quick entry)

**Script**:
"I've created a test marks record with mark_id 999. Now I'll delete it through the frontend."

**Action**: Delete the record

**Script**:
"The application executes a DELETE query. Let me verify the deletion in MySQL Workbench:

```sql
SELECT * FROM marks WHERE mark_id = 999;
```
The query returns no rows, confirming the record was successfully deleted."

#### Part 8: Multi-table JOIN (1 minute)

**Action**: Show JOIN query in MySQL Workbench

**Script**:
"Let me demonstrate a multi-table JOIN. This is a common operation that retrieves data from multiple related tables. I'll execute a query that joins students, marks, subjects, and examinations:

```sql
SELECT 
    s.registration_number,
    s.full_name,
    sub.subject_code,
    sub.subject_name,
    e.exam_name,
    m.marks_obtained,
    m.maximum_marks
FROM marks m
JOIN students s ON m.student_id = s.student_id
JOIN subjects sub ON m.subject_id = sub.subject_id
JOIN examinations e ON m.exam_id = e.exam_id
WHERE s.registration_number = '2024CS001';
```

This query combines data from four tables using foreign key relationships. The result shows student information, subject details, examination name, and marks in a single result set."

#### Part 9: WHERE and ORDER BY Clauses (1 minute)

**Action**: Execute filtered and sorted query

**Script**:
"Let me demonstrate WHERE and ORDER BY clauses. I'll filter results by examination and sort by marks in descending order:

```sql
SELECT 
    s.registration_number,
    s.full_name,
    sub.subject_name,
    m.marks_obtained
FROM marks m
JOIN students s ON m.student_id = s.student_id
JOIN subjects sub ON m.subject_id = sub.subject_id
WHERE m.exam_id = 2
ORDER BY m.marks_obtained DESC;
```

The WHERE clause filters to only show marks for examination ID 2. The ORDER BY clause sorts the results by marks_obtained in descending order, showing the highest marks first."

#### Part 10: GROUP BY and Aggregate Functions (1 minute)

**Action**: Execute aggregate query

**Script**:
"Now let me demonstrate GROUP BY with aggregate functions. I'll calculate student-wise totals and averages:

```sql
SELECT 
    s.registration_number,
    s.full_name,
    COUNT(m.mark_id) AS subject_count,
    SUM(m.marks_obtained) AS total_obtained,
    SUM(m.maximum_marks) AS total_maximum,
    (SUM(m.marks_obtained) / SUM(m.maximum_marks) * 100) AS overall_percentage
FROM marks m
JOIN students s ON m.student_id = s.student_id
GROUP BY s.student_id, s.registration_number, s.full_name
ORDER BY overall_percentage DESC;
```

This query uses:
- COUNT() to count the number of subjects
- SUM() to calculate total marks obtained and maximum marks
- The calculation in the SELECT computes overall percentage
- GROUP BY groups results by student
- ORDER BY sorts by percentage descending"

#### Part 11: Subquery (1 minute)

**Action**: Execute subquery

**Script**:
"Let me demonstrate a subquery. This query finds students whose performance exceeds the overall average:

```sql
SELECT 
    s.registration_number,
    s.full_name,
    (SUM(m.marks_obtained) / SUM(m.maximum_marks) * 100) AS overall_percentage
FROM marks m
JOIN students s ON m.student_id = s.student_id
GROUP BY s.student_id, s.registration_number, s.full_name
HAVING (SUM(m.marks_obtained) / SUM(m.maximum_marks) * 100) > (
    SELECT AVG(marks_obtained / maximum_marks * 100) 
    FROM marks
)
ORDER BY overall_percentage DESC;
```

The subquery in the HAVING clause calculates the average percentage across all marks. The main query returns only students whose overall percentage is greater than this average."

#### Part 12: Transaction Example (30 seconds)

**Action**: Show transaction code or explain

**Script**:
"For operations that require multiple related writes to succeed or fail together, the application supports transactions. For example, when inserting marks for multiple subjects for a student, we would use:

```sql
START TRANSACTION;
INSERT INTO marks (student_id, subject_id, exam_id, marks_obtained, maximum_marks) VALUES (1, 1, 2, 85.00, 100.00);
INSERT INTO marks (student_id, subject_id, exam_id, marks_obtained, maximum_marks) VALUES (1, 2, 2, 76.00, 100.00);
INSERT INTO marks (student_id, subject_id, exam_id, marks_obtained, maximum_marks) VALUES (1, 3, 2, 92.00, 100.00);
COMMIT;
```

If any INSERT fails, we can execute ROLLBACK to undo all changes. This ensures data integrity."

#### Part 13: Conclusion (30 seconds)

**Action**: Summarize

**Script**:
"In this demonstration, I've shown the complete backend implementation and database operations:

1. Database connection using mysql-connector-python with environment variables
2. Parameterized queries to prevent SQL injection
3. Route handlers that execute SQL operations
4. INSERT operation for adding data
5. SELECT operation for retrieving data
6. UPDATE operation for modifying data
7. DELETE operation for removing data
8. Multi-table JOIN to combine related data
9. WHERE and ORDER BY for filtering and sorting
10. GROUP BY with aggregate functions (COUNT, SUM, AVG)
11. Subqueries for complex filtering
12. Transactions for atomic multi-step operations

All operations were verified directly in MySQL Workbench, confirming the backend correctly communicates with the database."

### Key MySQL Queries for Demonstration

**INSERT Verification**:
```sql
SELECT * FROM students WHERE registration_number = '2024CS998';
```

**SELECT Verification**:
```sql
SELECT * FROM students WHERE registration_number = '2024CS001';
```

**UPDATE Verification**:
```sql
SELECT mark_id, marks_obtained, updated_at FROM marks WHERE mark_id = 1;
```

**DELETE Verification**:
```sql
SELECT * FROM marks WHERE mark_id = 999;
-- Should return 0 rows
```

**Multi-table JOIN**:
```sql
SELECT 
    s.registration_number,
    s.full_name,
    sub.subject_code,
    sub.subject_name,
    e.exam_name,
    m.marks_obtained,
    m.maximum_marks
FROM marks m
JOIN students s ON m.student_id = s.student_id
JOIN subjects sub ON m.subject_id = sub.subject_id
JOIN examinations e ON m.exam_id = e.exam_id
WHERE s.registration_number = '2024CS001';
```

**WHERE and ORDER BY**:
```sql
SELECT 
    s.registration_number,
    s.full_name,
    sub.subject_name,
    m.marks_obtained
FROM marks m
JOIN students s ON m.student_id = s.student_id
JOIN subjects sub ON m.subject_id = sub.subject_id
WHERE m.exam_id = 2
ORDER BY m.marks_obtained DESC;
```

**GROUP BY and Aggregates**:
```sql
SELECT 
    s.registration_number,
    s.full_name,
    COUNT(m.mark_id) AS subject_count,
    SUM(m.marks_obtained) AS total_obtained,
    SUM(m.maximum_marks) AS total_maximum,
    (SUM(m.marks_obtained) / SUM(m.maximum_marks) * 100) AS overall_percentage
FROM marks m
JOIN students s ON m.student_id = s.student_id
GROUP BY s.student_id, s.registration_number, s.full_name
ORDER BY overall_percentage DESC;
```

**Subquery**:
```sql
SELECT 
    s.registration_number,
    s.full_name,
    (SUM(m.marks_obtained) / SUM(m.maximum_marks) * 100) AS overall_percentage
FROM marks m
JOIN students s ON m.student_id = s.student_id
GROUP BY s.student_id, s.registration_number, s.full_name
HAVING (SUM(m.marks_obtained) / SUM(m.maximum_marks) * 100) > (
    SELECT AVG(marks_obtained / maximum_marks * 100) 
    FROM marks
)
ORDER BY overall_percentage DESC;
```

### Tips for Recording

1. **Code Visibility**: Ensure code snippets are readable when shown
2. **Query Results**: Zoom in on MySQL Workbench results to show actual data
3. **Pacing**: Take time to explain each operation clearly
4. **Verification**: Always verify operations in MySQL Workbench
5. **Consistency**: Use the same test records throughout for easy tracking

### What to Emphasize

- Parameterized queries for security
- Separation of concerns (routes, services, database layer)
- All SQL operations are standard MySQL syntax
- Verification proves operations actually work on real data
- Transactions ensure data integrity
- Complex queries (JOINs, subqueries) demonstrate advanced SQL knowledge

### What to Avoid

- Repeating the full interface tour from Assessment 8
- Going into too much detail about Flask framework
- Explaining HTML/CSS/JavaScript code
- Showing authentication implementation (unless required)
- Exploring every single route handler

### Verification Checklist

Before recording, ensure:
- [ ] Can show backend code files clearly
- [ ] Can demonstrate INSERT and verify in MySQL
- [ ] Can demonstrate SELECT and verify in MySQL
- [ ] Can demonstrate UPDATE and verify in MySQL
- [ ] Can demonstrate DELETE and verify in MySQL
- [ ] JOIN query returns correct combined data
- [ ] WHERE and ORDER BY filter and sort correctly
- [ ] GROUP BY with aggregates calculates correctly
- [ ] Subquery returns expected results
- [ ] All queries are ready in MySQL Workbench
