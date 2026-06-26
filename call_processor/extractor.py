import subprocess
import json
import re
import sys
from datetime import date

PROMPT_TEMPLATE = """\
You are processing a phone call transcript from CHEVS Garage, an ATV repair shop.
Extract structured information and return ONLY a valid JSON object — no markdown, no explanation.

Today's date: {today}

STEP 1 — Classify the call type:
- customer_intake: a customer calling about a new repair or service job
- customer_update: an existing customer checking on status, asking questions, or providing new info
- parts_supplier: a call about parts — ordering, availability, ETA, pricing, or a decision on parts
- subcontractor: a call with Allan Blain or another subcontractor about labour or work
- business: administrative — vendor, accounting, insurance, or other non-repair business
- internal: a call with Steve or another employee about shop operations
- unknown: cannot determine

STEP 2 — Extract all relevant fields. Return null for fields that do not apply.

JSON schema to return:
{{
  "call_type": "customer_intake | customer_update | parts_supplier | subcontractor | business | internal | unknown",
  "call_summary": "one sentence describing what this call was about",

  "customer": {{
    "name": "string or null",
    "phone": "string or null",
    "email": "string or null",
    "is_returning": true/false
  }},

  "atv": {{
    "year": "string or null",
    "make": "string or null",
    "model": "string or null",
    "color": "string or null",
    "issue": "string or null"
  }},

  "job": {{
    "work_requested": "string or null",
    "quoted_price": number or null,
    "drop_off_date": "YYYY-MM-DD or null",
    "estimated_completion": "YYYY-MM-DD or null"
  }},

  "parts_needed": ["list of parts to order — from customer calls"],

  "parts_status": [
    {{
      "part": "part name",
      "status": "ordered | in_stock | arriving | waiting | backordered | other",
      "eta": "YYYY-MM-DD or null",
      "supplier": "string or null",
      "decision": "any decision made about this part"
    }}
  ],

  "decisions_made": ["list of specific decisions or commitments made during this call"],

  "follow_ups": [
    {{
      "type": "call_customer | call_supplier | order_parts | notify_ready | check_parts | invoice_due | follow_up_call | other",
      "description": "what needs to happen",
      "due_date": "YYYY-MM-DD or null — convert relative dates like 'Thursday' or 'next week' to absolute dates",
      "due_time": "HH:MM in 24h format or null",
      "assignee": "owner | steve | null",
      "calendar_event": true
    }}
  ],

  "employee_tasks": [
    {{
      "assignee": "steve | owner",
      "task": "what they need to do",
      "due_date": "YYYY-MM-DD or null"
    }}
  ],

  "notes": "anything else important from the call"
}}

Rules:
- Set calendar_event to true on any follow_up that has a due_date — these become calendar invites.
- Convert ALL relative dates (tomorrow, Thursday, next week, end of month) to YYYY-MM-DD using today's date.
- For parts_status: include any parts discussed, their ETA if given, and any decision (e.g. "decided to order OEM instead of aftermarket").
- For decisions_made: capture any commitment, agreement, or decision from the call, even if it doesn't fit other fields.
- customer/atv/job fields are primarily for customer calls — set to null for parts/business/internal calls unless clearly relevant.

Transcript:
{transcript}"""


def _run_claude(prompt: str) -> str:
    cmd = ["claude", "-p", prompt]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
            stdin=subprocess.DEVNULL,
        )
        return result.stdout.strip()
    except FileNotFoundError:
        # Fallback: try with shell=True on Windows
        result = subprocess.run(
            f'claude -p "{prompt.replace(chr(34), chr(39))}"',
            shell=True,
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
        )
        return result.stdout.strip()


def _parse_json(raw: str) -> dict:
    # Strip markdown code fences if present
    raw = re.sub(r"^```(?:json)?\s*\n?", "", raw.strip())
    raw = re.sub(r"\n?```\s*$", "", raw)
    return json.loads(raw)


def extract(transcript: str) -> dict:
    today = date.today().isoformat()
    prompt = PROMPT_TEMPLATE.format(today=today, transcript=transcript)
    print("[EXTRACTOR] Sending transcript to Claude...")
    raw = _run_claude(prompt)
    data = _parse_json(raw)
    call_type = data.get("call_type", "unknown")
    summary = data.get("call_summary") or data.get("customer", {}).get("name") or "unknown"
    print(f"[EXTRACTOR] call_type={call_type} | {summary}")
    return data
