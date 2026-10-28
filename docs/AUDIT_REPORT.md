# Initial Audit Report

Student Result Processing System. Audit of commit `c35748d` (branch `main`, clean tree).
Written before any code changes. Where a later fix is noted, see the final report.

## 1. Scope and environment

| Item | Finding |
|------|---------|
| Checkout audited | `/home/ujjwal/dev/Student-Result-Processing-System` (Linux). The prompt names `D:\ACADEMICS\1_VIT\DBMS_Project` (Windows). Same repo, different machine. |
| Live MySQL data | **Not reachable from this machine.** No MySQL here, no `.env`. The real database lives on the Windows machine. |
| Python | 3.14.8 here. Pinned deps (Flask 3.0.0, mysql-connector-python 8.2.0) install and import cleanly. README says 3.8+. |
| Test baseline | `python -m unittest` runs 9 tests, all pass. They cover only `services/result_service.py`. |
| Test database | A throwaway MySQL 8.4 container is used for integration tests. The real database is never touched. |

### Baseline run (throwaway MySQL 8.4 container, empty server)

| Step | Result |
|------|--------|
| `schema.sql`, `seed.sql`, `migration_add_assessments.sql`, `seed_vit_students.sql` in README order | All apply with no errors. |
| Resulting rows | 33 students, **38** subjects, 6 exams, **28** marks, 6 assessments, **28** assessment marks, 1 user. README claims 28 subjects, 33 marks, and 0 assessment marks. |
| `queries.sql` run whole | Fails at line 24 (duplicate insert), **then silently changes student 1's email and mark 1 from 85 to 90.** H6 confirmed. |
| `seed.sql` run a second time | Fails on the first row (`Duplicate entry '2024CS001'`). M4 confirmed. |
| `users` after seeding | 1 row, `admin`, with a fabricated 96-character hash. H5 confirmed. |

## 2. Architecture

```
browser ──► Flask (app.py) ──► routes/*.py ──► db.py ──► MySQL
                │                   │
                │                   └─► services/result_service.py (pure calc)
                └─► templates/*.html (Jinja2 + Bootstrap 5 CDN) + static/
```

- Six blueprints: `students`, `subjects`, `examinations`, `marks`, `assessments`, `reports`. Two routes live in `app.py` (`/`, `/results`).
- `db.py` opens a **new connection per statement**. There is no pooling and no multi-statement transaction helper that returns data.
- Routes contain SQL, validation and presentation together. `services/` holds only the calculation code.
- Two parallel mark stores: legacy `marks` (per exam, free `maximum_marks`) and `assessment_marks` (six weighted components).

## 3. Feature inventory

| Feature | Routes | Tables | State |
|---------|--------|--------|-------|
| Students CRUD + search | `/students*` | `students` | Works. No pagination. Public. |
| Subjects CRUD + search | `/subjects*` | `subjects` | Works. Public. |
| Examinations CRUD, results | `/examinations*` | `examinations` | Works. No delete route. Public. |
| Legacy marks CRUD + filter | `/marks*` | `marks` | Works. Float parsing unguarded. |
| Assessment marks (6 components) | `/assessments*` | `assessments`, `assessment_marks` | Partial. See M1, M2, H4. |
| Weighted result calculation | `/assessments/calculate` | both | Works, but uses hardcoded weights (M1). |
| Result search | `/results` | `marks` | Works. Public (H7). |
| Reports (student, exam, subject, top, failed, incomplete) | `/reports*` | `marks` | Works on legacy marks only. Contains unsourced thresholds (M8). |
| Dashboard | `/` | counts | Works. Hides DB errors as zeros (M6). |
| **Login / logout / sessions** | none | `users` (unused) | **Missing** |
| **Roles (admin / faculty / student)** | none | none | **Missing** |
| **Faculty records, subject assignments** | none | none | **Missing** |
| **Account management, password reset** | none | `users` (unused) | **Missing** |
| **Marksheet (print)** | none | none | **Missing** |
| **Audit trail** | none | none | **Missing** |
| **Migration runner** | none | none | **Missing** (loose SQL files only) |

