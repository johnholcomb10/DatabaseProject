-- Five test queries for the University Records database.
-- Run all of them with:   python run_queries.py
-- or with the SQLite CLI: sqlite3 -header -column project.db < test_queries.sql
-- Each query starts with a "-- Q<n>:" line; run_queries.py uses it as the title.

-- Q1: Class roster for CSC 1350, Fall 2026 (all sections)
SELECT o.Section, s.StudentID, s.LastName, s.FirstName, s.Rank, d.DeptName AS Major
FROM Enrollment e
JOIN Offering o   ON o.OfferingID = e.OfferingID
JOIN Student s    ON s.StudentID = e.StudentID
JOIN Department d ON d.DeptID = s.MajorDeptID
WHERE o.CourseNumber = 'CSC 1350' AND o.Term = 'Fall' AND o.Year = 2026
ORDER BY o.Section, s.LastName, s.FirstName;

-- Q2: Instructor teaching load in Fall 2026 (sections and students taught)
SELECT i.InstructorID, i.FirstName || ' ' || i.LastName AS Instructor, i.DeptID,
       COUNT(DISTINCT o.OfferingID) AS Sections, COUNT(e.StudentID) AS Students
FROM Instructor i
JOIN Offering o        ON o.InstructorID = i.InstructorID
LEFT JOIN Enrollment e ON e.OfferingID = o.OfferingID
WHERE o.Term = 'Fall' AND o.Year = 2026
GROUP BY i.InstructorID
ORDER BY Students DESC
LIMIT 10;

-- Q3: Average GPA by major department and class rank
SELECT d.DeptName AS Major, s.Rank, COUNT(*) AS Students, ROUND(AVG(s.GPA), 2) AS AvgGPA
FROM Student s
JOIN Department d ON d.DeptID = s.MajorDeptID
WHERE s.GPA IS NOT NULL
GROUP BY d.DeptName, s.Rank
ORDER BY d.DeptName,
         CASE s.Rank WHEN 'Freshman' THEN 1 WHEN 'Sophomore' THEN 2
                     WHEN 'Junior' THEN 3 ELSE 4 END;

-- Q4: Enrollments where the student had not passed a prerequisite beforehand
SELECT s.StudentID, s.LastName, o.CourseNumber, o.Term || ' ' || o.Year AS TermTaken,
       p.PrereqNumber AS MissingPrereq
FROM Enrollment e
JOIN Student s      ON s.StudentID = e.StudentID
JOIN Offering o     ON o.OfferingID = e.OfferingID
JOIN Prerequisite p ON p.CourseNumber = o.CourseNumber
WHERE NOT EXISTS (
    SELECT 1
    FROM Enrollment e2
    JOIN Offering o2 ON o2.OfferingID = e2.OfferingID
    WHERE e2.StudentID = e.StudentID
      AND o2.CourseNumber = p.PrereqNumber
      AND e2.Grade IN ('A', 'B', 'C', 'D')
      AND (o2.Year * 10 + CASE o2.Term WHEN 'Spring' THEN 1 WHEN 'Summer' THEN 2 ELSE 3 END)
        < (o.Year  * 10 + CASE o.Term  WHEN 'Spring' THEN 1 WHEN 'Summer' THEN 2 ELSE 3 END))
ORDER BY o.Year, o.Term, s.StudentID;

-- Q5: Five most popular courses across all terms, with pass rate on graded enrollments
SELECT c.CourseNumber, c.CourseName,
       COUNT(e.StudentID) AS TotalEnrolled,
       ROUND(100.0 * SUM(e.Grade IN ('A', 'B', 'C', 'D'))
             / NULLIF(SUM(e.Grade IS NOT NULL AND e.Grade <> 'W'), 0), 1) AS PassRatePct
FROM Course c
JOIN Offering o   ON o.CourseNumber = c.CourseNumber
JOIN Enrollment e ON e.OfferingID = o.OfferingID
GROUP BY c.CourseNumber
ORDER BY TotalEnrolled DESC
LIMIT 5;
