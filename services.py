from datetime import date, timedelta

import database
import notifications
from rules import compute_fine, money

_MISSING = object()


def _book_dict(book):
    return {"id": book[0], "title": book[1], "author": book[2], "isbn": book[3], "available": bool(book[4])}


def _member_dict(member):
    return {"id": member[0], "name": member[1], "email": member[2], "type": member[3]}


def _loan_dict(loan, current_fine=_MISSING):
    result = {
        "id": loan[0],
        "book_id": loan[1],
        "member_id": loan[2],
        "due_date": loan[3],
        "returned": bool(loan[4]),
        "fine": money(loan[5]),
        "fine_paid": bool(loan[6]),
    }
    if current_fine is not _MISSING:
        result.update(
            {
                "renewals": loan[7],
                "checked_out": loan[8],
                "current_fine": money(current_fine),
            }
        )
    else:
        result.update({"renewals": loan[7], "checked_out": loan[8]})
    return result


def _not_found(resource):
    return {"error": resource + " not found"}, 404


def list_books(available_only=False):
    with database.connection() as conn:
        rows = database.list_books(conn, available_only)
    return [_book_dict(row) for row in rows]


def get_book(book_id):
    with database.connection() as conn:
        book = database.get_book(conn, book_id)
    if book is None:
        return _not_found("book")
    return _book_dict(book), 200


def create_book(title, author, isbn):
    with database.connection() as conn:
        book = database.insert_book(conn, title, author, isbn)
    return _book_dict(book), 201


def delete_book(book_id):
    with database.connection() as conn:
        book = database.get_book(conn, book_id)
        if book is None:
            return _not_found("book")
        if book[4] == 0:
            return {"error": "book is on loan"}, 409
        database.delete_book(conn, book_id)
    return None, 204


def list_members():
    with database.connection() as conn:
        rows = database.list_members(conn)
    return [_member_dict(row) for row in rows]


def get_member(member_id):
    with database.connection() as conn:
        member = database.get_member(conn, member_id)
    if member is None:
        return _not_found("member")
    return _member_dict(member), 200


def create_member(name, email, member_type):
    with database.connection() as conn:
        if database.get_member_by_email(conn, email) is not None:
            return {"error": "email already registered"}, 409
        member = database.insert_member(conn, name, email, member_type)
    return _member_dict(member), 201


def member_loans(member_id):
    with database.connection() as conn:
        member = database.get_member(conn, member_id)
        if member is None:
            return _not_found("member")
        rows = database.get_member_loans(conn, member_id)

    owed = 0
    open_loans = 0
    loans = []
    for loan in rows:
        if loan[4] == 0:
            open_loans += 1
            days_late = (date.today() - date.fromisoformat(loan[3])).days
            if days_late > 0:
                owed += compute_fine(days_late)
        elif loan[6] == 0:
            owed += loan[5]
        loans.append(
            {
                "id": loan[0],
                "book_id": loan[1],
                "due_date": loan[3],
                "returned": bool(loan[4]),
                "fine": money(loan[5]),
                "fine_paid": bool(loan[6]),
            }
        )
    remaining = (5 if member[3] == "staff" else 3) - open_loans
    return {"loans": loans, "total_owed": money(owed), "loans_remaining": remaining}, 200


def list_loans(overdue_only=False):
    with database.connection() as conn:
        rows = database.list_loans(conn)
    result = []
    for loan in rows:
        current_fine = loan[5]
        days_late = (date.today() - date.fromisoformat(loan[3])).days
        if loan[4] == 0:
            current_fine = compute_fine(days_late)
        if overdue_only and (loan[4] == 1 or days_late <= 0):
            continue
        result.append(_loan_dict(loan, current_fine))
    return result


def get_loan(loan_id):
    with database.connection() as conn:
        loan = database.get_loan(conn, loan_id)
    if loan is None:
        return _not_found("loan")
    current_fine = loan[5]
    if loan[4] == 0:
        days_late = (date.today() - date.fromisoformat(loan[3])).days
        current_fine = compute_fine(days_late)
    return _loan_dict(loan, current_fine), 200