## 4. Findings

### Critical

| # | Finding | Evidence |
|---|---------|----------|
| C1 | **No authentication or authorization.** Every route, including student delete and mark edit, is open to anyone who can reach the port. | `app.py`, `routes/*.py` have no guard. |
| C2 | **Debug server exposed to the network.** `app.run(debug=True, host='0.0.0.0')` serves the Werkzeug debugger, which allows remote code execution. | `app.py:112` |
| C3 | **`schema.sql` drops every table first.** The README tells users to run it. Re-running on a live database deletes all data, including `users`. | `database/schema.sql:10-15` |

### High

| # | Finding | Evidence |
|---|---------|----------|
| H1 | Hardcoded fallback `SECRET_KEY`. DB defaults to `root` with an empty password. | `config.py:10-12` |
| H2 | **No CSRF protection.** 15 POST forms, including all deletes. | `templates/*.html` |
| H3 | **Raw exception text is shown to users** (`flash(f'Error ...: {e}')`). It can carry SQL fragments and schema names. | `routes/*.py`, 14 sites |
| H4 | **Numeric input is unguarded.** `float(request.form[...])` raises on bad input (a 500 page). `nan` passes every `<` / `>` check. `/assessments/enter` has no range or sign check at all. | `routes/marks.py:58`, `routes/assessments.py:56` |
| H5 | **`seed.sql` creates an `admin` user** with a fabricated hash and a comment that discloses the password. The hash is not a valid scrypt hash, so it cannot log in, but it is a publicly documented credential. | `database/seed.sql:89-92` |
| H6 | **`queries.sql` has live `UPDATE`/`DELETE` statements.** Running the file as a whole changes student 1's email and mark 1. | `database/queries.sql:66-84` |
| H7 | **All student data is publicly readable.** Anyone can search `/results`, open `/students/<id>`, or query `/reports/student?registration_number=`. | `app.py:61`, `routes/students.py:53` |
| H8 | **A credential is in Git history.** The first commit has a non-placeholder `DB_PASSWORD` value in `README.md`. The latest commit replaced it with another password-like value, so a password-like value is still in the working tree. The repo has an `origin` remote, so treat both as exposed. History was **not** rewritten. Rotate the MySQL password. | `git show 5426a6c:README.md`, `c35748d` |

| H9 | **"Calculate Result" crashes on real data.** MySQL returns `Decimal`; the code added it to a `float` (`TypeError`). The original tests only used integers, so this was never seen. Found while rebuilding the calculation, not in the first read. | `services/result_service.py` (original), reproduced with `Decimal('40.00')` marks |

### Medium

| # | Finding |
|---|---------|
| M1 | **Assessment settings exist twice.** Weights and maximums are hardcoded in `calculate_student_result_with_assessments` and also stored in the `assessments` table. Editing the table does nothing to the calculation. |
| M2 | **Assessment save is not atomic.** Each component opens its own connection and commits. A failure mid-loop leaves a partial save. It also does SELECT-then-INSERT, which races. |
| M3 | **Migration `migration_add_assessments.sql` maps every legacy exam to `ENDSEM`.** If a student-subject has marks in several exams, an arbitrary one wins. It also ignores each legacy row's own `maximum_marks`. Needs your decision on which exam counts as end-semester. Not changed. |
| M4 | `seed.sql` is not re-runnable. Plain `INSERT`, and mark rows use hardcoded IDs 1-8. |
| M5 | `seed_vit_students.sql` uses the real institution email domain and real-format registration numbers for made-up people. One row has `academic_year = '2024-2024'`. README counts (33 marks, 28 subjects) do not match the scripts. |
| M6 | `db.py` prints errors, has no timeouts, and the dashboard turns any DB failure into zeros, which hides outages. |
| M7 | No pagination. Every list page loads whole tables. |
| M8 | Reports hardcode unsourced rules: "at least 5 subjects", "top performer is 85%+". They are not in the README. |
| M9 | README says DB integration tests exist and are skipped when MySQL is missing. No such tests exist. |
| M10 | Legacy-mark pass rule is "every subject at least 40%". README says "per subject and overall". Consistent with the code, kept as is. |

