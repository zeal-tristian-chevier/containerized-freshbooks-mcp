from pathlib import Path
from . import transcriber, extractor, actions, notifier, scheduler


def process(audio_path: Path) -> None:
    print(f"\n{'='*60}")
    print(f"[PIPELINE] Processing: {audio_path.name}")

    # 1. Transcribe
    transcript = transcriber.transcribe(str(audio_path))
    if not transcript:
        print("[PIPELINE] Empty transcript — skipping.")
        return

    # 2. Extract structured data via Claude
    data = extractor.extract(transcript)

    # 3. FreshBooks
    fb = actions.get_fb_client()
    client_record: dict = {}
    estimate: dict = {}

    customer = data.get("customer") or {}
    if customer.get("name"):
        client_record = actions.find_or_create_client(fb, customer)

    client_id = client_record.get("id")
    job = data.get("job") or {}
    if client_id and job.get("work_requested"):
        estimate = actions.create_estimate(fb, client_id, job, data.get("atv") or {}, data.get("notes"))

    # 4. Schedule reminders
    audio_stem = audio_path.stem
    for i, fu in enumerate(data.get("follow_ups") or []):
        desc = fu.get("description") or "Follow up"
        due = fu.get("due_date")
        assignee = fu.get("assignee") or "owner"
        scheduler.schedule_reminder(desc, due, assignee, job_id=f"{audio_stem}_fu_{i}")

    for i, task in enumerate(data.get("employee_tasks") or []):
        desc = task.get("task") or "Task from call"
        due = task.get("due_date")
        assignee = task.get("assignee") or "steve"
        scheduler.schedule_reminder(desc, due, assignee, job_id=f"{audio_stem}_task_{i}")

    # 5. Send summary to owner
    cname = customer.get("name") or "Unknown"
    atv = data.get("atv") or {}
    atv_str = " ".join(filter(None, [atv.get("year"), atv.get("make"), atv.get("model")])) or "Unknown ATV"
    parts = data.get("parts_needed") or []
    reminders = (data.get("follow_ups") or []) + (data.get("employee_tasks") or [])

    summary_lines = [
        f"Call file: {audio_path.name}",
        f"Customer:  {cname}",
        f"Phone:     {customer.get('phone') or 'N/A'}",
        f"ATV:       {atv_str}",
        f"Issue:     {atv.get('issue') or 'N/A'}",
        f"Work:      {job.get('work_requested') or 'N/A'}",
        f"Quote:     ${job.get('quoted_price') or 'N/A'}",
        f"Drop-off:  {job.get('drop_off_date') or 'N/A'}",
        f"Est. done: {job.get('estimated_completion') or 'N/A'}",
        "",
        f"FreshBooks client: {'id=' + str(client_record.get('id')) if client_record else 'not created'}",
        f"FreshBooks estimate: {'id=' + str(estimate.get('id')) if estimate else 'not created'}",
        "",
        f"Parts needed ({len(parts)}):",
        *[f"  - {p}" for p in parts],
        "",
        f"Reminders scheduled ({len(reminders)}):",
        *[f"  - [{r.get('due_date') or 'TBD'}] {r.get('description') or r.get('task')} → {r.get('assignee') or 'owner'}"
          for r in reminders],
        "",
        f"Notes: {data.get('notes') or 'None'}",
    ]

    body = "\n".join(summary_lines)
    notifier.notify_owner(f"Call Processed: {cname} | {atv_str}", body)

    print(f"[PIPELINE] Done: {cname} | {atv_str}")
    print("=" * 60)