def create_loan(book_id, member_id, requested_due_date=None):
    with database.connection() as conn:
        book = database.get_book(conn, book_id)
        if book is None:
            return _not_found("book")
        member = database.get_member(conn, member_id)
        if member is None:
            return _not_found("member")
        if book[4] == 0:
            return {"error": "book is not available"}, 409

        rows = database.get_member_loans(conn, member_id)
        owed = 0
        open_loans = 0
        for loan in rows:
            if loan[4] == 0:
                open_loans += 1
                days_late = (date.today() - date.fromisoformat(loan[3])).days
                if days_late > 0:
                    owed += compute_fine(days_late)
            elif loan[6] == 0:
                owed += loan[5]
        if owed > 0:
            return {"error": "member has unpaid fines"}, 409

        limit = 5 if member[3] == "staff" else 3
        if open_loans >= limit:
            return {"error": "loan limit reached"}, 409

        today = date.today()
        due_date = requested_due_date or (today + timedelta(days=14)).isoformat()
        loan = database.insert_loan(conn, book_id, member_id, due_date, today.isoformat())
        database.set_book_availability(conn, book_id, False)

    notifications.notify(member[2], "checkout", book[1])
    return _loan_dict(loan), 201


def return_book(loan_id):
    with database.connection() as conn:
        loan = database.get_loan(conn, loan_id)
        if loan is None:
            return _not_found("loan")
        if loan[4] == 1:
            return {"error": "loan already returned"}, 409

        days_late = (date.today() - date.fromisoformat(loan[3])).days
        fine = compute_fine(days_late)
        database.mark_loan_returned(conn, loan_id, fine)
        database.set_book_availability(conn, loan[1], True)
        member = database.get_member(conn, loan[2])
        book = database.get_book(conn, loan[1])
        updated = database.get_loan(conn, loan_id)

    notifications.notify_returned(member[2], book[1], fine)
    return _loan_dict(updated), 200


def renew_loan(loan_id):
    with database.connection() as conn:
        loan = database.get_loan(conn, loan_id)
        if loan is None:
            return _not_found("loan")
        if loan[4] == 1:
            return {"error": "loan already returned"}, 409
        if date.fromisoformat(loan[3]) < date.today():
            return {"error": "overdue loans cannot be renewed"}, 409
        if loan[7] >= 1:
            return {"error": "loan was already renewed"}, 409

        new_due = (date.fromisoformat(loan[3]) + timedelta(days=14)).isoformat()
        database.renew_loan(conn, loan_id, new_due)
        member = database.get_member(conn, loan[2])
        book = database.get_book(conn, loan[1])
        updated = database.get_loan(conn, loan_id)

    notifications.notify(member[2], "renew", book[1])
    return _loan_dict(updated), 200


def pay_fine(loan_id):
    with database.connection() as conn:
        loan = database.get_loan(conn, loan_id)
        if loan is None:
            return _not_found("loan")
        if loan[4] == 0:
            return {"error": "return the book before paying"}, 409
        if loan[5] <= 0 or loan[6] == 1:
            return {"error": "no fine to pay"}, 409

        database.mark_fine_paid(conn, loan_id)
        member = database.get_member(conn, loan[2])
        updated = database.get_loan(conn, loan_id)

    notifications.notify_fine_paid(member[2], loan[5])
    return _loan_dict(updated), 200


def report_overdue():
    with database.connection() as conn:
        rows = database.overdue_report_rows(conn)
    items = []
    total = 0
    for row in rows:
        days_late = (date.today() - date.fromisoformat(row[3])).days
        if days_late > 0:
            fine = compute_fine(days_late)
            total += fine
            items.append(
                {"loan_id": row[0], "title": row[1], "member": row[2], "days_late": days_late, "fine": money(fine)}
            )
    return {"items": items, "total_fines": money(total)}


def report_summary():
    with database.connection() as conn:
        total_books = database.count_books(conn)
        rows = database.list_loans(conn)
    on_loan = 0
    outstanding = 0
    for loan in rows:
        if loan[4] == 0:
            on_loan += 1
            days_late = (date.today() - date.fromisoformat(loan[3])).days
            outstanding += compute_fine(days_late)
        elif loan[6] == 0:
            outstanding += loan[5]
    return {"total_books": total_books, "on_loan": on_loan, "fines_outstanding": money(outstanding)}
