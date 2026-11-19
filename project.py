"""University Records Database - Tkinter application.

Usage:
    python generate_data.py   # first time only: builds project.db
    python project.py

Five tabs, one per user task:
    Students     (advisor)            add / edit / delete students
    Instructors  (department chair)   add / edit / delete instructors
    Courses      (registrar)          add / edit / delete catalog courses and prerequisites
    Offerings    (registrar / chair)  schedule sections, assign instructors
    Enrollment   (advisor / student)  enroll, drop, and enter grades
The "Run Test Queries" button shows the five queries from test_queries.sql.
"""

import os
import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

import run_queries

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "project.db")

RANKS = ["Freshman", "Sophomore", "Junior", "Senior"]
TITLES = ["Instructor", "Assistant Professor", "Associate Professor", "Professor"]
TERMS = ["Spring", "Summer", "Fall"]
GRADES = ["", "A", "B", "C", "D", "F", "W"]
SEP = " - "  # separates the key from its label in dropdowns


# ----------------------------------------------------------------------------
# Field definitions
# ----------------------------------------------------------------------------

class Field:
    """One column shown in a tab and edited in its dialog.

    kind: 'text' | 'int' | 'real' | 'choice' | 'fk'
    fk:   SQL returning (key, label) rows for a foreign-key dropdown
    auto: primary key assigned by the database (hidden when adding)
    """

    def __init__(self, name, kind="text", label=None, choices=None, fk=None,
                 required=True, auto=False, width=110):
        self.name, self.kind, self.label = name, kind, label or name
        self.choices, self.fk, self.required, self.auto, self.width = choices, fk, required, auto, width


DEPT_FK = "SELECT DeptID, DeptName FROM Department ORDER BY DeptID"
COURSE_FK = "SELECT CourseNumber, CourseName FROM Course ORDER BY CourseNumber"
INSTRUCTOR_FK = ("SELECT InstructorID, LastName || ', ' || FirstName || ' (' || DeptID || ')' "
                 "FROM Instructor ORDER BY LastName, FirstName")
STUDENT_FK = ("SELECT StudentID, LastName || ', ' || FirstName FROM Student "
              "ORDER BY LastName, FirstName")
OFFERING_FK = ("SELECT OfferingID, CourseNumber || ' ' || Term || ' ' || Year || ' sec ' || Section "
               "FROM Offering ORDER BY Year DESC, Term, CourseNumber, Section")

