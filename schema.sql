-- University Records Database schema (SQLite)
-- Run via generate_data.py, or: sqlite3 project.db < schema.sql

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS Enrollment;
DROP TABLE IF EXISTS Offering;
DROP TABLE IF EXISTS Prerequisite;
DROP TABLE IF EXISTS Course;
DROP TABLE IF EXISTS Student;
DROP TABLE IF EXISTS Instructor;
DROP TABLE IF EXISTS Department;

CREATE TABLE Department (
    DeptID      TEXT PRIMARY KEY,               -- e.g. 'CSC'
    DeptName    TEXT NOT NULL UNIQUE,
    Building    TEXT NOT NULL,
    Phone       TEXT
);

CREATE TABLE Instructor (
    InstructorID INTEGER PRIMARY KEY,
    FirstName    TEXT NOT NULL,
    LastName     TEXT NOT NULL,
    Email        TEXT NOT NULL UNIQUE,
    Title        TEXT NOT NULL
                 CHECK (Title IN ('Instructor', 'Assistant Professor',
                                  'Associate Professor', 'Professor')),
    DeptID       TEXT NOT NULL REFERENCES Department(DeptID)
                 ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE Student (
    StudentID   INTEGER PRIMARY KEY,
    FirstName   TEXT NOT NULL,
    LastName    TEXT NOT NULL,
    DOB         TEXT NOT NULL,                  -- ISO date YYYY-MM-DD
    Rank        TEXT NOT NULL
                CHECK (Rank IN ('Freshman', 'Sophomore', 'Junior', 'Senior')),
    GPA         REAL CHECK (GPA IS NULL OR GPA BETWEEN 0.0 AND 4.0),
    MajorDeptID TEXT NOT NULL REFERENCES Department(DeptID)
                ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE Course (
    CourseNumber       TEXT PRIMARY KEY,        -- e.g. 'CSC 4402'
    CourseName         TEXT NOT NULL,
    CatalogDescription TEXT,
    Required           INTEGER NOT NULL DEFAULT 0 CHECK (Required IN (0, 1)),
    CreditHours        INTEGER NOT NULL CHECK (CreditHours BETWEEN 1 AND 6),
    LabCourse          INTEGER NOT NULL DEFAULT 0 CHECK (LabCourse IN (0, 1)),
    DeptID             TEXT NOT NULL REFERENCES Department(DeptID)
                       ON UPDATE CASCADE ON DELETE RESTRICT
);

-- Recursive M:N relationship: CourseNumber requires PrereqNumber
CREATE TABLE Prerequisite (
    CourseNumber TEXT NOT NULL REFERENCES Course(CourseNumber)
                 ON UPDATE CASCADE ON DELETE CASCADE,
    PrereqNumber TEXT NOT NULL REFERENCES Course(CourseNumber)
                 ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (CourseNumber, PrereqNumber),
    CHECK (CourseNumber <> PrereqNumber)
);

-- One section of one course in one term
CREATE TABLE Offering (
    OfferingID            INTEGER PRIMARY KEY AUTOINCREMENT,
    CourseNumber          TEXT NOT NULL REFERENCES Course(CourseNumber)
                          ON UPDATE CASCADE ON DELETE RESTRICT,
    Term                  TEXT NOT NULL CHECK (Term IN ('Spring', 'Summer', 'Fall')),
    Year                  INTEGER NOT NULL CHECK (Year BETWEEN 2000 AND 2100),
    Section               INTEGER NOT NULL CHECK (Section >= 1),
    InstructorID          INTEGER REFERENCES Instructor(InstructorID)
                          ON DELETE SET NULL,   -- NULL = instructor TBA
    Capacity              INTEGER NOT NULL CHECK (Capacity > 0),
    FourteenDayEnrollment INTEGER CHECK (FourteenDayEnrollment >= 0),
    UNIQUE (CourseNumber, Term, Year, Section)
);

-- M:N relationship between Student and Offering, with attribute Grade
CREATE TABLE Enrollment (
    StudentID  INTEGER NOT NULL REFERENCES Student(StudentID)
               ON DELETE CASCADE,
    OfferingID INTEGER NOT NULL REFERENCES Offering(OfferingID)
               ON DELETE CASCADE,
    Grade      TEXT CHECK (Grade IS NULL OR Grade IN ('A', 'B', 'C', 'D', 'F', 'W')),
    PRIMARY KEY (StudentID, OfferingID)
);

CREATE INDEX idx_offering_course     ON Offering(CourseNumber);
CREATE INDEX idx_offering_instructor ON Offering(InstructorID);
CREATE INDEX idx_enrollment_offering ON Enrollment(OfferingID);
