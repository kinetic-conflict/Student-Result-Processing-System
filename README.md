# Student Result Processing System

A Flask + MySQL web application for managing student academic results, with sign-in and three roles
(administrator, faculty, student). Built as a DBMS course project and meant to run on one computer.

## What it does

| Role | Can do |
|------|--------|
| **Administrator** | Manage students, subjects, examinations, faculty (add, edit, deactivate, delete) and their subject assignments. Create, edit, deactivate accounts and reset passwords. Enter or correct any mark. Change the assessment weights. Read the audit log and all reports. |
| **Faculty** | See their own subjects. Enter and correct marks **only** for subjects assigned to them, for students in that subject's semester. See results for those subjects. |
| **Student** | See **only their own** results, assessment by assessment, and print their own marksheet. |

Highlights: password hashing, server-side permission checks on every request, CSRF protection, login rate limiting,
session expiry, an audit trail of changes, pagination and search on long lists, and tracked database migrations.
The interface has a light and a dark theme: it follows the system setting, and the button in the top bar overrides it
(the choice is remembered in the browser). Printed marksheets always use the light colours.

### Result rules (as implemented)

These come from the original project and its tests. Nothing was added.

| Percentage | Grade | | Component | Max marks | Weight |
|-----------:|:-----:|-|-----------|----------:|-------:|
| 90 and above | S | | CAT1 | 50 | 15% |
| 80 to 89.99 | A | | CAT2 | 50 | 15% |
| 70 to 79.99 | B | | CAT3 | 50 | 15% |
| 60 to 69.99 | C | | Assignment | 50 | 10% |
| 50 to 59.99 | D | | Project | 100 | 20% |
| 40 to 49.99 | E | | End Semester | 100 | 25% |
| below 40 | F | | | | |

- **Pass mark: 40%.**
- A weighted result needs **every** component. If one is missing or out of range the result is **Incomplete**: no
  total and no grade is shown.
- Each figure is rounded half-up to two decimals, and the grade is taken from the rounded figure that is displayed.
- Results are calculated when they are viewed, so they always match the marks currently stored.
- The component maximums and weights live in the `assessments` table and can be changed by an administrator
  (Administration, Assessment settings). The weights must total exactly 100.
- **GPA / CGPA are not calculated.** No grade-point table exists in this project. Supply one if you want it.
- The legacy per-examination marks (`marks` table) are still supported. A legacy result passes only if every subject
  reaches 40%.

## Technology

Python 3 and Flask, MySQL 8.0.16 or newer (earlier versions do not enforce `CHECK` constraints),
`mysql-connector-python`, Jinja2 templates, Bootstrap 5 (loaded from a CDN, so the pages need internet access).

## Project layout

```
app.py                    create_app() and the run command; BLUEPRINTS = who may open what
config.py                 reads and validates .env settings
db.py                     database access (queries, transaction())
security.py               sessions, CSRF, route guards, response headers
cli.py                    flask commands: migrate, create-admin, backup
routes/                   one module per screen group (students, assessments, users_admin, ...)
services/                 business rules with no Flask in them (results, access, auth, audit, ...)
templates/, static/       pages, styles, a little JavaScript
database/                 schema.sql, seed*.sql, queries.sql, verification.sql, migrations/
tests/                    pytest suite (needs a throwaway MySQL for the database tests)
docs/                     database design, audit report, demonstration guides
```

## Set up (Windows, PowerShell)

You need Python 3.8+ and MySQL Server 8.x. Replace paths and passwords with your own.

```powershell
cd D:\ACADEMICS\1_VIT\DBMS_Project
python -m venv venv
.\venv\Scripts\Activate
pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` in an editor and fill in the two required values. Never paste them into a chat or commit the file.

```powershell
python -c "import secrets; print(secrets.token_hex(32))"     # put the output after SECRET_KEY=
```

`DB_PASSWORD=` takes your MySQL password. The application will not start without both. Other settings and their
defaults are listed in `.env.example`.

On Linux or macOS the same steps work with `python3 -m venv venv`, `source venv/bin/activate` and `cp .env.example .env`.

### New installation

PowerShell does not support the `<` redirect, so run the scripts from the MySQL prompt (or MySQL Workbench):

```powershell
mysql -u root -p
```
```sql
source database/schema.sql;
source database/migration_add_assessments.sql;
source database/seed.sql;                 -- optional: synthetic sample data
source database/seed_vit_students.sql;    -- optional: more synthetic sample data
exit
```

