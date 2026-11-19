"""Build project.db from schema.sql and fill it with synthetic data.

Usage:
    python generate_data.py                 # writes project.db
    python generate_data.py --db other.db --seed 7

The output is deterministic for a given seed. Only the Python standard
library is used.
"""

import argparse
import os
import random
import sqlite3
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))

# Terms covered by the data, oldest first. The last one is the current term
# (grades not yet assigned).
TERMS = [(t, y) for y in range(2022, 2027) for t in ("Spring", "Fall")][1:]  # Fall 2022 .. Fall 2026
CURRENT = len(TERMS) - 1

DEPARTMENTS = [
    ("CSC", "Computer Science", "Patrick F. Taylor Hall", "225-578-1495"),
    ("MATH", "Mathematics", "Lockett Hall", "225-578-1665"),
    ("PHYS", "Physics and Astronomy", "Nicholson Hall", "225-578-2261"),
    ("CHEM", "Chemistry", "Choppin Hall", "225-578-3361"),
    ("BIOL", "Biological Sciences", "Life Sciences Building", "225-578-2601"),
    ("ENGL", "English", "Allen Hall", "225-578-4086"),
    ("HIST", "History", "Himes Hall", "225-578-4471"),
    ("ECON", "Economics", "Business Education Complex", "225-578-5211"),
    ("ME", "Mechanical Engineering", "Patrick F. Taylor Hall", "225-578-5792"),
    ("EE", "Electrical Engineering", "Electrical Engineering Building", "225-578-5241"),
]

# (number, name, credit hours, lab course, required for majors)
COURSES = {
    "CSC": [(1350, "Computer Science I", 4, 1, 1), (1351, "Computer Science II", 4, 1, 1),
            (2259, "Discrete Structures", 3, 0, 1), (3102, "Advanced Data Structures", 3, 0, 1),
            (3380, "Operating Systems", 3, 0, 0), (4402, "Introduction to Database Management Systems", 3, 0, 0)],
    "MATH": [(1550, "Calculus I", 5, 0, 1), (1552, "Calculus II", 4, 0, 1),
             (2057, "Multidimensional Calculus", 3, 0, 1), (2090, "Differential Equations", 3, 0, 0),
             (3355, "Probability", 3, 0, 0), (4031, "Advanced Calculus", 3, 0, 0)],
    "PHYS": [(2001, "General Physics I", 3, 0, 1), (2108, "Physics Lab I", 1, 1, 1),
             (2110, "Physics for Engineers", 3, 0, 0), (3041, "Mechanics", 3, 0, 1),
             (3098, "Modern Physics", 3, 0, 0), (4141, "Quantum Mechanics", 3, 0, 0)],
    "CHEM": [(1201, "General Chemistry I", 3, 0, 1), (1212, "General Chemistry Lab", 2, 1, 1),
             (2261, "Organic Chemistry I", 3, 0, 1), (2262, "Organic Chemistry II", 3, 0, 0),
             (3492, "Physical Chemistry", 3, 0, 0), (4553, "Biochemistry", 3, 0, 0)],
    "BIOL": [(1201, "Biology for Science Majors I", 3, 0, 1), (1208, "Biology Lab I", 1, 1, 1),
             (2051, "General Microbiology", 4, 1, 1), (2160, "Human Anatomy", 3, 0, 0),
             (3090, "Cell Biology", 3, 0, 0), (4087, "Genetics", 3, 0, 0)],
    "ENGL": [(1001, "English Composition", 3, 0, 1), (2000, "Writing and Research", 3, 0, 1),
             (2027, "American Literature", 3, 0, 0), (2148, "Shakespeare", 3, 0, 0),
             (3001, "Technical Writing", 3, 0, 1), (4011, "Literary Theory", 3, 0, 0)],
    "HIST": [(1001, "Western Civilization I", 3, 0, 1), (2055, "American History to 1865", 3, 0, 1),
             (2057, "American History since 1865", 3, 0, 0), (3020, "History of Louisiana", 3, 0, 0),
             (3093, "Modern Europe", 3, 0, 0), (4001, "Historiography", 3, 0, 1)],
    "ECON": [(2000, "Principles of Microeconomics", 3, 0, 1), (2010, "Principles of Macroeconomics", 3, 0, 1),
             (2035, "Economic Statistics", 3, 0, 1), (3030, "Intermediate Microeconomics", 3, 0, 0),
             (3040, "Money and Banking", 3, 0, 0), (4520, "Econometrics", 3, 0, 0)],
    "ME": [(2183, "Engineering Graphics", 2, 1, 1), (2221, "Statics", 3, 0, 1),
           (2534, "Dynamics", 3, 0, 1), (3333, "Thermodynamics", 3, 0, 0),
           (3834, "Fluid Mechanics", 3, 0, 0), (4243, "Machine Design", 3, 0, 0)],
    "EE": [(2120, "Electric Circuits", 3, 0, 1), (2130, "Circuits Lab", 1, 1, 1),
           (2720, "Digital Logic", 3, 0, 1), (3220, "Signals and Systems", 3, 0, 0),
           (3755, "Electronics", 3, 0, 0), (4440, "Embedded Systems", 4, 1, 0)],
}

