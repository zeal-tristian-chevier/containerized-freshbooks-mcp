"""
Test the call processor pipeline with fake transcripts.
Runs extractor → shows classification + structured data → optionally runs full pipeline.

Usage:
    .venv\Scripts\python.exe scripts\test_processor.py           (Windows)
    .venv/bin/python scripts/test_processor.py                   (macOS)
    docker compose run --rm call-processor python scripts/test_processor.py
"""

import sys
import json
from pathlib import Path

# Allow running from project root without install
sys.path.insert(0, str(Path(__file__).parent.parent))

SAMPLE_TRANSCRIPTS = {
    "1": {
        "label": "Customer intake (new job)",
        "transcript": (
            "Hi, this is Mike Johnson calling. I've got a 2020 Can-Am Outlander 450, "
            "dark green, and it's been making a grinding noise in the front axle for about a week now. "
            "Getting worse. I want to bring it in to get looked at. "
            "I can drop it off this Saturday morning. I need it back by Friday July 4th — "
            "I've got a trip planned that weekend. "
            "My number is 613-555-0123. Do you guys do free estimates?"
        ),
    },
    "2": {
        "label": "Customer update (checking on status)",
        "transcript": (
            "Hey, this is Linda Marsh calling. I dropped off my Polaris Sportsman 570 last week, "
            "just calling to see if you've had a chance to look at it yet. "
            "Any idea on the timeline? I'm also wondering if you found out what was causing "
            "the overheating issue we talked about. If you need to order parts just let me know "
            "and I'll okay it. My number is 613-555-0456."
        ),
    },
    "3": {
        "label": "Parts supplier (ETA + decision)",
        "transcript": (
            "Hey Tristian, it's Dave from Northern ATV Parts. Calling about your order number 4821. "
            "The CV axle for the Outlander is in stock, we've got two of them. "
            "The OEM brake pads are on backorder — ETA is July 2nd. "
            "The aftermarket ones I can get you tomorrow if you want to go that route, about 40 bucks cheaper. "
            "Let me know what you want to do on the brakes. "
            "I'll ship the CV axle today either way. "
            "Give me a call back at 613-555-0789."
        ),
    },
    "4": {
        "label": "Subcontractor (Allan Blain)",
        "transcript": (
            "Hey Tris, it's Allan. Just calling about the two machines you wanted me on. "
            "The yellow Grizzly 700 — I can come in Thursday afternoon to do the differential rebuild. "
            "For that RZR 900 we talked about, I went ahead and decided to go with the OEM clutch kit "
            "instead of the aftermarket one. It's an extra 200 dollars in parts but it's going to last "
            "three times as long. I'll need you to order it, part number RZR-CLT-900-OEM. "
            "I can finish that one by end of next week. Sound good? Call me back."
        ),
    },
    "5": {
        "label": "Internal (message for Steve)",
        "transcript": (
            "Steve, it's Tris. Quick update — that yellow Yamaha Grizzly that came in Monday, "
            "the customer called and he's coming Friday afternoon to pick it up, so that's the priority. "
            "Make sure you check the rear differential before anything else on that one. "
            "Also we're out of 80w90 gear oil — order two quarts when you get a chance. "
            "And the invoice for the Polaris we finished last week still hasn't been paid — "
            "remind me to follow up on that Thursday."
        ),
    },
    "6": {
        "label": "Business (insurance renewal)",
        "transcript": (
            "Hi, this is Sarah from Intact Insurance calling for Tristian Chevier. "
            "I'm calling about your commercial property and liability policy, renewal date is July 15th. "
            "I need to go over a few updates before we can finalize the renewal. "
            "We need to update the replacement value on the shop equipment — "
            "I have it listed at 85 thousand but you mentioned it should be higher. "
            "Also I need to confirm the square footage on the building addition. "
            "Please call me back at 613-555-0199 before end of day Friday so we don't have a lapse."
        ),
    },
    "7": {
        "label": "Custom — type your own transcript",
        "transcript": None,
    },
}


