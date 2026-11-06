from rules import money


def _write(recipient_email, subject, body):
    with open("outbox.txt", "a") as outbox:
        outbox.write(
            "TO: " + recipient_email + " | SUBJECT: " + subject + " | BODY: " + body + "\n"
        )


def notify(recipient_email, kind, title="", send=True):
    if not send:
        return
    if kind == "checkout":
        subject = "Book checked out"
        body = "You checked out " + title
    elif kind == "renew":
        subject = "Loan renewed"
        body = "You renewed " + title
    else:
        subject = "Library notice"
        body = title
    _write(recipient_email, subject, body)


def notify_returned(recipient_email, title, fine):
    _write(recipient_email, "Book returned", "You returned " + title + ". Fine: $" + str(money(fine)))


def notify_fine_paid(recipient_email, fine):
    _write(recipient_email, "Fine paid", "We received $" + str(money(fine)))
