from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from .config import DB_PATH
from . import notifier

_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        jobstores = {"default": SQLAlchemyJobStore(url=f"sqlite:///{DB_PATH}")}
        executors = {"default": ThreadPoolExecutor(4)}
        _scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, timezone="America/Chicago")
        _scheduler.start()
        print(f"[SCHEDULER] Started. DB: {DB_PATH}")
    return _scheduler


def schedule_reminder(description: str, due_date: str | None, assignee: str, job_id: str | None = None) -> None:
    if due_date:
        try:
            run_at = datetime.fromisoformat(due_date).replace(hour=9, minute=0, second=0)
        except ValueError:
            run_at = datetime.now() + timedelta(days=2)
    else:
        run_at = datetime.now() + timedelta(days=2)

    # Don't schedule reminders in the past
    if run_at < datetime.now():
        run_at = datetime.now() + timedelta(minutes=5)

    def _fire(msg: str, who: str) -> None:
        subject = "CHEVS Garage Reminder"
        if who == "steve":
            notifier.notify_employee(subject, msg)
        else:
            notifier.notify_owner(subject, msg)

    scheduler = get_scheduler()
    scheduler.add_job(
        _fire,
        "date",
        run_date=run_at,
        args=[description, assignee],
        id=job_id,
        replace_existing=True,
    )
    print(f"[SCHEDULER] Reminder scheduled for {run_at.date()} → {assignee}: {description[:60]}")


def list_pending() -> list[dict]:
    jobs = get_scheduler().get_jobs()
    return [
        {
            "id": j.id,
            "next_run": str(j.next_run_time),
            "args": j.args,
        }
        for j in jobs
    ]
