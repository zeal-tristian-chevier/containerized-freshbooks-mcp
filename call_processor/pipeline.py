from datetime import datetime
from pathlib import Path
from . import transcriber, extractor, actions, notifier, scheduler, calendar_reminder
from .config import BASE_DIR, NOTIFY_EMAIL, EMPLOYEE_EMAIL

# Call types that warrant FreshBooks client/estimate creation
_CUSTOMER_TYPES = {"customer_intake", "customer_update", "unknown"}

# Human-readable labels for the summary email subject
_TYPE_LABELS = {
    "customer_intake":  "New Customer",
    "customer_update":  "Customer Update",
    "parts_supplier":   "Parts/Supplier",
    "subcontractor":    "Subcontractor",
    "business":         "Business",
    "internal":         "Internal",
    "unknown":          "Unknown",
}


def _write_inbox_note(audio_path: Path, data: dict, transcript: str) -> None:
    """Drop a structured markdown note into _inbox/ for the knowledge base ingest skill."""
    inbox = BASE_DIR / "_inbox"
    inbox.mkdir(exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    call_type = data.get("call_type", "unknown")
    fname = f"call-{ts}-{call_type}.md"

    parts_lines = []
    for p in data.get("parts_status") or []:
        line = f"- **{p.get('part')}** — {p.get('status')}"
        if p.get("eta"):
            line += f" (ETA: {p['eta']})"
        if p.get("supplier"):
            line += f" via {p['supplier']}"
        if p.get("decision"):
            line += f" | Decision: {p['decision']}"
        parts_lines.append(line)

    decisions = data.get("decisions_made") or []
    follow_ups = data.get("follow_ups") or []
    employee_tasks = data.get("employee_tasks") or []
    customer = data.get("customer") or {}
    atv = data.get("atv") or {}
    job = data.get("job") or {}

    lines = [
        "---",
        f"title: Call — {_TYPE_LABELS.get(call_type, call_type)} — {ts[:8]}",
        f"source: call transcript {audio_path.name}",
        f"date: {ts[:4]}-{ts[4:6]}-{ts[6:8]}",
        "status: extracted",
        f"call_type: {call_type}",
        "---",
        "",
        f"## Summary",
        f"{data.get('call_summary') or 'No summary extracted.'}",
        "",
    ]

    if customer.get("name"):
        lines += [
            "## Customer",
            f"- Name: {customer.get('name')}",
            f"- Phone: {customer.get('phone') or 'N/A'}",
            f"- Email: {customer.get('email') or 'N/A'}",
            f"- Returning: {customer.get('is_returning')}",
            "",
        ]

    if atv.get("make") or atv.get("model"):
        atv_str = " ".join(filter(None, [atv.get("year"), atv.get("make"), atv.get("model"), atv.get("color")]))
        lines += [
            "## ATV",
            f"- {atv_str}",
            f"- Issue: {atv.get('issue') or 'N/A'}",
            "",
        ]

    if job.get("work_requested"):
        lines += [
            "## Job",
            f"- Work: {job.get('work_requested')}",
            f"- Quote: ${job.get('quoted_price') or 'N/A'}",
            f"- Drop-off: {job.get('drop_off_date') or 'N/A'}",
            f"- Est. completion: {job.get('estimated_completion') or 'N/A'}",
            "",
        ]

    if parts_lines:
        lines += ["## Parts Status", *parts_lines, ""]

    if data.get("parts_needed"):
        lines += ["## Parts to Order", *[f"- {p}" for p in data["parts_needed"]], ""]

    if decisions:
        lines += ["## Decisions Made", *[f"- {d}" for d in decisions], ""]

    if follow_ups:
        lines += ["## Follow-ups"]
        for fu in follow_ups:
            due = fu.get("due_date") or "TBD"
            t = fu.get("due_time") or ""
            lines.append(f"- [{due}{' ' + t if t else ''}] {fu.get('description')} → {fu.get('assignee') or 'owner'}")
        lines.append("")

    if employee_tasks:
        lines += ["## Employee Tasks"]
        for task in employee_tasks:
            lines.append(f"- [{task.get('due_date') or 'TBD'}] {task.get('task')} → {task.get('assignee') or 'steve'}")
        lines.append("")

    if data.get("notes"):
        lines += ["## Notes", data["notes"], ""]

    lines += ["## Transcript", "```", transcript.strip(), "```", ""]

    (inbox / fname).write_text("\n".join(lines), encoding="utf-8")
    print(f"[PIPELINE] Inbox note written: {fname}")


def _send_calendar_invites(data: dict, audio_stem: str, call_summary: str) -> int:
    """Send ICS calendar invites for any follow-up that has a specific due_date."""
    sent = 0
    all_items = (data.get("follow_ups") or []) + (data.get("employee_tasks") or [])

    for item in all_items:
        due_date = item.get("due_date")
        if not due_date:
            continue

        desc = item.get("description") or item.get("task") or "Follow up"
        due_time = item.get("due_time")
        assignee = item.get("assignee") or "owner"
        title = f"CHEVS: {desc}"

        # Determine recipient(s)
        recipients = []
        if assignee in ("owner", None):
            if NOTIFY_EMAIL:
                recipients.append(NOTIFY_EMAIL)
        elif assignee == "steve":
            if EMPLOYEE_EMAIL:
                recipients.append(EMPLOYEE_EMAIL)
            if NOTIFY_EMAIL:
                recipients.append(NOTIFY_EMAIL)

        body = f"Call summary: {call_summary}\nFile: {audio_stem}\n\n{desc}"

        for to in recipients:
            calendar_reminder.send_calendar_reminder(title, due_date, due_time, body, to)
            sent += 1

    # Also send a calendar reminder for estimated job completion (customer calls)
    job = data.get("job") or {}
    if job.get("estimated_completion") and data.get("customer", {}).get("name"):
        customer_name = data["customer"]["name"]
        atv = data.get("atv") or {}
        atv_str = " ".join(filter(None, [atv.get("year"), atv.get("make"), atv.get("model")])) or "ATV"
        title = f"CHEVS: ATV ready — {customer_name} {atv_str}"
        body = f"Estimated completion for {customer_name}'s {atv_str}.\n{job.get('work_requested') or ''}"
        if NOTIFY_EMAIL:
            calendar_reminder.send_calendar_reminder(title, job["estimated_completion"], None, body, NOTIFY_EMAIL)
            sent += 1

    # Parts ETA reminders
    for ps in data.get("parts_status") or []:
        if ps.get("eta"):
            title = f"CHEVS: Parts arriving — {ps.get('part', 'unknown')}"
            body = f"Parts ETA from {ps.get('supplier') or 'supplier'}.\nStatus: {ps.get('status')}\n{call_summary}"
            if NOTIFY_EMAIL:
                calendar_reminder.send_calendar_reminder(title, ps["eta"], None, body, NOTIFY_EMAIL)
                sent += 1

    return sent


def process(audio_path: Path) -> None:
    print(f"\n{'='*60}")
    print(f"[PIPELINE] Processing: {audio_path.name}")

    # 1. Transcribe
    transcript = transcriber.transcribe(str(audio_path))
    if not transcript:
        print("[PIPELINE] Empty transcript — skipping.")
        return

    # 2. Extract structured data + call type classification
    data = extractor.extract(transcript)
    call_type = data.get("call_type", "unknown")
    call_summary = data.get("call_summary") or "No summary"
    audio_stem = audio_path.stem

    print(f"[PIPELINE] Call type: {_TYPE_LABELS.get(call_type, call_type)}")
    print(f"[PIPELINE] Summary: {call_summary}")

    # 3. Write to _inbox/ for every call (knowledge base ingest skill picks this up)
    _write_inbox_note(audio_path, data, transcript)

    # 4. FreshBooks actions — customer calls only
    client_record: dict = {}
    estimate: dict = {}

    if call_type in _CUSTOMER_TYPES:
        fb = actions.get_fb_client()
        customer = data.get("customer") or {}
        if customer.get("name"):
            client_record = actions.find_or_create_client(fb, customer)

        client_id = client_record.get("id")
        job = data.get("job") or {}
        if client_id and job.get("work_requested"):
            estimate = actions.create_estimate(fb, client_id, job, data.get("atv") or {}, data.get("notes"))
    else:
        print(f"[PIPELINE] Skipping FreshBooks actions for {call_type} call.")

    # 5. APScheduler reminders (all call types — internal queue)
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

    # 6. Calendar invites for any follow-up or event with a specific date
    cal_count = _send_calendar_invites(data, audio_stem, call_summary)
    print(f"[PIPELINE] Calendar invites sent: {cal_count}")

    # 7. Summary email
    _send_summary(audio_path, data, call_type, call_summary, client_record, estimate)

    customer = data.get("customer") or {}
    cname = customer.get("name") or call_summary
    print(f"[PIPELINE] Done: {_TYPE_LABELS.get(call_type, call_type)} | {cname}")
    print("=" * 60)


def _send_summary(audio_path: Path, data: dict, call_type: str, call_summary: str,
                  client_record: dict, estimate: dict) -> None:
    customer = data.get("customer") or {}
    atv = data.get("atv") or {}
    job = data.get("job") or {}
    parts = data.get("parts_needed") or []
    parts_status = data.get("parts_status") or []
    decisions = data.get("decisions_made") or []
    follow_ups = data.get("follow_ups") or []
    employee_tasks = data.get("employee_tasks") or []

    cname = customer.get("name") or "N/A"
    atv_str = " ".join(filter(None, [atv.get("year"), atv.get("make"), atv.get("model")])) or "N/A"
    type_label = _TYPE_LABELS.get(call_type, call_type)

    lines = [
        f"Call file:   {audio_path.name}",
        f"Call type:   {type_label}",
        f"Summary:     {call_summary}",
        "",
    ]

    if call_type in _CUSTOMER_TYPES:
        lines += [
            f"Customer:    {cname}",
            f"Phone:       {customer.get('phone') or 'N/A'}",
            f"ATV:         {atv_str}",
            f"Issue:       {atv.get('issue') or 'N/A'}",
            f"Work:        {job.get('work_requested') or 'N/A'}",
            f"Quote:       ${job.get('quoted_price') or 'N/A'}",
            f"Drop-off:    {job.get('drop_off_date') or 'N/A'}",
            f"Est. done:   {job.get('estimated_completion') or 'N/A'}",
            "",
            f"FreshBooks client:   {'id=' + str(client_record.get('id')) if client_record else 'not created'}",
            f"FreshBooks estimate: {'id=' + str(estimate.get('id')) if estimate else 'not created'}",
            "",
        ]

    if parts_status:
        lines.append(f"Parts status ({len(parts_status)}):")
        for p in parts_status:
            eta = f" | ETA: {p['eta']}" if p.get("eta") else ""
            dec = f" | {p['decision']}" if p.get("decision") else ""
            lines.append(f"  - {p.get('part')} [{p.get('status')}]{eta}{dec}")
        lines.append("")

    if parts:
        lines.append(f"Parts to order ({len(parts)}):")
        lines += [f"  - {p}" for p in parts]
        lines.append("")

    if decisions:
        lines.append(f"Decisions made ({len(decisions)}):")
        lines += [f"  - {d}" for d in decisions]
        lines.append("")

    all_reminders = follow_ups + employee_tasks
    if all_reminders:
        lines.append(f"Reminders/tasks ({len(all_reminders)}):")
        for r in all_reminders:
            due = r.get("due_date") or "TBD"
            desc = r.get("description") or r.get("task") or ""
            assignee = r.get("assignee") or "owner"
            cal = " 📅" if r.get("due_date") else ""
            lines.append(f"  - [{due}] {desc} → {assignee}{cal}")
        lines.append("")

    if data.get("notes"):
        lines += [f"Notes: {data['notes']}", ""]

    body = "\n".join(lines)
    subject = f"Call ({type_label}): {cname if call_type in _CUSTOMER_TYPES else call_summary}"
    notifier.notify_owner(subject, body)

    # Notify Steve if he has tasks
    steve_tasks = [t for t in employee_tasks if t.get("assignee") == "steve"]
    if steve_tasks and EMPLOYEE_EMAIL:
        task_lines = [f"Tasks from a {type_label.lower()} call ({call_summary}):"]
        for t in steve_tasks:
            task_lines.append(f"  - [{t.get('due_date') or 'TBD'}] {t.get('task')}")
        notifier.notify_employee(f"Tasks: {call_summary}", "\n".join(task_lines))
