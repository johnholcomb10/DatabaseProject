# University Records Database

Final project for CSC 4402 (Introduction to Database Management Systems) at LSU.

A SQLite database for a university's academic records office: departments, instructors,
students, catalog courses and prerequisites, the sections offered each term, and student
enrollments with grades. It comes with a Python/Tkinter interface for adding, updating and
deleting data, five test queries, and an automated test suite.

## Requirements

- Python 3.9 or newer (tested on 3.13). Only the standard library is used (`sqlite3`, `tkinter`).
  - Windows / macOS: the python.org installer includes Tkinter.
  - Linux: install it separately if needed, for example `sudo apt install python3-tk`.
- Optional: the `sqlite3` command-line shell, to run the SQL files directly.

On Windows, use `py` in place of `python` if `python` is not on your PATH.

## Files

| File | Purpose |
| --- | --- |
| `schema.sql` | Table definitions with primary keys, foreign keys, CHECK and UNIQUE constraints |
| `generate_data.py` | Rebuilds `project.db` from `schema.sql` and fills it with synthetic data (deterministic seed) |
| `project.db` | The populated SQLite database |
| `test_queries.sql` | The five test queries |
| `run_queries.py` | Runs the five test queries and prints the results as tables |
| `test_database.py` | Automated tests: data checks, constraint checks, and the five queries |
| `project.py` | Tkinter application with the five user interfaces |

## Quick start

```bash
# 1. (Optional) rebuild the database. project.db is already included.
python generate_data.py

# 2. Run the five test queries
python run_queries.py              # first 20 rows of each result
python run_queries.py --max-rows 0 # all rows

# 3. Run the automated tests (uses a temporary copy, never touches project.db)
python test_database.py

# 4. Start the application
python project.py
```

With the SQLite shell you can also run:

```bash
sqlite3 -header -column project.db < test_queries.sql
```

## Database

| Table | Rows | Description |
| --- | ---: | --- |
| Department | 10 | Academic departments |
| Instructor | 40 | Faculty, each in one department |
| Student | 300 | Students with rank, GPA and major department |
| Course | 60 | Catalog courses, six per department |
| Prerequisite | 56 | Course-to-course prerequisite pairs |
| Offering | 650 | Sections of a course in a term (Fall 2022 to Fall 2026) |
| Enrollment | 6,990 | Student-in-section records with grade (NULL for the current term, Fall 2026) |

Row counts are for the default seed (`--seed 4402`). The data is synthetic. GPA is calculated
from each student's graded enrollments, weighted by credit hours. About 1% of student-terms
include an advisor override of a prerequisite, which test query 4 finds.

Foreign keys are enforced (`PRAGMA foreign_keys = ON`):

- Deleting a student deletes their enrollments.
- Deleting an instructor leaves their sections with no instructor (TBA).
- Deleting a course or department that is still in use is blocked.

## Test queries

| # | Query |
| --- | --- |
| Q1 | Class roster for CSC 1350, Fall 2026 |
| Q2 | Top 10 instructors by students taught in Fall 2026 |
| Q3 | Average GPA by major department and class rank |
| Q4 | Enrollments where the student had not passed a prerequisite in an earlier term |
| Q5 | Five most popular courses across all terms, with pass rate |

## Application (`project.py`)

The window has one tab per user task. Every tab has a search box and Add, Edit and Delete
buttons. Double-click a row to edit it. Foreign keys are chosen from dropdowns, and database
errors (for example, a GPA above 4.0 or a duplicate enrollment) are shown in a message box.

| Tab | Typical user | What you can do |
| --- | --- | --- |
| Students | Advisor | Add, edit and delete students; change rank, GPA, major |
| Instructors | Department chair | Add, edit and delete instructors |
| Courses | Registrar | Add, edit and delete courses and choose their prerequisites |
| Offerings | Registrar / chair | Schedule sections, assign or change the instructor, set capacity |
| Enrollment | Advisor | Enroll a student in a section, drop them, enter or change a grade |

**Run Test Queries** (top left) opens the five test queries, one result per tab.
