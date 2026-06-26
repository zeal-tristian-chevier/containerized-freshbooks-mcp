import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from freshbooks_mcp.config import Config
from freshbooks_mcp.auth_manager import AuthManager
from freshbooks_mcp.freshbooks_client import FreshBooksClient


def get_fb_client() -> FreshBooksClient:
    config = Config.load()
    auth = AuthManager(config)
    return FreshBooksClient(config, auth)


def find_or_create_client(fb: FreshBooksClient, customer: dict) -> dict:
    name = (customer.get("name") or "").strip()
    if not name:
        return {}

    clients = fb.list_clients()
    name_lower = name.lower()
    for c in clients:
        full = f"{c.get('fname', '')} {c.get('lname', '')}".strip().lower()
        org = (c.get("organization") or "").lower()
        phone = (c.get("home_phone") or c.get("bus_phone") or "").replace(" ", "").replace("-", "")
        call_phone = (customer.get("phone") or "").replace(" ", "").replace("-", "")
        if name_lower in full or name_lower in org:
            print(f"[ACTIONS] Found existing client: {full} (id={c.get('id')})")
            return c
        if call_phone and phone and call_phone[-10:] == phone[-10:]:
            print(f"[ACTIONS] Found existing client by phone: {full} (id={c.get('id')})")
            return c

    parts = name.split(None, 1)
    fname = parts[0]
    lname = parts[1] if len(parts) > 1 else ""
    result = fb.create_client(
        fname=fname,
        lname=lname,
        email=customer.get("email") or "",
        organization="",
        phone=customer.get("phone") or "",
    )
    print(f"[ACTIONS] Created new client: {name} (id={result.get('id')})")
    return result


def create_estimate(fb: FreshBooksClient, client_id: int, job: dict, atv: dict, notes: str | None) -> dict:
    atv_str = " ".join(filter(None, [atv.get("year"), atv.get("make"), atv.get("model")])).strip()
    description = "\n".join(filter(None, [atv_str, notes])).strip()
    lines = [
        {
            "type": 0,
            "name": (job.get("work_requested") or "ATV Repair")[:100],
            "description": description,
            "qty": 1,
            "unit_cost": {"amount": str(float(job.get("quoted_price") or 0)), "code": "USD"},
        }
    ]
    result = fb.create_estimate(client_id, lines, notes or "", "USD")
    print(f"[ACTIONS] Created estimate id={result.get('id')}")
    return result
