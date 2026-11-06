import os
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta


@contextmanager
def connection():
    conn = sqlite3.connect("library.db")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db():
    with connection() as conn:
        conn.executescript(
            """
            DROP TABLE IF EXISTS books;
            DROP TABLE IF EXISTS members;
            DROP TABLE IF EXISTS loans;
            CREATE TABLE books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT, author TEXT, isbn TEXT, available INTEGER DEFAULT 1
            );
            CREATE TABLE members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, email TEXT UNIQUE, type TEXT
            );
            CREATE TABLE loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER, member_id INTEGER, due_date TEXT,
                returned INTEGER DEFAULT 0, fine REAL DEFAULT 0,
                fine_paid INTEGER DEFAULT 0, renewals INTEGER DEFAULT 0,
                checked_out TEXT
            );
            """
        )
        books = [
            ("Clean Code", "Robert C. Martin", "9780132350884", 1),
            ("The Pragmatic Programmer", "Andrew Hunt", "9780135957059", 1),
            ("Design Patterns", "Erich Gamma", "9780201633610", 1),
            ("Refactoring", "Martin Fowler", "9780134757599", 1),
            ("Code Complete", "Steve McConnell", "9780735619678", 0),
        ]
        conn.executemany("INSERT INTO books (title, author, isbn, available) VALUES (?, ?, ?, ?)", books)
        members = [
            ("Sam Rivera", "sam@campus.edu", "student"),
            ("Dr. Noor Aziz", "noor@campus.edu", "staff"),
            ("Alex Chen", "alex@campus.edu", "student"),
        ]
        conn.executemany("INSERT INTO members (name, email, type) VALUES (?, ?, ?)", members)
        today = date.today()
        conn.execute(
            "INSERT INTO loans (book_id, member_id, due_date, checked_out) VALUES (5, 3, ?, ?)",
            ((today - timedelta(days=5)).isoformat(), (today - timedelta(days=19)).isoformat()),
        )


def initialize_if_needed():
    if not os.path.exists("library.db"):
        init_db()


def list_books(conn, available_only=False):
    if available_only:
        return conn.execute("SELECT * FROM books WHERE available = 1").fetchall()
    return conn.execute("SELECT * FROM books").fetchall()


def get_book(conn, book_id):
    return conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()


def insert_book(conn, title, author, isbn):
    cur = conn.execute(
        "INSERT INTO books (title, author, isbn, available) VALUES (?, ?, ?, 1)",
        (title, author, isbn),
    )
    return get_book(conn, cur.lastrowid)


def delete_book(conn, book_id):
    conn.execute("DELETE FROM books WHERE id = ?", (book_id,))


def list_members(conn):
    return conn.execute("SELECT * FROM members").fetchall()


def get_member(conn, member_id):
    return conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()


def get_member_by_email(conn, email):
    return conn.execute("SELECT * FROM members WHERE email = ?", (email,)).fetchone()


def insert_member(conn, name, email, member_type):
    cur = conn.execute(
        "INSERT INTO members (name, email, type) VALUES (?, ?, ?)",
        (name, email, member_type),
    )
    return get_member(conn, cur.lastrowid)


def get_member_loans(conn, member_id):
    return conn.execute("SELECT * FROM loans WHERE member_id = ?", (member_id,)).fetchall()


def list_loans(conn):
    return conn.execute("SELECT * FROM loans").fetchall()


def get_loan(conn, loan_id):
    return conn.execute("SELECT * FROM loans WHERE id = ?", (loan_id,)).fetchone()


def insert_loan(conn, book_id, member_id, due_date, checked_out):
    cur = conn.execute(
        "INSERT INTO loans (book_id, member_id, due_date, checked_out) VALUES (?, ?, ?, ?)",
        (book_id, member_id, due_date, checked_out),
    )
    return get_loan(conn, cur.lastrowid)


def set_book_availability(conn, book_id, available):
    conn.execute("UPDATE books SET available = ? WHERE id = ?", (int(available), book_id))


def mark_loan_returned(conn, loan_id, fine):
    conn.execute("UPDATE loans SET returned = 1, fine = ? WHERE id = ?", (fine, loan_id))


def renew_loan(conn, loan_id, new_due):
    conn.execute("UPDATE loans SET due_date = ?, renewals = renewals + 1 WHERE id = ?", (new_due, loan_id))


def mark_fine_paid(conn, loan_id):
    conn.execute("UPDATE loans SET fine_paid = 1 WHERE id = ?", (loan_id,))


def overdue_report_rows(conn):
    return conn.execute(
        """
        SELECT loans.id, books.title, members.name, loans.due_date
        FROM loans
        JOIN books ON books.id = loans.book_id
        JOIN members ON members.id = loans.member_id
        WHERE loans.returned = 0
        """
    ).fetchall()


def count_books(conn):
    return conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
