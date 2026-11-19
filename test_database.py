"""Automated tests for the University Records database.

Usage:
    python test_database.py        (or: python -m unittest -v test_database)

Each test builds a fresh database in a temporary folder with generate_data.py,
so project.db is never modified.
"""

import os
import shutil
import sqlite3
import tempfile
import unittest

import generate_data
import run_queries


class DatabaseTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.db = os.path.join(cls.tmp, "test.db")
        generate_data.build(cls.db, seed=4402)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self.conn = sqlite3.connect(self.db)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("BEGIN")  # every test is rolled back

    def tearDown(self):
        self.conn.rollback()
        self.conn.close()

    def count(self, table):
        return self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


class TestData(DatabaseTestCase):
    def test_every_table_has_data(self):
        for table in ["Department", "Instructor", "Student", "Course",
                      "Prerequisite", "Offering", "Enrollment"]:
            with self.subTest(table=table):
                self.assertGreater(self.count(table), 0)

    def test_no_foreign_key_violations(self):
        self.assertEqual(self.conn.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_fourteen_day_enrollment_within_capacity(self):
        bad = self.conn.execute(
            "SELECT COUNT(*) FROM Offering WHERE FourteenDayEnrollment > Capacity").fetchone()[0]
        self.assertEqual(bad, 0)

    def test_current_term_has_no_grades(self):
        graded = self.conn.execute("""
            SELECT COUNT(*) FROM Enrollment e JOIN Offering o ON o.OfferingID = e.OfferingID
            WHERE o.Term = 'Fall' AND o.Year = 2026 AND e.Grade IS NOT NULL""").fetchone()[0]
        self.assertEqual(graded, 0)


class TestConstraints(DatabaseTestCase):
    def assertRejected(self, sql, params=()):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(sql, params)

    def test_gpa_must_be_between_0_and_4(self):
        self.assertRejected("INSERT INTO Student VALUES (1,'A','B','2005-01-01','Senior',4.5,'CSC')")

    def test_rank_must_be_valid(self):
        self.assertRejected("INSERT INTO Student VALUES (1,'A','B','2005-01-01','Grad',3.0,'CSC')")

    def test_student_major_must_exist(self):
        self.assertRejected("INSERT INTO Student VALUES (1,'A','B','2005-01-01','Senior',3.0,'XYZ')")

    def test_duplicate_enrollment_rejected(self):
        sid, oid = self.conn.execute("SELECT StudentID, OfferingID FROM Enrollment LIMIT 1").fetchone()
        self.assertRejected("INSERT INTO Enrollment VALUES (?,?,NULL)", (sid, oid))

    def test_invalid_grade_rejected(self):
        sid, oid = self.conn.execute("SELECT StudentID, OfferingID FROM Enrollment LIMIT 1").fetchone()
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE Enrollment SET Grade='E' WHERE StudentID=? AND OfferingID=?",
                              (sid, oid))

    def test_duplicate_section_rejected(self):
        row = self.conn.execute(
            "SELECT CourseNumber, Term, Year, Section FROM Offering LIMIT 1").fetchone()
        self.assertRejected(
            "INSERT INTO Offering (CourseNumber, Term, Year, Section, Capacity) VALUES (?,?,?,?,30)", row)

    def test_course_cannot_require_itself(self):
        self.assertRejected("INSERT INTO Prerequisite VALUES ('CSC 4402','CSC 4402')")

    def test_course_with_offerings_cannot_be_deleted(self):
        self.assertRejected("DELETE FROM Course WHERE CourseNumber = 'CSC 1350'")

    def test_deleting_student_cascades_to_enrollment(self):
        sid = self.conn.execute("SELECT StudentID FROM Enrollment LIMIT 1").fetchone()[0]
        self.conn.execute("DELETE FROM Student WHERE StudentID = ?", (sid,))
        left = self.conn.execute("SELECT COUNT(*) FROM Enrollment WHERE StudentID = ?", (sid,)).fetchone()[0]
        self.assertEqual(left, 0)

    def test_deleting_instructor_leaves_sections_tba(self):
        iid = self.conn.execute("SELECT InstructorID FROM Offering LIMIT 1").fetchone()[0]
        n = self.conn.execute("SELECT COUNT(*) FROM Offering WHERE InstructorID = ?", (iid,)).fetchone()[0]
        self.conn.execute("DELETE FROM Instructor WHERE InstructorID = ?", (iid,))
        self.assertEqual(self.count("Offering WHERE InstructorID IS NULL"), n)


class TestQueries(DatabaseTestCase):
    def test_five_queries_run_and_return_rows(self):
        results = list(run_queries.run_all(self.conn))
        self.assertEqual(len(results), 5)
        for title, headers, rows in results:
            with self.subTest(query=title):
                self.assertTrue(headers)
                self.assertGreater(len(rows), 0)

    def test_q5_returns_top_five(self):
        rows = list(run_queries.run_all(self.conn))[4][2]
        self.assertEqual(len(rows), 5)
        totals = [r[2] for r in rows]
        self.assertEqual(totals, sorted(totals, reverse=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
