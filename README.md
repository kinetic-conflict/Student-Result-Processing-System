# Student Result Processing System

A full-stack web application for managing student academic results, built with Flask (Python) and MySQL 8.x. This system demonstrates real database connectivity, CRUD operations, result processing, and comprehensive reporting for DBMS academic projects.

## Features

- **Student Management**: Add, view, edit, search, and delete student records with VIT-style registration numbers
- **Subject Management**: Manage subjects with VIT-style course codes, names, credits, and semesters
- **Examination Management**: Create and manage examinations
- **Marks Entry**: Enter and manage student marks with validation (legacy system)
- **Assessment System**: 6-component weighted assessment system:
  - CAT1: 50 marks, 15% weight
  - CAT2: 50 marks, 15% weight
  - CAT3: 50 marks, 15% weight
  - Assignment: 50 marks, 10% weight
  - Project: 100 marks, 20% weight
  - End Semester: 100 marks, 25% weight
- **Result Processing**: Automatic calculation of weighted scores, percentages, grades (VIT style: S, A, B, C, D, E, F), and pass/fail status
- **Result Search**: Search results by registration number or student name
- **Comprehensive Reports**: 
  - Individual student result reports
  - Examination-wise reports
  - Subject-wise performance reports
  - Top performers
  - Failed students
  - Incomplete results
- **Database-Backed**: All data stored in MySQL with proper constraints and referential integrity

## Technology Stack

- **Database**: MySQL Server 8.x
- **Backend**: Python Flask
- **Database Connector**: mysql-connector-python
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Templating**: Jinja2

## Project Structure

```
DBMS_Project/
├── app.py                      # Flask application entry point
├── config.py                   # Configuration management
├── db.py                       # Database connection and query functions
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
├── database/
│   ├── schema.sql             # Database schema creation
│   ├── seed.sql               # Sample data insertion
│   ├── migration_add_assessments.sql  # Assessment system migration
│   ├── seed_vit_students.sql  # VIT-style students and subjects
│   ├── queries.sql            # Important SQL queries
│   └── verification.sql       # Assessment verification queries
├── routes/
│   ├── __init__.py
│   ├── students.py            # Student management routes
│   ├── subjects.py            # Subject management routes
│   ├── examinations.py        # Examination management routes
│   ├── marks.py               # Marks entry routes (legacy)
│   ├── assessments.py         # Assessment system routes (NEW)
│   └── reports.py             # Report generation routes
├── services/
│   ├── __init__.py
│   └── result_service.py      # Result calculation logic (updated)
├── templates/
│   ├── base.html              # Base template with navigation
│   ├── dashboard.html         # Dashboard page
│   ├── students.html          # Student management page
│   ├── subjects.html          # Subject management page
│   ├── examinations.html      # Examination management page
│   ├── marks.html             # Marks entry page (legacy)
│   ├── assessments.html       # Assessment system page (NEW)
│   ├── results.html           # Result search page
│   └── reports.html           # Reports page
├── static/
│   ├── css/
│   │   └── style.css          # Custom styles (updated for S grade)
│   └── js/
│       └── main.js            # JavaScript functionality
├── tests/
│   └── test_app.py            # Automated tests (updated)
└── docs/
    ├── database_design.md     # Database design documentation (updated)
    ├── assessment8_demo.md    # Assessment 8 demonstration guide
    ├── assessment9_demo.md    # Assessment 9 demonstration guide
    └── assessment10_demo.md   # Assessment 10 demonstration guide
```

## Windows Setup Instructions

### Prerequisites

1. **Python 3.8 or higher**
   - Download from: https://www.python.org/downloads/
   - During installation, check "Add Python to PATH"

2. **MySQL Server 8.x**
   - Download from: https://dev.mysql.com/downloads/mysql/
   - Install MySQL Server and MySQL Workbench (recommended)
   - Set a root password during installation (remember it!)

3. **Git** (optional, for version control)
   - Download from: https://git-scm.com/download/win

### Step-by-Step Setup

#### 1. Navigate to Project Directory

