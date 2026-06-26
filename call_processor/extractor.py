import subprocess
import json
import re
import sys
from datetime import date

PROMPT_TEMPLATE = """\
You are processing a phone call transcript from CHEVS Garage, an ATV repair shop.
Extract structured information and return ONLY a valid JSON object — no markdown, no explanation.

Today's date: {today}

JSON schema to return:
{{
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
    "issue": "string describing problem"
  }},
  "job": {{
    "work_requested": "string summarising work to be done",
    "quoted_price": number or null,
    "drop_off_date": "YYYY-MM-DD or null",
    "estimated_completion": "YYYY-MM-DD or null"
  }},
  "parts_needed": ["list of parts to order"],
  "follow_ups": [
    {{
      "type": "call_customer | order_parts | notify_ready | invoice_due | other",
      "description": "what needs to happen",
      "due_date": "YYYY-MM-DD or null",
      "assignee": "owner | steve | null"
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
    print(f"[EXTRACTOR] Got structured data for: {data.get('customer', {}).get('name', 'unknown')}")
    return data
