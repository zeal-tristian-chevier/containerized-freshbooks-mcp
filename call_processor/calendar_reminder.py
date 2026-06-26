import uuid
import smtplib
from datetime import date, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from icalendar import Calendar, Event as ICSEvent

from .config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, TZ


def _make_ics(title: str, event_date: str, event_time: str | None, description: str) -> bytes:
    cal = Calendar()
    cal.add("prodid", "-//CHEVS Garage//Call Processor//EN")
    cal.add("version", "2.0")
    cal.add("method", "PUBLISH")

    event = ICSEvent()
    event.add("summary", title)
    event.add("description", description)
    event.add("uid", str(uuid.uuid4()))

    tz = ZoneInfo(TZ)
    y, mo, d = map(int, event_date.split("-"))

    if event_time:
        h, m = map(int, event_time.split(":"))
        dt_start = datetime(y, mo, d, h, m, tzinfo=tz)
        event.add("dtstart", dt_start)
        event.add("dtend", dt_start + timedelta(hours=1))
    else:
        event.add("dtstart", date(y, mo, d))
        event.add("dtend", date(y, mo, d) + timedelta(days=1))

    cal.add_component(event)
    return cal.to_ical()


def send_calendar_reminder(title: str, event_date: str, event_time: str | None,
                            description: str, to: str) -> None:
    if not to:
        print(f"[CALENDAR] (no recipient) {title} on {event_date}")
        return
    if not all([SMTP_USER, SMTP_PASS]):
        print(f"[CALENDAR] (no SMTP) Would create: {title} on {event_date}")
        return

    ics_bytes = _make_ics(title, event_date, event_time, description)
    date_str = f"{event_date} at {event_time}" if event_time else event_date

    msg = MIMEMultipart("mixed")
    msg["From"] = SMTP_USER
    msg["To"] = to
    msg["Subject"] = f"Reminder: {title}"

    body = f"{title}\nDate: {date_str}\n\n{description}\n\nOpen the attached .ics file to add this to your calendar."
    msg.attach(MIMEText(body, "plain"))

    ics_part = MIMEBase("text", "calendar", method="PUBLISH", name="reminder.ics")
    ics_part.set_payload(ics_bytes)
    encoders.encode_base64(ics_part)
    ics_part.add_header("Content-Disposition", "attachment", filename="reminder.ics")
    msg.attach(ics_part)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        print(f"[CALENDAR] Invite sent to {to}: {title} on {event_date}")
    except Exception as e:
        print(f"[CALENDAR] Failed ({e}): {title} on {event_date}")
