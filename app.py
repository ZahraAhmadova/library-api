from flask import Flask, jsonify, request

import database
import services
from database import init_db
from validation import validate_book, validate_loan, validate_member

__all__ = ["app", "init_db"]

app = Flask(__name__)


def _respond(payload, status=200):
    if status == 204:
        return "", 204
    return jsonify(payload), status


@app.route("/books", methods=["GET"])
def list_books():
    return jsonify(services.list_books(request.args.get("available") == "true"))


@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    return _respond(*services.get_book(book_id))


@app.route("/books", methods=["POST"])
def create_book():
    data = request.get_json(silent=True) or {}
    error = validate_book(data)
    if error is not None:
        return _respond({"error": error}, 400)
    return _respond(*services.create_book(data["title"], data["author"], data["isbn"]))


@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    return _respond(*services.delete_book(book_id))


@app.route("/members", methods=["GET"])
def list_members():
    return jsonify(services.list_members())


@app.route("/members/<int:member_id>", methods=["GET"])
def get_member(member_id):
    return _respond(*services.get_member(member_id))


@app.route("/members", methods=["POST"])
def create_member():
    data = request.get_json(silent=True) or {}
    error, member_type = validate_member(data)
    if error is not None:
        return _respond({"error": error}, 400)
    return _respond(*services.create_member(data["name"], data["email"], member_type))


@app.route("/members/<int:member_id>/loans", methods=["GET"])
def member_loans(member_id):
    return _respond(*services.member_loans(member_id))


@app.route("/loans", methods=["GET"])
def list_loans():
    return jsonify(services.list_loans(request.args.get("overdue") == "true"))


@app.route("/loans/<int:loan_id>", methods=["GET"])
def get_loan(loan_id):
    return _respond(*services.get_loan(loan_id))


@app.route("/loans", methods=["POST"])
def create_loan():
    data = request.get_json(silent=True) or {}
    error = validate_loan(data)
    if error is not None:
        return _respond({"error": error}, 400)
    return _respond(*services.create_loan(data["book_id"], data["member_id"], data.get("due_date")))


@app.route("/loans/<int:loan_id>/return", methods=["POST"])
def return_book(loan_id):
    return _respond(*services.return_book(loan_id))


@app.route("/loans/<int:loan_id>/renew", methods=["POST"])
def renew_loan(loan_id):
    return _respond(*services.renew_loan(loan_id))


@app.route("/loans/<int:loan_id>/pay-fine", methods=["POST"])
def pay_fine(loan_id):
    return _respond(*services.pay_fine(loan_id))


@app.route("/reports/overdue", methods=["GET"])
def report_overdue():
    return jsonify(services.report_overdue())


@app.route("/reports/summary", methods=["GET"])
def report_summary():
    return jsonify(services.report_summary())


database.initialize_if_needed()