### Low

L1 Bootstrap loads from a CDN without SRI, so an offline demo breaks. L2 Footer says 2024. L3 `LIKE` wildcards in search are not escaped. L4 `.env.example` has no `SECRET_KEY` entry and no trailing newline. L5 No custom 403/404/500 pages. L6 `PROJECT_SUMMARY.md` and `UPGRADE_SUMMARY.md` overlap the README and have drifted.

## 5. Database and migration findings

- `users(user_id, username, password_hash, role DEFAULT 'admin')` exists and is unused. No email, no active flag, no link to a student or faculty row, no role constraint.
- **No faculty table, no class/section table, no assignment table.** The only groupings are `students.department`, `students.semester`, `subjects.semester`.
- Tables use InnoDB, foreign keys, unique keys and CHECK constraints. This part is sound. CHECK needs MySQL 8.0.16+.
- `ON DELETE CASCADE` from `students` to `marks` and `assessment_marks` means one student delete removes their whole record. Acceptable only behind admin auth and a confirmation.
- There is no migration tracking. Order is a README convention.
- `verification.sql` and `queries.sql` are checked against a live schema in the test container. Results are in the final report.

## 6. Academic rules that are established

Taken from the README, code and tests. These are used as is and not changed.

| Rule | Source |
|------|--------|
| Grades: S >= 90, A >= 80, B >= 70, C >= 60, D >= 50, E >= 40, F < 40 | README, `calculate_grade`, tests |
| Pass at 40% | README, `calculate_pass_status`, tests |
| Components: CAT1/2/3 (50 marks, 15% each), Assignment (50, 10%), Project (100, 20%), End Sem (100, 25%) | README, migration SQL, tests |
| A weighted result needs all components. Anything missing gives `Incomplete` | `calculate_student_result_with_assessments`, tests |

**Not established, so not implemented:** GPA and CGPA (no grade-point mapping exists), any "absent" or "withheld" mark status, rank rules, and any rule for how legacy `marks` and `assessment_marks` should combine.

## 7. Security findings summary

Authentication, authorization, CSRF, debug exposure, secret fallbacks, error leakage and public data exposure are all open (C1, C2, H1-H3, H7). SQL injection: every query seen uses `%s` parameters. No injection found. XSS: no `|safe`, no `innerHTML`, autoescape is on. No XSS sink found in templates or `main.js`. File uploads: none.

## 8. UI and usability

Bootstrap 5, one consistent navbar, flash messages, a delete confirm. Weak points: no login, no role-aware navigation, no pagination, no empty or loading states, no mobile check of the wide report tables, no print layout, no custom error pages.

## 9. Test coverage

9 unit tests on pure calculation code. Nothing covers routes, SQL, templates, config, migrations or any security property.

## 10. Rectification plan

| Order | Work | Closes |
|-------|------|--------|
| 1 | Test harness: pytest + throwaway MySQL 8.4 container. Isolated test DB, guarded against the real one. | M9 |
| 2 | Config: required `SECRET_KEY`, safe debug default, bind to localhost. App factory so tests can build an app. | C2, H1 |
| 3 | Non-destructive SQL: remove `DROP` from `schema.sql`, remove the fake admin, neutralise `queries.sql`, make seeds re-runnable. | C3, H5, H6, M4, M5 |
| 4 | Migration runner + migrations: auth columns, faculty, assignments, audit log. Tracked, ordered, additive only. | gap |
| 5 | Auth: login, logout, hashing, session rules, rate limit, CSRF, first-admin CLI. | C1, H2 |
| 6 | Authorization layer and role scoping on every route. | C1, H7 |
| 7 | Input validation helper, atomic mark save, safe error pages. | H3, H4, M2, M6 |
| 8 | Read assessment config from the DB, not code. | M1 |
| 9 | Admin screens: users, faculty, assignments, assessment config, audit log. | gap |
| 10 | Faculty and student dashboards, result views, print marksheet, pagination. | gap, M7 |
| 11 | Docs and final report. | L2, L4, L6 |