Open PowerShell and navigate to the project folder:

```powershell
cd D:\ACADEMICS\1_VIT\DBMS_Project
```

#### 2. Create Python Virtual Environment

```powershell
python -m venv venv
```

#### 3. Activate Virtual Environment

```powershell
.\venv\Scripts\Activate
```

You should see `(venv)` in your command prompt indicating the virtual environment is active.

#### 4. Install Python Dependencies

```powershell
pip install -r requirements.txt
```

This will install:
- Flask
- mysql-connector-python
- python-dotenv
- Werkzeug

#### 5. Configure Environment Variables

Create a `.env` file in the project root:

```powershell
Copy-Item .env.example .env
```

Edit the `.env` file with your MySQL credentials:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=DBMS@Vellore2026
DB_NAME=student_result_db
```

Replace `your_mysql_password` with your actual MySQL root password.

#### 6. Start MySQL Service

If MySQL is not running, start it:

```powershell
# Using MySQL as a Windows service
net start MySQL80

# Or if you have a different service name
net start MySQL
```

Alternatively, start MySQL from MySQL Workbench or the MySQL Notifier.

#### 7. Create Database and Tables

Open MySQL Workbench and connect to your MySQL server using your root password.

Execute the SQL scripts in order:

1. **schema.sql** - Creates the database and all tables
   - Open `database/schema.sql` in MySQL Workbench
   - Click the lightning bolt icon to execute
   - This creates the `student_result_db` database and all tables

2. **seed.sql** - Inserts sample demonstration data
   - Open `database/seed.sql` in MySQL Workbench
   - Click the lightning bolt icon to execute
   - This populates the database with sample students, subjects, examinations, and marks

3. **migration_add_assessments.sql** - Adds the assessment system
   - Open `database/migration_add_assessments.sql` in MySQL Workbench
   - Click the lightning bolt icon to execute
   - This adds the 6-component assessment system and migrates existing data

4. **seed_vit_students.sql** - Adds VIT-style students and subjects
   - Open `database/seed_vit_students.sql` in MySQL Workbench
   - Click the lightning bolt icon to execute
   - This adds 25 VIT-style students and VIT course codes

**Alternative: Command-Line Execution**

If you prefer using the MySQL command line:

```powershell
mysql -u root -p < database\schema.sql
mysql -u root -p < database\seed.sql
```

Enter your MySQL password when prompted.

#### 8. Verify Database Setup

In MySQL Workbench, run:

```sql
USE student_result_db;
SELECT COUNT(*) AS total_students FROM students;
SELECT COUNT(*) AS total_subjects FROM subjects;
SELECT COUNT(*) AS total_examinations FROM examinations;
SELECT COUNT(*) AS total_marks FROM marks;
```

You should see:
- 33 students (8 original + 25 VIT-style)
- 28 subjects (8 original + 20 VIT-style)
- 6 examinations (4 original + 2 new)
- 33 marks records (legacy system)
- 6 assessment components
- 0 assessment marks (until you enter them)

#### 9. Start the Flask Application

```powershell
python app.py
```

You should see output like:

```
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://0.0.0.0:5000
```

#### 10. Open the Application in Browser

Open your web browser and navigate to:

```
http://localhost:5000
```

You should see the dashboard with statistics and recent marks entries.

## Troubleshooting

### MySQL Connection Errors

**Error**: `Can't connect to MySQL server on 'localhost'`

**Solutions**:
1. Verify MySQL service is running: `net start MySQL80`
2. Check MySQL port is 3306 (default)
3. Verify your MySQL root password in `.env`
4. Check firewall settings

**Error**: `Access denied for user 'root'@'localhost'`

**Solutions**:
1. Verify password in `.env` matches your MySQL root password
2. If you forgot the password, reset it in MySQL Workbench

### Port Already in Use

**Error**: `Address already in use` when starting Flask

**Solution**:
- Change the port in `app.py` from 5000 to another port (e.g., 5001)
- Or stop the process using port 5000:
  ```powershell
  # Find the process
  netstat -ano | findstr :5000
  # Kill the process (replace PID with actual process ID)
  taskkill /PID <PID> /F
  ```