# Within each department: course index -> indexes of its prerequisites.
PREREQ_PATTERN = {1: [0], 2: [0], 3: [1], 4: [1], 5: [3]}
CROSS_PREREQS = [
    ("PHYS 2001", "MATH 1550"), ("ME 2221", "MATH 1552"), ("EE 2120", "MATH 1552"),
    ("CHEM 3492", "MATH 1552"), ("ECON 2035", "MATH 1550"), ("CSC 4402", "CSC 2259"),
]

FIRST = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "David",
         "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah",
         "Chris", "Karen", "Daniel", "Lisa", "Matthew", "Nancy", "Anthony", "Ashley", "Mark", "Emily",
         "Andrew", "Olivia", "Joshua", "Sophia", "Kevin", "Ava", "Brian", "Mia", "Tyler", "Chloe",
         "Jordan", "Grace", "Ethan", "Zoe", "Noah", "Hannah", "Lucas", "Maya", "Caleb", "Aaliyah"]
LAST = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez",
        "Martinez", "Hernandez", "Lopez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson",
        "Martin", "Lee", "Thompson", "White", "Harris", "Clark", "Lewis", "Robinson", "Walker", "Young",
        "Allen", "King", "Wright", "Scott", "Nguyen", "Hill", "Green", "Adams", "Baker", "Hall",
        "Rivera", "Campbell", "Mitchell", "Carter", "Roberts", "Landry", "Thibodeaux", "Broussard"]