def print_result(data: dict) -> None:
    call_type = data.get("call_type", "unknown")
    labels = {
        "customer_intake": "New Customer",
        "customer_update": "Customer Update",
        "parts_supplier": "Parts/Supplier",
        "subcontractor": "Subcontractor",
        "business": "Business",
        "internal": "Internal",
        "unknown": "Unknown",
    }
    print(f"\n{'─'*60}")
    print(f"  CALL TYPE:  {labels.get(call_type, call_type).upper()}")
    print(f"  SUMMARY:    {data.get('call_summary', 'N/A')}")
    print(f"{'─'*60}")

    if data.get("customer", {}).get("name"):
        c = data["customer"]
        print(f"\nCustomer:  {c.get('name')} | {c.get('phone') or 'no phone'} | returning={c.get('is_returning')}")

    atv = data.get("atv") or {}
    if atv.get("make") or atv.get("model"):
        atv_str = " ".join(filter(None, [atv.get("year"), atv.get("make"), atv.get("model"), atv.get("color")]))
        print(f"ATV:       {atv_str}")
        if atv.get("issue"):
            print(f"Issue:     {atv['issue']}")

    job = data.get("job") or {}
    if job.get("work_requested"):
        print(f"Work:      {job['work_requested']}")
        if job.get("quoted_price"):
            print(f"Quote:     ${job['quoted_price']}")
        if job.get("drop_off_date"):
            print(f"Drop-off:  {job['drop_off_date']}")
        if job.get("estimated_completion"):
            print(f"Est. done: {job['estimated_completion']}")

    if data.get("parts_status"):
        print(f"\nParts status:")
        for p in data["parts_status"]:
            eta = f" | ETA: {p['eta']}" if p.get("eta") else ""
            dec = f" | {p['decision']}" if p.get("decision") else ""
            print(f"  [{p.get('status','?')}] {p.get('part')}{eta}{dec}")

    if data.get("parts_needed"):
        print(f"\nParts to order: {', '.join(data['parts_needed'])}")

    if data.get("decisions_made"):
        print(f"\nDecisions:")
        for d in data["decisions_made"]:
            print(f"  - {d}")

    if data.get("follow_ups"):
        print(f"\nFollow-ups ({len(data['follow_ups'])}):")
        for fu in data["follow_ups"]:
            due = fu.get("due_date") or "TBD"
            t = fu.get("due_time") or ""
            cal = " [CALENDAR INVITE]" if fu.get("due_date") else ""
            print(f"  [{due}{' ' + t if t else ''}] {fu.get('description')} → {fu.get('assignee') or 'owner'}{cal}")

    if data.get("employee_tasks"):
        print(f"\nSteve's tasks:")
        for task in data["employee_tasks"]:
            print(f"  [{task.get('due_date') or 'TBD'}] {task.get('task')}")

    if data.get("notes"):
        print(f"\nNotes: {data['notes']}")

    print()


def main():
    print("\n╔══════════════════════════════════════╗")
    print("║   CHEVS Garage — Pipeline Test Tool  ║")
    print("╚══════════════════════════════════════╝\n")

    print("Choose a test scenario:\n")
    for key, val in SAMPLE_TRANSCRIPTS.items():
        print(f"  {key}. {val['label']}")
    print()

    choice = input("Enter number (1-7): ").strip()
    if choice not in SAMPLE_TRANSCRIPTS:
        print("Invalid choice.")
        sys.exit(1)

    scenario = SAMPLE_TRANSCRIPTS[choice]
    transcript = scenario["transcript"]

    if transcript is None:
        print("\nPaste your transcript (press Enter twice when done):\n")
        lines = []
        while True:
            line = input()
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)
        transcript = "\n".join(lines).strip()
        if not transcript:
            print("Empty transcript.")
            sys.exit(1)

    print(f"\n[TEST] Running: {scenario['label']}")
    print(f"[TEST] Transcript length: {len(transcript)} chars")
    print("[TEST] Sending to Claude for extraction...\n")

    from call_processor.extractor import extract
    data = extract(transcript)

    print_result(data)

    # Show raw JSON option
    show_json = input("Show full JSON? (y/N): ").strip().lower()
    if show_json == "y":
        print(json.dumps(data, indent=2))
        print()

    # Calendar invite test
    follow_ups_with_dates = [fu for fu in (data.get("follow_ups") or []) if fu.get("due_date")]
    parts_with_eta = [p for p in (data.get("parts_status") or []) if p.get("eta")]

    if follow_ups_with_dates or parts_with_eta:
        send_cal = input(f"Send test calendar invite(s) to your email? (y/N): ").strip().lower()
        if send_cal == "y":
            from call_processor import calendar_reminder
            from call_processor.config import NOTIFY_EMAIL
            for fu in follow_ups_with_dates:
                calendar_reminder.send_calendar_reminder(
                    f"CHEVS: {fu.get('description')}",
                    fu["due_date"],
                    fu.get("due_time"),
                    f"From test call: {scenario['label']}\n{fu.get('description')}",
                    NOTIFY_EMAIL,
                )
            for p in parts_with_eta:
                calendar_reminder.send_calendar_reminder(
                    f"CHEVS: Parts arriving — {p.get('part')}",
                    p["eta"],
                    None,
                    f"Parts ETA from test call.\nPart: {p.get('part')}\nStatus: {p.get('status')}",
                    NOTIFY_EMAIL,
                )
    else:
        print("No dated follow-ups found — no calendar invites to send.")

    # Inbox note
    write_note = input("\nWrite to _inbox/ (knowledge base)? (y/N): ").strip().lower()
    if write_note == "y":
        from call_processor.pipeline import _write_inbox_note
        from pathlib import Path
        fake_path = Path(f"test-{choice}-{scenario['label'].replace(' ', '_').replace('(','').replace(')','')}.m4a")
        _write_inbox_note(fake_path, data, transcript)
        print(f"[TEST] Written to _inbox/")

    print("\n[TEST] Done.\n")


if __name__ == "__main__":
    main()