# Each tab: table, primary key, editable fields, the SELECT that fills the grid
# (field columns first, in order, then any read-only display columns).
TABS = [
    dict(title="Students", table="Student", pk=["StudentID"],
         fields=[Field("StudentID", "int"), Field("FirstName"), Field("LastName"),
                 Field("DOB", label="DOB (YYYY-MM-DD)"), Field("Rank", "choice", choices=RANKS),
                 Field("GPA", "real", required=False, width=60),
                 Field("MajorDeptID", "fk", label="Major", fk=DEPT_FK)],
         select="SELECT StudentID, FirstName, LastName, DOB, Rank, GPA, MajorDeptID FROM Student "
                "ORDER BY LastName, FirstName"),
    dict(title="Instructors", table="Instructor", pk=["InstructorID"],
         fields=[Field("InstructorID", "int"), Field("FirstName"), Field("LastName"),
                 Field("Email", width=200), Field("Title", "choice", choices=TITLES, width=140),
                 Field("DeptID", "fk", label="Department", fk=DEPT_FK)],
         select="SELECT InstructorID, FirstName, LastName, Email, Title, DeptID FROM Instructor "
                "ORDER BY LastName, FirstName"),
    dict(title="Courses", table="Course", pk=["CourseNumber"], prereqs=True,
         fields=[Field("CourseNumber", label="Course number (e.g. CSC 4402)"),
                 Field("CourseName", width=220),
                 Field("CatalogDescription", required=False, width=260),
                 Field("Required", "choice", choices=["0", "1"], width=70),
                 Field("CreditHours", "int", width=80),
                 Field("LabCourse", "choice", choices=["0", "1"], width=70),
                 Field("DeptID", "fk", label="Department", fk=DEPT_FK)],
         extra=["Prerequisites"],
         select="SELECT c.CourseNumber, c.CourseName, c.CatalogDescription, c.Required, "
                "c.CreditHours, c.LabCourse, c.DeptID, "
                "(SELECT GROUP_CONCAT(PrereqNumber, ', ') FROM Prerequisite p "
                " WHERE p.CourseNumber = c.CourseNumber) "
                "FROM Course c ORDER BY c.CourseNumber"),
    dict(title="Offerings", table="Offering", pk=["OfferingID"],
         fields=[Field("OfferingID", "int", auto=True, width=80),
                 Field("CourseNumber", "fk", label="Course", fk=COURSE_FK),
                 Field("Term", "choice", choices=TERMS, width=70), Field("Year", "int", width=60),
                 Field("Section", "int", width=60),
                 Field("InstructorID", "fk", label="Instructor", fk=INSTRUCTOR_FK, required=False),
                 Field("Capacity", "int", width=70),
                 Field("FourteenDayEnrollment", "int", label="14-day enrollment", required=False)],
         extra=["Instructor name"],
         select="SELECT o.OfferingID, o.CourseNumber, o.Term, o.Year, o.Section, o.InstructorID, "
                "o.Capacity, o.FourteenDayEnrollment, "
                "COALESCE(i.FirstName || ' ' || i.LastName, 'TBA') "
                "FROM Offering o LEFT JOIN Instructor i ON i.InstructorID = o.InstructorID "
                "ORDER BY o.Year DESC, o.Term, o.CourseNumber, o.Section"),
    dict(title="Enrollment", table="Enrollment", pk=["StudentID", "OfferingID"],
         fields=[Field("StudentID", "fk", label="Student", fk=STUDENT_FK),
                 Field("OfferingID", "fk", label="Section", fk=OFFERING_FK),
                 Field("Grade", "choice", choices=GRADES, required=False, width=60)],
         extra=["Student name", "Course", "Term"],
         select="SELECT e.StudentID, e.OfferingID, e.Grade, s.LastName || ', ' || s.FirstName, "
                "o.CourseNumber || ' sec ' || o.Section, o.Term || ' ' || o.Year "
                "FROM Enrollment e JOIN Student s ON s.StudentID = e.StudentID "
                "JOIN Offering o ON o.OfferingID = e.OfferingID "
                "ORDER BY o.Year DESC, o.Term, o.CourseNumber, s.LastName"),
]


def friendly_error(err):
    msg = str(err)
    if "FOREIGN KEY" in msg:
        return ("This change would break a link between tables.\n\n"
                "Either a referenced row does not exist, or other rows still depend on this one "
                "(for example, a course that still has offerings).")
    if "UNIQUE" in msg or "PRIMARY KEY" in msg:
        return f"A row with this key already exists.\n\n({msg})"
    if "CHECK" in msg:
        return f"A value is outside the allowed range.\n\n({msg})"
    if "NOT NULL" in msg:
        return f"A required field is empty.\n\n({msg})"
    return msg


# ----------------------------------------------------------------------------
# Add / edit dialog
# ----------------------------------------------------------------------------