Sample *assessment marks* are not in those files. To add them for the synthetic students only, run
`flask --app app seed-demo` (see [Sample marks](#sample-marks)) after the steps below.

Then, back in PowerShell with the virtual environment active:

```powershell
flask --app app migrate            # adds accounts, faculty and audit tables
flask --app app create-admin       # asks for a username and a password (hidden)
python app.py
```

Open <http://127.0.0.1:5000> and sign in. The seed files create **no** accounts and no passwords exist in them.

### Existing installation (data you want to keep)

1. **Back up first.** MySQL cannot undo schema changes.
   ```powershell
   flask --app app backup
   ```
   This writes a private, timestamped `.sql` file to `backups\` and checks it is not empty. It needs `mysqldump` on
   your PATH, or pass `--mysqldump "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe"`. The password is
   passed through the environment, not on the command line.
2. Add `SECRET_KEY` to your existing `.env` (see above).
3. Apply the new migrations. Do **not** run `schema.sql` or the seed files again.
   ```powershell
   flask --app app migrate
   ```
   It lists what it will do and asks whether you made a backup. Existing rows, hashes and roles are left as they are.
4. Create your first administrator with `flask --app app create-admin`.
5. Optional: restore the backup into a *different* database to prove it works, for example
   `mysql -u root -p -e "CREATE DATABASE restore_check"` then `source backups/<file>.sql` after `USE restore_check;`.

The old `seed.sql` inserted an `admin` user whose password hash was invalid, so it could not be used to sign in.
If your database has that row, the command above still works with another username; the old row can be deactivated
from the Accounts page.

## Day-to-day use

**Administrator**
1. *Administration, Faculty*: add faculty members. Open *Subjects* on a row to assign the subjects they teach.
   *Deactivate* suspends a person and can be undone. *Delete* is permanent: it removes the person, their login and
   their subject assignments, after a confirmation. Student marks and results are never touched, and the deletion is
   written to the audit log.
2. *Administration, Accounts*: *New account* creates one login (admin, faculty or student) and shows a **temporary
   password once**. *Create all student accounts* does it for everyone who has none, with one password each, on a
   page you can print. Copy them then; they cannot be looked up later.
3. Everyone must replace their temporary password the first time they sign in.
4. *Reset password* issues a new temporary password and signs the person out everywhere. *Deactivate* blocks sign-in
   at once, including for open sessions. The last active administrator cannot be deactivated.

**Faculty**: *My subjects* lists their subjects. *Enter marks* opens a sheet of every student in that subject's
semester against every component. Leave a box empty to keep the stored mark. Out-of-range or malformed values are
rejected and nothing is saved.

**Students**: *My results* shows their results; *Marksheet* is a print-ready page.

## Sample marks

`flask --app app seed-demo` adds synthetic continuous-assessment marks so the grids, results and reports have something
to show. It is explicit (nothing runs it for you) and cautious:

- It only touches students whose email ends in `@students.example`, the reserved domain of the sample seed files.
  Real students are never read or written.
- It only adds marks that are missing. An existing mark is never changed or removed, and running it again adds nothing.
- It prints how many marks it will add and asks before writing (`--yes` skips the question). The run is audited.
- The numbers are deterministic, not random: each component is the student's end-semester percentage plus a fixed
  offset, rounded to the nearest half mark. A few records are deliberately left unfinished (no row, so the result is
  *Incomplete*) and one has a real zero, so the sample shows that missing and zero are different.

Which subjects a sample student has marks in comes from the examination marks that student already has, because the
schema has no enrolment table.

## Examinations and assessments

They are two separate things and stay separate (details in `docs/database_design.md`).

- An **examination** is a named sitting (name, academic year, semester). Its marks (the *Marks* page) each carry their
  own maximum. The same name, year and semester cannot be added twice.
- An **assessment component** (CAT1, CAT2, CAT3, ASSIGN, PROJECT, ENDSEM) has one maximum and one weight, and its marks
  (the *Assessments* page) combine into the weighted result.
- A component that was never entered is *missing* and makes the result *Incomplete*. A zero is a real mark.
- `database/integrity_checks.sql` is a read-only check of both: run `source database/integrity_checks.sql;` at the MySQL
  prompt. No rows means no problem; rows starting "Review:" are questions, not errors.

## Security notes

- Passwords are salted scrypt hashes. No default or shared password exists. Temporary passwords are random, shown
  once on the response page, and never logged, flashed or written to the audit log.
- Roles are checked on the server for every request. The role is read from the database, so editing a cookie or form
  does nothing. Students are identified by their account, never by an id in the URL or form.
- Sessions: HttpOnly, SameSite=Lax cookies; idle timeout (default 30 minutes) and a 12-hour absolute limit. Logging
  out, changing or resetting a password, or deactivating an account ends every session of that user.
- Failed sign-ins are limited per account-and-address and per address. The counters live in memory, so they reset when
  the app restarts and are not shared between processes.
- CSRF tokens on every form. A content security policy, `X-Frame-Options`, `nosniff` and `no-store` caching headers.
- Errors shown to people never contain SQL, file paths or tracebacks; details go to the server log.
- The server listens on `127.0.0.1` only and debug mode is off unless you set `FLASK_DEBUG=1`.
- Run the application under a dedicated MySQL account instead of `root`: `SELECT, INSERT, UPDATE, DELETE` on this
  database for day-to-day use, plus `CREATE` and `ALTER` only for the moment you run `flask --app app migrate`.
- All sign-in attempts from computers behind one shared address (a college network, a proxy) count together toward the
  per-address limit, so one noisy client can block the others for the window.
- Serving it to other computers needs HTTPS and a real WSGI server (for example Waitress on Windows); set
  `SESSION_COOKIE_SECURE=1` when you do. That setup is outside this project.

## Tests

```powershell
pip install -r requirements-dev.txt
python -m pytest
```

Without a test database, the database-backed tests are **skipped** and the rest run. To run everything, start a
throwaway MySQL (never one holding real data) and point the tests at it. Each test run creates and drops its own
`srps_test_*` database and refuses to touch any other name.

```powershell
docker run -d --name srps-test-mysql -e MYSQL_ROOT_PASSWORD=<choose-a-throwaway-password> -p 127.0.0.1:33306:3306 mysql:8.4
$env:SRPS_TEST_DB_HOST = "127.0.0.1"
$env:SRPS_TEST_DB_PORT = "33306"
$env:SRPS_TEST_DB_USER = "root"
$env:SRPS_TEST_DB_PASSWORD = "<the same throwaway password>"
python -m pytest
```

The suite covers configuration, SQL script safety, migrations on a database that already holds data, hashing and
sessions, login throttling, CSRF, every route for every role (including attempts to reach another student's data),
mark entry rules, result calculations and the audit log.

## Database scripts

| File | Purpose | Safe to re-run? |
|------|---------|-----------------|
| `schema.sql` | Creates the core tables if missing | Yes. Never drops or alters anything |
| `migration_add_assessments.sql` | Assessment tables and the stock components | **Run once.** Re-running copies the legacy marks again, bringing back any copied mark deleted since (see `docs/database_design.md`) |
| `migrations/NNN_*.sql` | Accounts, faculty, audit log | Run through `flask --app app migrate`; each applies once |
| `seed.sql`, `seed_vit_students.sql` | **Synthetic** sample data | Yes; rows are matched on their natural keys |
| `queries.sql` | Reference queries; the INSERT/UPDATE/DELETE examples are commented out | Yes (read-only) |
| `verification.sql` | Demonstration checks for the course assessments | Yes (read-only) |
| `integrity_checks.sql` | Data checks: weights, ranges, duplicate examinations, semester mismatches | Yes (read-only) |

## Known limitations

- No email, so no self-service password recovery: an administrator resets passwords.
- A faculty member's students are those in the subject's semester. The schema has no classes or sections.
- An account's role and linked record are fixed when it is created.
- Assessment marks have no examination or academic year: one mark per student, subject and component, so a re-attempt
  overwrites the first. Examination marks are not checked against the subject's semester. Both are policy questions.
- A faculty member who is deleted is gone for good. Deactivate instead if the person may return.
- Legacy per-examination marks can only be changed by administrators; faculty work with assessment marks.
- The weighted result needs all six components; there is no "absent" or "withheld" status because none was defined.
- The "top performers" (85%) and "incomplete" (fewer than 5 subjects) reports use working assumptions, stated on the pages.
- The login rate limiter is per process (see above). Bootstrap is loaded from a CDN.

## Troubleshooting

| Message | Fix |
|---------|-----|
| `SECRET_KEY is not set` / `DB_PASSWORD is not set` | Add the value to `.env` (see Set up). |
| `Could not connect to the MySQL database` | Start MySQL (`net start MySQL80`), then check `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` in `.env`. |
| `Base tables are missing` from `migrate` | New install: run `schema.sql` and `migration_add_assessments.sql` first. |
| Too many failed attempts | Wait for the window (15 minutes by default) or restart the app. |
| `Address already in use` | Set `APP_PORT` in `.env` to another number. |
| `ModuleNotFoundError: flask` | Activate the virtual environment and run `pip install -r requirements.txt`. |

## Documentation

- `docs/database_design.md`: tables, relationships, constraints, migrations.
- `docs/AUDIT_REPORT.md`: the initial audit and what was done about each finding.
- `docs/assessment8_demo.md`, `assessment9_demo.md`, `assessment10_demo.md`: demonstration guides (sign in first).
- `PROJECT_SUMMARY.md`, `UPGRADE_SUMMARY.md`: historical notes from earlier versions of the project.

## License

Created for academic purposes as part of a DBMS course project.
