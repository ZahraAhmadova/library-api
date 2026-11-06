import re
from datetime import date


def check(value, kind):
    if kind == "email":
        return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(value)) is not None
    elif kind == "isbn":
        digits = str(value).replace("-", "")
        return digits.isdigit() and len(digits) in (10, 13)
    elif kind == "date":
        try:
            date.fromisoformat(str(value))
            return True
        except ValueError:
            return False
    elif kind == "member_type":
        return value in ("student", "staff")
    return False


def validate_book(data):
    if not data.get("title") or not data.get("author"):
        return "title and author are required"
    if not check(data.get("isbn"), "isbn"):
        return "invalid isbn"
    return None


def validate_member(data):
    if not data.get("name"):
        return "name is required", None
    if not check(data.get("email"), "email"):
        return "invalid email", None
    member_type = data.get("type", "student")
    if not check(member_type, "member_type"):
        return "type must be student or staff", None
    return None, member_type


def validate_loan(data):
    if not data.get("book_id") or not data.get("member_id"):
        return "book_id and member_id are required"
    if data.get("due_date") and not check(data["due_date"], "date"):
        return "invalid due_date"
    return None