class RecordDialog:
    def __init__(self, app, tab, row=None):
        self.app, self.tab, self.row = app, tab, row
        self.win = tk.Toplevel(app.root)
        self.win.title(f"{'Edit' if row else 'Add'} {tab['title'][:-1] if tab['title'].endswith('s') else tab['title']}")
        self.win.transient(app.root)
        self.win.grab_set()
        self.widgets = {}
        r = 0
        for i, f in enumerate(tab["fields"]):
            if f.auto and row is None:
                continue
            tk.Label(self.win, text=f.label + ("" if f.required else " (optional)"), anchor="w") \
                .grid(row=r, column=0, sticky="w", padx=8, pady=3)
            value = "" if row is None or row[i] is None else str(row[i])
            if f.kind in ("choice", "fk"):
                options = f.choices if f.kind == "choice" else self.fk_options(f)
                if f.kind == "fk" and not f.required:
                    options = [""] + options
                w = ttk.Combobox(self.win, values=options, width=45, state="readonly")
                if f.kind == "fk" and value:
                    value = next((o for o in options if o.split(SEP)[0] == value), value)
                w.set(value)
            else:
                w = ttk.Entry(self.win, width=48)
                w.insert(0, value)
            locked = row is not None and (f.name in tab["pk"])
            if locked:
                w.configure(state="disabled")
            w.grid(row=r, column=1, padx=8, pady=3, sticky="we")
            self.widgets[f.name] = w
            r += 1

        if tab.get("prereqs"):
            tk.Label(self.win, text="Prerequisites (optional)", anchor="nw") \
                .grid(row=r, column=0, sticky="nw", padx=8, pady=3)
            self.prereq_list = tk.Listbox(self.win, selectmode="multiple", height=8, exportselection=False)
            courses = self.fk_options(Field("x", "fk", fk=COURSE_FK))
            current = set()
            if row is not None:
                current = {p for (p,) in app.conn.execute(
                    "SELECT PrereqNumber FROM Prerequisite WHERE CourseNumber = ?", (row[0],))}
            for j, c in enumerate(courses):
                self.prereq_list.insert(tk.END, c)
                if c.split(SEP)[0] in current:
                    self.prereq_list.selection_set(j)
            self.prereq_list.grid(row=r, column=1, padx=8, pady=3, sticky="we")
            r += 1

        bar = tk.Frame(self.win)
        bar.grid(row=r, column=0, columnspan=2, pady=8)
        ttk.Button(bar, text="Save", command=self.save).pack(side="left", padx=4)
        ttk.Button(bar, text="Cancel", command=self.win.destroy).pack(side="left", padx=4)

    def fk_options(self, f):
        return [f"{k}{SEP}{label}" for k, label in self.app.conn.execute(f.fk)]

    def read_values(self):
        values = {}
        for i, f in enumerate(self.tab["fields"]):
            if f.name not in self.widgets:
                continue
            if self.row is not None and f.name in self.tab["pk"]:
                values[f.name] = self.row[i]
                continue
            raw = self.widgets[f.name].get().strip()
            if f.kind == "fk" and raw:
                raw = raw.split(SEP)[0]
            if raw == "":
                if f.required:
                    raise ValueError(f"{f.label} is required.")
                values[f.name] = None
            elif f.kind == "int" or (f.kind == "fk" and raw.isdigit()):
                try:
                    values[f.name] = int(raw)
                except ValueError:
                    raise ValueError(f"{f.label} must be a whole number.")
            elif f.kind == "real":
                try:
                    values[f.name] = float(raw)
                except ValueError:
                    raise ValueError(f"{f.label} must be a number.")
            elif f.kind == "choice" and raw.isdigit():
                values[f.name] = int(raw)
            else:
                values[f.name] = raw
        return values

    def save(self):
        try:
            values = self.read_values()
        except ValueError as e:
            messagebox.showerror("Invalid input", str(e), parent=self.win)
            return
        t, pk, conn = self.tab["table"], self.tab["pk"], self.app.conn
        try:
            with conn:
                if self.row is None:
                    cols = list(values)
                    conn.execute(f"INSERT INTO {t} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                                 [values[c] for c in cols])
                else:
                    cols = [c for c in values if c not in pk]
                    if cols:
                        conn.execute(
                            f"UPDATE {t} SET {', '.join(c + ' = ?' for c in cols)} "
                            f"WHERE {' AND '.join(k + ' = ?' for k in pk)}",
                            [values[c] for c in cols] + [values[k] for k in pk])
                if self.tab.get("prereqs"):
                    course = values["CourseNumber"]
                    chosen = [self.prereq_list.get(j).split(SEP)[0] for j in self.prereq_list.curselection()]
                    conn.execute("DELETE FROM Prerequisite WHERE CourseNumber = ?", (course,))
                    conn.executemany("INSERT INTO Prerequisite VALUES (?, ?)",
                                     [(course, p) for p in chosen if p != course])
        except sqlite3.Error as e:
            messagebox.showerror("Could not save", friendly_error(e), parent=self.win)
            return
        self.win.destroy()
        self.app.refresh_all()


# ----------------------------------------------------------------------------
# One tab: searchable grid + Add / Edit / Delete
# ----------------------------------------------------------------------------

class TableTab:
    def __init__(self, app, notebook, tab):
        self.app, self.tab = app, tab
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=tab["title"])

        top = ttk.Frame(frame)
        top.pack(fill="x", padx=6, pady=6)
        ttk.Label(top, text="Search:").pack(side="left")
        self.search = tk.StringVar()
        self.search.trace_add("write", lambda *_: self.fill())
        ttk.Entry(top, textvariable=self.search, width=30).pack(side="left", padx=4)
        self.count_label = ttk.Label(top, text="")
        self.count_label.pack(side="left", padx=8)
        for text, cmd in [("Delete", self.delete), ("Edit", self.edit), ("Add", self.add)]:
            ttk.Button(top, text=text, command=cmd).pack(side="right", padx=2)

        headings = [f.name for f in tab["fields"]] + tab.get("extra", [])
        widths = [f.width for f in tab["fields"]] + [160] * len(tab.get("extra", []))
        grid = ttk.Frame(frame)
        grid.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.tree = ttk.Treeview(grid, columns=headings, show="headings", selectmode="browse")
        for h, w in zip(headings, widths):
            self.tree.heading(h, text=h)
            self.tree.column(h, width=w, stretch=True)
        ys = ttk.Scrollbar(grid, orient="vertical", command=self.tree.yview)
        xs = ttk.Scrollbar(grid, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        grid.rowconfigure(0, weight=1)
        grid.columnconfigure(0, weight=1)
        self.tree.bind("<Double-1>", lambda e: self.edit())
        self.rows = []
        self.load()

    def load(self):
        self.rows = self.app.conn.execute(self.tab["select"]).fetchall()
        self.fill()

    def fill(self):
        self.tree.delete(*self.tree.get_children())
        term = self.search.get().strip().lower()
        shown = 0
        for i, r in enumerate(self.rows):
            cells = ["" if v is None else str(v) for v in r]
            if term and not any(term in c.lower() for c in cells):
                continue
            self.tree.insert("", tk.END, iid=str(i), values=cells)
            shown += 1
        self.count_label.config(text=f"{shown} of {len(self.rows)} rows")

    def selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select a row", "Select a row first.")
            return None
        return self.rows[int(sel[0])]

    def add(self):
        RecordDialog(self.app, self.tab)

    def edit(self):
        row = self.selected()
        if row is not None:
            RecordDialog(self.app, self.tab, row)

    def delete(self):
        row = self.selected()
        if row is None:
            return
        pk = self.tab["pk"]
        names = [f.name for f in self.tab["fields"]]
        key = [row[names.index(k)] for k in pk]
        desc = ", ".join(f"{k} = {v}" for k, v in zip(pk, key))
        if not messagebox.askyesno("Confirm delete", f"Delete {self.tab['table']} row {desc}?"):
            return
        try:
            with self.app.conn:
                self.app.conn.execute(
                    f"DELETE FROM {self.tab['table']} WHERE {' AND '.join(k + ' = ?' for k in pk)}", key)
        except sqlite3.Error as e:
            messagebox.showerror("Could not delete", friendly_error(e))
            return
        self.app.refresh_all()


# ----------------------------------------------------------------------------
# Test query viewer
# ----------------------------------------------------------------------------

def show_queries(app):
    win = tk.Toplevel(app.root)
    win.title("Test Queries")
    win.geometry("950x500")
    nb = ttk.Notebook(win)
    nb.pack(fill="both", expand=True)
    try:
        results = list(run_queries.run_all(app.conn))
    except (sqlite3.Error, OSError) as e:
        messagebox.showerror("Query failed", str(e), parent=win)
        win.destroy()
        return
    for title, headers, rows in results:
        frame = ttk.Frame(nb)
        nb.add(frame, text=title.split(":")[0])
        ttk.Label(frame, text=f"{title}   ({len(rows)} rows)", font=("Arial", 10, "bold")) \
            .pack(anchor="w", padx=6, pady=4)
        tree = ttk.Treeview(frame, columns=headers, show="headings")
        for h in headers:
            tree.heading(h, text=h)
            tree.column(h, width=140)
        for r in rows:
            tree.insert("", tk.END, values=["" if v is None else v for v in r])
        ys = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=ys.set)
        ys.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True, padx=6, pady=(0, 6))


# ----------------------------------------------------------------------------
# Main window
# ----------------------------------------------------------------------------

class App:
    def __init__(self, db_path=DB_PATH):
        if not os.path.exists(db_path):
            raise SystemExit(f"{db_path} not found. Run first:  python generate_data.py")
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.root = tk.Tk()
        self.root.title("University Records Database")
        self.root.geometry("1100x600")
        top = ttk.Frame(self.root)
        top.pack(fill="x", padx=6, pady=6)
        ttk.Button(top, text="Run Test Queries", command=lambda: show_queries(self)).pack(side="left")
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True)
        self.tabs = [TableTab(self, notebook, t) for t in TABS]

    def refresh_all(self):
        for t in self.tabs:
            t.load()

    def run(self):
        self.root.mainloop()
        self.conn.close()


if __name__ == "__main__":
    App().run()