### Python Module Import Errors

**Error**: `ModuleNotFoundError: No module named 'flask'`

**Solution**:
- Ensure virtual environment is activated: `.\venv\Scripts\Activate`
- Reinstall dependencies: `pip install -r requirements.txt`

### Database Not Found

**Error**: `Unknown database 'student_result_db'`

**Solution**:
- Execute `database/schema.sql` in MySQL Workbench
- Verify database exists: `SHOW DATABASES;`

### CHECK Constraint Not Enforced

**Note**: Some MySQL versions may not enforce CHECK constraints. The application includes server-side validation to handle this.

## Running Tests

To run the automated tests:

```powershell
# Ensure virtual environment is activated
.\venv\Scripts\Activate

# Run tests
python tests\test_app.py
```

**Note**: Database integration tests require MySQL to be running and properly configured. If MySQL is not available, those tests will be skipped.

## Using the Assessment System

The new 6-component assessment system provides more accurate grade calculation:

1. **Enter Assessment Marks**: Navigate to "Assessments" in the menu
2. **Select Student and Subject**: Choose the student and subject
3. **Enter Scores**: Fill in marks for all 6 components (CAT1, CAT2, CAT3, Assignment, Project, End Semester)
4. **Calculate Result**: Use the "Calculate Result" feature to see the weighted score and grade

The system automatically:
- Calculates weighted scores for each component
- Sums the weighted scores to get the final score out of 100
- Assigns the appropriate grade (S, A, B, C, D, E, F)
- Determines pass/fail status based on 40% threshold

## Grading System

The system uses VIT-style grading:

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

## Database Queries

Important SQL queries are documented in:
- `database/queries.sql` - All important SQL operations used in the application
- `database/verification.sql` - Verification queries for assessment demonstrations

## Demonstration Student

The seed data includes a demonstration student for reproducible calculations:

- **Registration Number**: 2024CS001
- **Name**: Rahul Sharma
- **Marks** (Legacy System):
  - CS301 (Data Structures): 85/100 (85% - Grade A)
  - CS302 (DBMS): 76/100 (76% - Grade B)
  - CS303 (Operating Systems): 92/100 (92% - Grade S)
  - CS304 (Computer Networks): 78/100 (78% - Grade B)
  - CS305 (Web Technologies): 88/100 (88% - Grade A)

**Expected Result (Legacy)**:
- Total Obtained: 419
- Total Maximum: 500
- Overall Percentage: 83.8%
- Status: Pass

### Assessment System Example

For the weighted assessment system, a sample calculation:

Assessment scores:
- CAT1: 42/50 (84%) → weighted: 12.6
- CAT2: 38/50 (76%) → weighted: 11.4
- CAT3: 45/50 (90%) → weighted: 13.5
- Assignment: 40/50 (80%) → weighted: 8.0
- Project: 85/100 (85%) → weighted: 17.0
- End Semester: 78/100 (78%) → weighted: 19.5

**Total Weighted Score**: 82.0/100
**Grade**: A (80-89%)
**Status**: Pass

### VIT-Style Students

The system includes 25 VIT-style students with registration numbers like:
- 23BCE1042 (2023 Bioengineering)
- 24BIT0237 (2024 Information Technology)
- 25BAI0493 (2025 Artificial Intelligence)

Email pattern: firstname.lastnameYYYY@vitstudent.ac.in

## Assessment Demonstration Guides

Detailed guides for recording assessment demonstration videos are available in the `docs/` folder:

- `docs/assessment8_demo.md` - Frontend and Database Connectivity
- `docs/assessment9_demo.md` - Backend and Database Operations
- `docs/assessment10_demo.md` - Complete End-to-End Workflow

## Database Design Documentation

Comprehensive database design documentation is available in:
- `docs/database_design.md`

## License

This project is created for academic purposes as part of a DBMS course project.

## Support

For issues or questions, refer to the troubleshooting section above or consult the assessment demonstration guides.
