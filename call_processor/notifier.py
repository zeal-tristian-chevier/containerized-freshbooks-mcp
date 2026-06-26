import smtplib
from email.message import EmailMessage
from .config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, NOTIFY_EMAIL, EMPLOYEE_EMAIL


def _send(to: str, subject: str, body: str) -> None:
    if not to:
        print(f"[NOTIFY] (no recipient) {subject}")
        return
    if not all([SMTP_USER, SMTP_PASS]):
        print(f"[NOTIFY] (no SMTP config) → {to}: {subject}\n{body}")
        return
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        print(f"[NOTIFY] Email sent to {to}: {subject}")
    except Exception as e:
        print(f"[NOTIFY] Email failed ({e}) — printing instead:\n{body}")


def notify_owner(subject: str, body: str) -> None:
    _send(NOTIFY_EMAIL, subject, body)


def notify_employee(subject: str, body: str) -> None:
    _send(EMPLOYEE_EMAIL, subject, body)


def notify_both(subject: str, body: str) -> None:
    notify_owner(subject, body)
    if EMPLOYEE_EMAIL and EMPLOYEE_EMAIL != NOTIFY_EMAIL:
        notify_employee(subject, body)