TITLES = ["Instructor", "Assistant Professor", "Associate Professor", "Professor"]
RANKS = ["Freshman", "Sophomore", "Junior", "Senior"]
# First term index each rank starts taking classes in this data window.
RANK_START = {"Senior": [0, 1, 2], "Junior": [2, 3, 4], "Sophomore": [4, 5, 6], "Freshman": [6, 7, 8]}
GRADES, GRADE_WEIGHTS = ["A", "B", "C", "D", "F", "W"], [30, 33, 21, 7, 5, 4]
POINTS = {"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "F": 0.0}
PASSING = {"A", "B", "C", "D"}

N_INSTRUCTORS_PER_DEPT = 4
N_STUDENTS = 300
PREREQ_OVERRIDE_RATE = 0.01   # chance per student-term of one advisor override of a prerequisite
# Courses scheduled every term regardless of level
ALWAYS_OFFERED = {"CSC 4402"}


def build(db_path, seed):
    rng = random.Random(seed)
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    with open(os.path.join(HERE, "schema.sql"), encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    # Departments
    cur.executemany("INSERT INTO Department VALUES (?,?,?,?)", DEPARTMENTS)
    dept_ids = [d[0] for d in DEPARTMENTS]

    # Instructors
    used_emails, instructors_by_dept = set(), {d: [] for d in dept_ids}
    iid = 1000
    for d in dept_ids:
        for _ in range(N_INSTRUCTORS_PER_DEPT):
            iid += 1
            fn, ln = rng.choice(FIRST), rng.choice(LAST)
            email, n = f"{fn}.{ln}@univ.edu".lower(), 1
            while email in used_emails:
                n += 1
                email = f"{fn}.{ln}{n}@univ.edu".lower()
            used_emails.add(email)
            cur.execute("INSERT INTO Instructor VALUES (?,?,?,?,?,?)",
                        (iid, fn, ln, email, rng.choice(TITLES), d))
            instructors_by_dept[d].append(iid)

    # Courses and prerequisites
    course_info = {}  # number -> (dept, credits, level)
    lab_courses = set()
    for d, rows in COURSES.items():
        for num, name, cr, lab, req in rows:
            cn = f"{d} {num}"
            desc = f"{name}. Offered by the Department of {dict((x[0], x[1]) for x in DEPARTMENTS)[d]}."
            cur.execute("INSERT INTO Course VALUES (?,?,?,?,?,?,?)", (cn, name, desc, req, cr, lab, d))
            course_info[cn] = (d, cr, num // 1000)
            if lab:
                lab_courses.add(cn)
    prereqs = {cn: set() for cn in course_info}
    for d, rows in COURSES.items():
        for i, reqs in PREREQ_PATTERN.items():
            for j in reqs:
                prereqs[f"{d} {rows[i][0]}"].add(f"{d} {rows[j][0]}")
    for c, p in CROSS_PREREQS:
        prereqs[c].add(p)
    cur.executemany("INSERT INTO Prerequisite VALUES (?,?)",
                    [(c, p) for c, ps in prereqs.items() for p in sorted(ps)])

    # Offerings: intro (1000/2000-level) courses run every term with 1-2 sections,
    # upper-level courses run in about 60% of terms.
    offerings = {}  # term index -> list of [offering_id, course, capacity, enrolled]
    for t, (term, year) in enumerate(TERMS):
        offerings[t] = []
        for cn, (d, cr, level) in course_info.items():
            if level <= 2 or cn in ALWAYS_OFFERED:
                sections = rng.choice([1, 2, 2])
            else:
                sections = 1 if rng.random() < 0.6 else 0
            for s in range(1, sections + 1):
                cap = 24 if cn in lab_courses else rng.choice([30, 35, 40, 45])
                cur.execute(
                    "INSERT INTO Offering (CourseNumber, Term, Year, Section, InstructorID, Capacity)"
                    " VALUES (?,?,?,?,?,?)",
                    (cn, term, year, s, rng.choice(instructors_by_dept[d]), cap))
                offerings[t].append([cur.lastrowid, cn, cap, 0])

    # Students and enrollments
    rank_weights = [25, 25, 25, 25]
    for sid in range(890000001, 890000001 + N_STUDENTS):
        rank = rng.choices(RANKS, rank_weights)[0]
        major = rng.choice(dept_ids)
        birth_year = 2008 - RANKS.index(rank)
        dob = date(birth_year, 1, 1) + timedelta(days=rng.randrange(365))
        cur.execute("INSERT INTO Student VALUES (?,?,?,?,?,?,?)",
                    (sid, rng.choice(FIRST), rng.choice(LAST), dob.isoformat(), rank, None, major))

        passed, taken = set(), set()
        quality, graded_credits = 0.0, 0
        for t in range(rng.choice(RANK_START[rank]), len(TERMS)):
            pool = [o for o in offerings[t] if o[3] < o[2] and o[1] not in taken]
            rng.shuffle(pool)
            # Prefer major courses, then lower-level courses
            pool.sort(key=lambda o: (course_info[o[1]][0] != major, course_info[o[1]][2]))
            chosen, credits, courses_this_term = [], 0, set()
            override = rng.random() < PREREQ_OVERRIDE_RATE
            for o in pool:
                cn = o[1]
                if cn in courses_this_term:
                    continue
                if not prereqs[cn] <= passed:
                    if not override:
                        continue
                    override = False  # one override per term
                if credits + course_info[cn][1] > 16:
                    continue
                chosen.append(o)
                courses_this_term.add(cn)
                credits += course_info[cn][1]
                if credits >= 12 and rng.random() < 0.5:
                    break
            for o in chosen:
                cn = o[1]
                grade = None if t == CURRENT else rng.choices(GRADES, GRADE_WEIGHTS)[0]
                cur.execute("INSERT INTO Enrollment VALUES (?,?,?)", (sid, o[0], grade))
                o[3] += 1
                if grade in PASSING:
                    passed.add(cn)
                    taken.add(cn)
                if grade in POINTS:
                    quality += POINTS[grade] * course_info[cn][1]
                    graded_credits += course_info[cn][1]
        if graded_credits:
            cur.execute("UPDATE Student SET GPA = ? WHERE StudentID = ?",
                        (round(quality / graded_credits, 2), sid))

    # 14-day enrollment = head count recorded for each section
    cur.execute("""UPDATE Offering SET FourteenDayEnrollment =
                   (SELECT COUNT(*) FROM Enrollment e WHERE e.OfferingID = Offering.OfferingID)""")
    conn.commit()

    counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ["Department", "Instructor", "Student", "Course",
                        "Prerequisite", "Offering", "Enrollment"]}
    conn.close()
    return counts


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=os.path.join(HERE, "project.db"), help="output database file")
    ap.add_argument("--seed", type=int, default=4402, help="random seed")
    args = ap.parse_args()
    counts = build(args.db, args.seed)
    print(f"Built {args.db}")
    for table, n in counts.items():
        print(f"  {table:<13}{n:>6} rows")


if __name__ == "__main__":
    main()