## 11. Decisions that belong to you

1. **Rotate the MySQL password** that appeared in Git history (H8). Decide whether to rewrite history. Not done without your approval.
2. **ENDSEM mapping** in the old migration (M3): which exam counts as end-semester?
3. **Faculty scope.** The schema has no classes or sections. Working assumption, marked as my call: a faculty assignment is (faculty, subject, academic year), and the students in scope are those whose semester equals the subject's semester. It lives in one function, so it is cheap to change.
4. **Report thresholds** (M8): keep "5 subjects" and "85%" or define them.
5. **GPA/CGPA**: supply the grade-point mapping if you want it.


## 12. Resolution status

Written after the work. "Fixed" means a test fails without the change and passes with it. Nothing was applied to your real
database (it is not reachable from this machine); the migrations and the backup command are ready for you to run.

| Finding | Status | How |
|---------|--------|-----|
| C1 no authentication | Fixed | Login, default-deny on every route, role registry, 400+ tests incl. a walk over every registered route |
| C2 debug server on all interfaces | Fixed | Debug off by default, binds `127.0.0.1`, `APP_HOST` and `FLASK_DEBUG` are explicit opt-ins |
| C3 `schema.sql` drops tables | Fixed | Rewritten to `CREATE ... IF NOT EXISTS`; a test applies it twice over live rows; a test forbids `DROP`/`TRUNCATE`/`DELETE FROM` in every shipped script |
| H1 default secrets | Fixed | `SECRET_KEY` and `DB_PASSWORD` are required; weak or placeholder keys are rejected |
| H2 no CSRF | Fixed | Token on all 20 forms, checked on every state-changing request; a lint test fails if a form lacks one |
| H3 raw errors shown | Fixed | Friendly messages only; DB errors are logged without parameters; a test injects an error carrying a schema name |
| H4 unguarded numbers | Fixed | One validation module; `nan`, `inf`, exponents, separators rejected; ranges checked in one place |
| H5 fake admin in seed | Fixed | Removed. No seed file creates accounts; a test enforces it |
| H6 `queries.sql` changes data | Fixed | Write examples commented out; a test runs the file and compares the data before and after |
| H7 public data | Fixed | Sign-in required; students see only their own rows; faculty only their cohort |
| H8 credential in Git history | **Open: your action** | Rotate the MySQL password. History was not rewritten (needs your approval). The README no longer contains a password |
| H9 Decimal crash | Fixed | Exact `Decimal` arithmetic, one rounding rule, regression tests with DB-style values |
| M1 duplicated weights | Fixed | Calculation reads the `assessments` table; admin screen edits it (weights must total 100) |
| M2 non-atomic save | Fixed | One transaction per save, upsert, all-or-nothing, audited in the same transaction |
| M3 ENDSEM mapping | **Open: needs your decision** | Documented in README and design doc; not changed |
| M4 / M5 seeds | Fixed | Re-runnable; synthetic; reserved `.example` domain; `2024-2024` typo corrected |
| M6 swallowed DB errors | Fixed | Outage shows a clear 503 page; a test takes the database away mid-session |
| M7 pagination | Fixed | All long lists (students, subjects, marks, results, accounts, faculty, audit) |
| M8 report thresholds | Documented | Kept (5 subjects, 85%); the pages say they are assumptions. Your call |
| M9 missing tests | Fixed | Pytest suite; database tests use a throwaway server and refuse non-test databases |
| M10 legacy pass rule | Kept | Matches the code and tests |
| L1 CDN integrity | Fixed | Subresource Integrity hashes on both Bootstrap files |
| L2-L6 | Fixed | Footer, `.env.example`, README, error pages, historical notices on the old summaries |
