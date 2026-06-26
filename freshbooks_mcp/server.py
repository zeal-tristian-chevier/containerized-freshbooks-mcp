"""MCP interface — tool definitions and dispatch.

Tool *logic* lives in plain ``handle_*`` functions that take an explicit client,
so they are unit-testable without the MCP runtime. The FastMCP layer is a thin
wrapper registered in ``build_server``.

Security note (§11): all validation happens here, server-side — never trust the
calling agent. ``identity_id`` is always the authenticated user; write tools
require an explicit ``project_id`` and clamp/limit inputs.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

from .config import Config
from .freshbooks_client import FreshBooksClient, FreshBooksError
from . import transformers as T

logger = logging.getLogger(__name__)

MAX_HOURS_PER_DAY = 24


def _today(config: Config) -> date:
    return datetime.now(ZoneInfo(config.timezone)).date()


def _parse_date(value: str | None, config: Config) -> date:
    if not value:
        return _today(config)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid date {value!r}; use YYYY-MM-DD.") from exc


# -- handlers -----------------------------------------------------------------

def handle_check_timesheet(
    client: FreshBooksClient,
    config: Config,
    period: str,
    date_str: str | None = None,
    expected_hours: float | None = None,
    today: date | None = None,
) -> dict:
    anchor = _parse_date(date_str, config)
    today = today or _today(config)
    expected = (
        expected_hours
        if expected_hours is not None
        else config.default_daily_hours
    )
    start, end = T.resolve_range(period, anchor)
    frm, to = T.utc_bounds(start, end, config.timezone)
    entries = client.list_time_entries(frm, to)
    report = T.build_timesheet_report(
        start, end, entries, expected, today, config.timezone
    )
    report["summary"] = _summarize_report(period, report)
    return report


def handle_log_time(
    client: FreshBooksClient,
    config: Config,
    period: str,
    hours: float,
    project_id: int,
    date_str: str | None = None,
    off_days: list[str] | None = None,
    note: str = "Logged via MCP",
    billable: bool = False,
    client_id: int | None = None,
    service_id: int | None = None,
    skip_existing: bool = True,
    dry_run: bool = False,
    today: date | None = None,
) -> dict:
    # --- validation (server-side, never trust the agent) ---
    if project_id is None:
        raise ValueError(
            "project_id is required. Call list_projects and ask the user "
            "which project to log against."
        )
    if hours <= 0 or hours > MAX_HOURS_PER_DAY:
        raise ValueError(f"hours must be between 0 and {MAX_HOURS_PER_DAY}.")
    if billable and client_id is None:
        raise ValueError("billable=true requires a client_id.")

    anchor = _parse_date(date_str, config)
    start, end = T.resolve_range(period, anchor)

    off = {_parse_date(d, config) for d in (off_days or [])}
    targets = [d for d in T.business_days(start, end) if d not in off]

    if len(targets) > config.max_log_days:
        raise ValueError(
            f"Refusing to log {len(targets)} days in one call "
            f"(MAX_LOG_DAYS={config.max_log_days})."
        )

    skipped: list[str] = []
    if skip_existing and targets:
        frm, to = T.utc_bounds(targets[0], targets[-1], config.timezone)
        existing = T.entries_by_day(
            client.list_time_entries(frm, to), config.timezone
        )
        kept = []
        for d in targets:
            if existing.get(d, 0) > 0:
                skipped.append(d.isoformat())
            else:
                kept.append(d)
        targets = kept

    plan = [d.isoformat() for d in targets]
    if dry_run:
        return {
            "dry_run": True,
            "would_log": plan,
            "hours_each": hours,
            "skipped_existing": skipped,
            "off_days": sorted(d.isoformat() for d in off),
            "project_id": project_id,
        }

    duration = T.hours_to_seconds(hours)
    created: list[dict] = []
    errors: list[dict] = []
    for d in targets:
        started = T.local_datetime(d, config.default_start_time, config.timezone)
        try:
            entry = client.create_time_entry(
                started,
                duration,
                project_id=project_id,
                note=note,
                client_id=client_id,
                service_id=service_id,
                billable=billable,
            )
            created.append({"date": d.isoformat(), "hours": hours, "id": entry.id})
        except Exception as exc:  # surface partial failure clearly
            errors.append({"date": d.isoformat(), "error": str(exc)})

    return {
        "dry_run": False,
        "created": created,
        "skipped_existing": skipped,
        "off_days": sorted(d.isoformat() for d in off),
        "errors": errors,
        "summary": _summarize_log(created, skipped, errors, hours),
    }


def handle_list_projects(
    client: FreshBooksClient, active_only: bool = True, query: str | None = None
) -> dict:
    projects = client.list_projects(active_only=active_only)
    items = [
        {"project_id": p.id, "title": p.title, "client_id": p.client_id,
         "active": p.active}
        for p in projects
    ]
    if query:
        q = query.lower()
        items = [p for p in items if q in (p["title"] or "").lower()]
    return {"projects": items}


def handle_list_clients(client: FreshBooksClient) -> dict:
    return {"clients": client.list_clients()}


def handle_list_services(client: FreshBooksClient) -> dict:
    return {"services": client.list_services()}


# -- invoice handlers ---------------------------------------------------------

def _amount(field) -> float:
    """Extract a float from a FreshBooks amount field (dict or string)."""
    if isinstance(field, dict):
        return float(field.get("amount", 0) or 0)
    return float(field or 0)


def handle_list_invoices(
    client: FreshBooksClient,
    date_min: str | None = None,
    date_max: str | None = None,
    status: str | None = None,
    client_id: int | None = None,
) -> dict:
    invoices = client.list_invoices(date_min, date_max, status, client_id)
    items = [
        {
            "id": inv.get("id"),
            "invoice_number": inv.get("invoice_number") or inv.get("invoicenumber"),
            "client_id": inv.get("customerid"),
            "status": inv.get("v3_status") or inv.get("payment_status"),
            "amount": _amount(inv.get("amount")),
            "outstanding": _amount(inv.get("outstanding")),
            "date": inv.get("date") or inv.get("create_date"),
            "due_date": inv.get("due_date"),
            "currency": inv.get("currency_code"),
        }
        for inv in invoices
    ]
    return {
        "invoices": items,
        "count": len(items),
        "total": round(sum(i["amount"] for i in items), 2),
        "outstanding": round(sum(i["outstanding"] for i in items), 2),
    }


def handle_create_invoice(
    client: FreshBooksClient,
    client_id: int,
    lines: list[dict],
    due_offset_days: int = 30,
    notes: str = "",
    currency_code: str = "USD",
) -> dict:
    inv = client.create_invoice(client_id, lines, due_offset_days, notes, currency_code)
    return {
        "id": inv.get("id"),
        "invoice_number": inv.get("invoice_number") or inv.get("invoicenumber"),
        "status": inv.get("v3_status"),
        "amount": _amount(inv.get("amount")),
        "due_date": inv.get("due_date"),
        "created": inv.get("create_date"),
    }


def handle_send_invoice(client: FreshBooksClient, invoice_id: int) -> dict:
    inv = client.send_invoice(invoice_id)
    return {
        "id": inv.get("id"),
        "invoice_number": inv.get("invoice_number") or inv.get("invoicenumber"),
        "status": inv.get("v3_status"),
        "sent": True,
    }


# -- payment handlers ---------------------------------------------------------

def handle_list_payments(
    client: FreshBooksClient,
    date_min: str | None = None,
    date_max: str | None = None,
    client_id: int | None = None,
) -> dict:
    payments = client.list_payments(date_min, date_max, client_id)
    items = [
        {
            "id": p.get("id"),
            "invoice_id": p.get("invoiceid"),
            "client_id": p.get("clientid"),
            "amount": _amount(p.get("amount")),
            "date": p.get("date"),
            "type": p.get("type"),
            "note": p.get("note"),
        }
        for p in payments
    ]
    total = round(sum(i["amount"] for i in items), 2)
    return {"payments": items, "count": len(items), "total": total}


def handle_get_income_summary(
    client: FreshBooksClient,
    date_min: str | None = None,
    date_max: str | None = None,
) -> dict:
    payments = client.list_payments(date_min, date_max)
    total = 0.0
    by_month: dict[str, float] = {}
    for p in payments:
        amt = _amount(p.get("amount"))
        total += amt
        date_str = str(p.get("date", ""))
        if len(date_str) >= 7:
            month = date_str[:7]
            by_month[month] = round(by_month.get(month, 0.0) + amt, 2)
    return {
        "date_min": date_min,
        "date_max": date_max,
        "total_received": round(total, 2),
        "payment_count": len(payments),
        "by_month": dict(sorted(by_month.items())),
    }


# -- expense handlers ---------------------------------------------------------

def handle_list_expenses(
    client: FreshBooksClient,
    date_min: str | None = None,
    date_max: str | None = None,
    client_id: int | None = None,
) -> dict:
    expenses = client.list_expenses(date_min, date_max, client_id)
    items = [
        {
            "id": e.get("id"),
            "vendor": e.get("vendor"),
            "amount": _amount(e.get("amount")),
            "date": e.get("date"),
            "category": e.get("category", {}).get("name") if isinstance(e.get("category"), dict) else None,
            "notes": e.get("notes"),
            "client_id": e.get("clientid"),
        }
        for e in expenses
    ]
    return {
        "expenses": items,
        "count": len(items),
        "total": round(sum(i["amount"] for i in items), 2),
    }


def handle_get_profit_loss(
    client: FreshBooksClient,
    date_min: str | None = None,
    date_max: str | None = None,
) -> dict:
    payments = client.list_payments(date_min, date_max)
    expenses = client.list_expenses(date_min, date_max)
    income = round(sum(_amount(p.get("amount")) for p in payments), 2)
    expense_total = round(sum(_amount(e.get("amount")) for e in expenses), 2)
    return {
        "date_min": date_min,
        "date_max": date_max,
        "income": income,
        "expenses": expense_total,
        "net": round(income - expense_total, 2),
        "payment_count": len(payments),
        "expense_count": len(expenses),
    }


# -- invoice detail / lifecycle handlers --------------------------------------

def handle_get_invoice(client: FreshBooksClient, invoice_id: int) -> dict:
    inv = client.get_invoice(invoice_id)
    return {
        "id": inv.get("id"),
        "invoice_number": inv.get("invoice_number") or inv.get("invoicenumber"),
        "client_id": inv.get("customerid"),
        "status": inv.get("v3_status") or inv.get("payment_status"),
        "amount": _amount(inv.get("amount")),
        "outstanding": _amount(inv.get("outstanding")),
        "date": inv.get("date") or inv.get("create_date"),
        "due_date": inv.get("due_date"),
        "currency": inv.get("currency_code"),
        "notes": inv.get("notes"),
        "lines": [
            {
                "name": ln.get("name"),
                "description": ln.get("description"),
                "qty": ln.get("qty"),
                "unit_cost": _amount(ln.get("unit_cost")),
                "amount": _amount(ln.get("amount")),
            }
            for ln in (inv.get("lines") or [])
        ],
    }


def handle_void_invoice(client: FreshBooksClient, invoice_id: int) -> dict:
    inv = client.void_invoice(invoice_id)
    return {
        "id": inv.get("id") or invoice_id,
        "voided": True,
        "status": inv.get("v3_status", "deleted"),
    }


# -- payment management handlers ----------------------------------------------

def handle_apply_payment(
    client: FreshBooksClient,
    invoice_id: int,
    amount: float,
    date: str,
    payment_type: str = "Check",
    note: str = "",
) -> dict:
    payment = client.apply_payment(invoice_id, amount, date, payment_type, note)
    return {
        "id": payment.get("id"),
        "invoice_id": invoice_id,
        "amount": _amount(payment.get("amount")),
        "date": payment.get("date"),
        "type": payment.get("type"),
    }


def handle_delete_payment(client: FreshBooksClient, payment_id: int) -> dict:
    client.delete_payment(payment_id)
    return {"payment_id": payment_id, "deleted": True}


# -- expense management handlers ----------------------------------------------

def handle_list_expense_categories(client: FreshBooksClient) -> dict:
    cats = client.list_expense_categories()
    return {
        "categories": [
            {
                "id": c.get("id"),
                "name": c.get("name") or c.get("categoryname") or c.get("category_name"),
                "parent_id": c.get("parentid") or c.get("parent_id"),
            }
            for c in cats
        ],
        "count": len(cats),
    }


def handle_create_expense(
    client: FreshBooksClient,
    amount: float,
    category_id: int,
    date: str,
    vendor: str = "",
    notes: str = "",
    client_id: int | None = None,
) -> dict:
    exp = client.create_expense(amount, category_id, date, vendor, notes, client_id)
    return {
        "id": exp.get("id"),
        "amount": _amount(exp.get("amount")),
        "vendor": exp.get("vendor"),
        "date": exp.get("date"),
        "notes": exp.get("notes"),
    }


# -- estimate handlers --------------------------------------------------------

def handle_list_estimates(
    client: FreshBooksClient,
    date_min: str | None = None,
    date_max: str | None = None,
    client_id: int | None = None,
    status: str | None = None,
) -> dict:
    estimates = client.list_estimates(date_min, date_max, client_id, status)
    items = [
        {
            "id": e.get("id"),
            "estimate_number": e.get("estimate_number") or e.get("estimatenumber"),
            "client_id": e.get("customerid"),
            "status": e.get("v3_status") or e.get("estimate_status"),
            "amount": _amount(e.get("amount")),
            "date": e.get("date") or e.get("create_date"),
        }
        for e in estimates
    ]
    return {
        "estimates": items,
        "count": len(items),
        "total": round(sum(i["amount"] for i in items), 2),
    }


# -- items / catalog handlers -------------------------------------------------

def handle_list_items(client: FreshBooksClient) -> dict:
    items = client.list_items()
    return {
        "items": [
            {
                "id": i.get("id"),
                "name": i.get("name"),
                "description": i.get("description"),
                "unit_cost": _amount(i.get("unit_cost")),
                "tax_id": i.get("tax1"),
            }
            for i in items
        ],
        "count": len(items),
    }


def handle_create_item(
    client: FreshBooksClient,
    name: str,
    unit_cost: float,
    description: str = "",
    tax_id: int | None = None,
) -> dict:
    item = client.create_item(name, unit_cost, description, tax_id)
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "unit_cost": _amount(item.get("unit_cost")),
        "description": item.get("description"),
    }


# -- tax handlers -------------------------------------------------------------

def handle_list_taxes(client: FreshBooksClient) -> dict:
    taxes = client.list_taxes()
    return {
        "taxes": [
            {"id": t.get("id"), "name": t.get("name"), "rate": t.get("amount"), "compound": t.get("compound")}
            for t in taxes
        ],
        "count": len(taxes),
    }


def handle_create_tax(client: FreshBooksClient, name: str, amount: float, compound: bool = False) -> dict:
    tax = client.create_tax(name, amount, compound)
    return {"id": tax.get("id"), "name": tax.get("name"), "rate": tax.get("amount")}


# -- estimate create handler --------------------------------------------------

def handle_create_estimate(
    client: FreshBooksClient,
    client_id: int,
    lines: list[dict],
    notes: str = "",
    currency_code: str = "USD",
) -> dict:
    formatted = [
        {
            "type": 0,
            "name": ln.get("name", ""),
            "description": ln.get("description", ""),
            "qty": int(ln.get("qty", 1)),
            "unit_cost": {"amount": str(float(ln.get("unit_cost", 0))), "code": currency_code},
        }
        for ln in lines
    ]
    est = client.create_estimate(client_id, formatted, notes, currency_code)
    return {
        "id": est.get("id"),
        "estimate_number": est.get("estimate_number") or est.get("estimatenumber"),
        "status": est.get("v3_status"),
        "amount": _amount(est.get("amount")),
        "created": est.get("create_date"),
    }


# -- invoice update handler ---------------------------------------------------

def handle_update_invoice(
    client: FreshBooksClient,
    invoice_id: int,
    notes: str | None = None,
    due_offset_days: int | None = None,
    po_number: str | None = None,
) -> dict:
    fields: dict = {}
    if notes is not None:
        fields["notes"] = notes
    if due_offset_days is not None:
        fields["due_offset_days"] = due_offset_days
    if po_number is not None:
        fields["po_number"] = po_number
    inv = client.update_invoice(invoice_id, fields)
    return {
        "id": inv.get("id") or invoice_id,
        "invoice_number": inv.get("invoice_number") or inv.get("invoicenumber"),
        "status": inv.get("v3_status"),
        "due_date": inv.get("due_date"),
        "notes": inv.get("notes"),
    }


# -- staff handler ------------------------------------------------------------

def handle_list_staff(client: FreshBooksClient) -> dict:
    staff = client.list_staff()
    return {
        "staff": [
            {
                "id": s.get("id"),
                "name": f"{s.get('fname', '')} {s.get('lname', '')}".strip(),
                "email": s.get("email"),
                "role": s.get("role"),
            }
            for s in staff
        ],
        "count": len(staff),
    }


# -- recurring invoices handler -----------------------------------------------

def handle_list_recurring_invoices(client: FreshBooksClient) -> dict:
    invoices = client.list_recurring_invoices()
    return {
        "recurring_invoices": [
            {
                "id": inv.get("id"),
                "invoice_number": inv.get("invoice_number") or inv.get("invoicenumber"),
                "client_id": inv.get("customerid"),
                "amount": _amount(inv.get("amount")),
                "status": inv.get("v3_status"),
            }
            for inv in invoices
        ],
        "count": len(invoices),
    }


# -- accounts aging handler ---------------------------------------------------

def handle_get_accounts_aging(client: FreshBooksClient) -> dict:
    from datetime import date as date_type

    # Try the native report endpoint first; fall back to computing from invoices.
    try:
        result = client.get_accounts_aging()
        aging_list = result.get("aging", [])
        if aging_list:
            return {
                "aging": [
                    {
                        "client": e.get("client_name") or e.get("organization"),
                        "current": _amount(e.get("current")),
                        "1_30_days": _amount(e.get("1-30")),
                        "31_60_days": _amount(e.get("31-60")),
                        "61_90_days": _amount(e.get("61-90")),
                        "over_90_days": _amount(e.get("90+")),
                        "total": _amount(e.get("total")),
                    }
                    for e in aging_list
                ],
                "total_outstanding": round(sum(_amount(e.get("total")) for e in aging_list), 2),
                "source": "freshbooks_report",
            }
    except FreshBooksError:
        pass

    # Compute aging from outstanding invoices.
    today = date_type.today()
    invoices = client.list_invoices()
    by_client: dict[int, dict] = {}
    for inv in invoices:
        outstanding = _amount(inv.get("outstanding"))
        if outstanding <= 0:
            continue
        cid = inv.get("customerid") or 0
        due_raw = inv.get("due_date") or inv.get("date") or today.isoformat()
        try:
            due = date_type.fromisoformat(str(due_raw))
        except (ValueError, TypeError):
            due = today
        days_over = (today - due).days
        if cid not in by_client:
            by_client[cid] = {"client_id": cid, "c": 0.0, "d30": 0.0, "d60": 0.0, "d90": 0.0, "d90p": 0.0}
        bucket = by_client[cid]
        if days_over <= 0:
            bucket["c"] += outstanding
        elif days_over <= 30:
            bucket["d30"] += outstanding
        elif days_over <= 60:
            bucket["d60"] += outstanding
        elif days_over <= 90:
            bucket["d90"] += outstanding
        else:
            bucket["d90p"] += outstanding

    aging = [
        {
            "client_id": v["client_id"],
            "current": round(v["c"], 2),
            "1_30_days": round(v["d30"], 2),
            "31_60_days": round(v["d60"], 2),
            "61_90_days": round(v["d90"], 2),
            "over_90_days": round(v["d90p"], 2),
            "total": round(v["c"] + v["d30"] + v["d60"] + v["d90"] + v["d90p"], 2),
        }
        for v in by_client.values()
    ]
    aging.sort(key=lambda x: x["total"], reverse=True)
    return {
        "aging": aging,
        "total_outstanding": round(sum(a["total"] for a in aging), 2),
        "source": "computed_from_invoices",
    }


# -- client management handlers -----------------------------------------------

def handle_create_client(
    client: FreshBooksClient,
    fname: str,
    lname: str,
    email: str = "",
    organization: str = "",
    phone: str = "",
) -> dict:
    result = client.create_client(fname, lname, email, organization, phone)
    return {
        "id": result.get("id"),
        "name": f"{fname} {lname}".strip(),
        "email": email,
        "organization": organization,
    }


# -- summaries ----------------------------------------------------------------

def _summarize_report(period: str, report: dict) -> str:
    missing = report["missing_days"]
    under = report["under_logged_days"]
    parts = [
        f"{period.capitalize()} {report['range']['start']}–"
        f"{report['range']['end']}: {report['total_hours']}h logged."
    ]
    if missing:
        parts.append(f"Missing: {', '.join(missing)}.")
    if under:
        parts.append(f"Under-logged: {', '.join(under)}.")
    if not missing and not under:
        parts.append("All weekdays accounted for.")
    return " ".join(parts)


def _summarize_log(created, skipped, errors, hours) -> str:
    parts = [f"Logged {hours}h on {len(created)} day(s)."]
    if skipped:
        parts.append(f"Skipped {len(skipped)} already-logged day(s).")
    if errors:
        parts.append(f"{len(errors)} failed.")
    return " ".join(parts)


# -- MCP wiring ---------------------------------------------------------------

def build_server(config: Config, client: FreshBooksClient):
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("freshbooks-timesheet")

    @mcp.tool()
    def check_timesheet(
        period: str,
        date: str | None = None,
        expected_hours: float | None = None,
    ) -> dict:
        """Report logged/missing time for a day, week, or month (M–F).

        period: "day" | "week" | "month". date: anchor YYYY-MM-DD (default today).
        Lists days missing an entry and days logged under expected_hours.
        """
        return handle_check_timesheet(client, config, period, date, expected_hours)

    @mcp.tool()
    def log_time(
        period: str,
        hours: float,
        project_id: int,
        date: str | None = None,
        off_days: list[str] | None = None,
        note: str = "Logged via MCP",
        billable: bool = False,
        client_id: int | None = None,
        service_id: int | None = None,
        skip_existing: bool = True,
        dry_run: bool = False,
    ) -> dict:
        """Log `hours` per weekday (M–F) for a period against a project.

        project_id is REQUIRED — if the user hasn't named a project, call
        list_projects first and ask which to use. Use off_days (YYYY-MM-DD list)
        for PTO/holidays. Set dry_run=true to preview without writing. Skips days
        that already have entries unless skip_existing=false. Logs as the
        authenticated user only.
        """
        return handle_log_time(
            client, config, period, hours, project_id, date, off_days, note,
            billable, client_id, service_id, skip_existing, dry_run,
        )

    @mcp.tool()
    def list_projects(active_only: bool = True, query: str | None = None) -> dict:
        """List the user's projects (id + title) to choose for logging time."""
        return handle_list_projects(client, active_only, query)

    @mcp.tool()
    def list_clients() -> dict:
        """List clients (needed when logging billable time)."""
        return handle_list_clients(client)

    @mcp.tool()
    def list_services() -> dict:
        """List services (optional; sets the billing rate on an entry)."""
        return handle_list_services(client)

    # -- invoices -------------------------------------------------------------

    @mcp.tool()
    def list_invoices(
        date_min: str | None = None,
        date_max: str | None = None,
        status: str | None = None,
        client_id: int | None = None,
    ) -> dict:
        """List invoices with optional filters.

        date_min / date_max: YYYY-MM-DD. status: paid | unpaid | partial | draft | sent.
        Returns each invoice's amount, outstanding balance, due date, and status.
        """
        return handle_list_invoices(client, date_min, date_max, status, client_id)

    @mcp.tool()
    def create_invoice(
        client_id: int,
        lines: list[dict],
        due_offset_days: int = 30,
        notes: str = "",
        currency_code: str = "USD",
    ) -> dict:
        """Create a new invoice for a client.

        lines: list of dicts with keys: name (str), description (str), qty (int),
        unit_cost (float). Example: [{"name": "Consulting", "qty": 10, "unit_cost": 150.0}]
        due_offset_days: days from today until due (default 30).
        Call list_clients first to get client_id.
        """
        formatted_lines = [
            {
                "type": 0,
                "name": ln.get("name", ""),
                "description": ln.get("description", ""),
                "qty": int(ln.get("qty", 1)),
                "unit_cost": {"amount": str(float(ln.get("unit_cost", 0))), "code": currency_code},
            }
            for ln in lines
        ]
        return handle_create_invoice(client, client_id, formatted_lines, due_offset_days, notes, currency_code)

    @mcp.tool()
    def send_invoice(invoice_id: int) -> dict:
        """Email an invoice to the client. Call list_invoices to get the invoice_id."""
        return handle_send_invoice(client, invoice_id)

    # -- invoice detail / lifecycle -------------------------------------------

    @mcp.tool()
    def get_invoice(invoice_id: int) -> dict:
        """Get full details of a single invoice including all line items.
        Call list_invoices to get the invoice_id."""
        return handle_get_invoice(client, invoice_id)

    @mcp.tool()
    def void_invoice(invoice_id: int) -> dict:
        """Void (delete) an invoice. This is irreversible.
        Call list_invoices to get the invoice_id."""
        return handle_void_invoice(client, invoice_id)

    # -- payments -------------------------------------------------------------

    @mcp.tool()
    def list_payments(
        date_min: str | None = None,
        date_max: str | None = None,
        client_id: int | None = None,
    ) -> dict:
        """List payments received. date_min / date_max: YYYY-MM-DD.
        Returns each payment's amount, date, type, and linked invoice."""
        return handle_list_payments(client, date_min, date_max, client_id)

    @mcp.tool()
    def apply_payment(
        invoice_id: int,
        amount: float,
        date: str,
        payment_type: str = "Check",
        note: str = "",
    ) -> dict:
        """Record a payment against an invoice. Marks it paid (fully or partially).
        payment_type: Check | Credit | Cash | ACH | PayPal | Stripe | Other.
        date: YYYY-MM-DD. Call list_invoices to get invoice_id."""
        return handle_apply_payment(client, invoice_id, amount, date, payment_type, note)

    @mcp.tool()
    def delete_payment(payment_id: int) -> dict:
        """Void/delete a payment record. Call list_payments to get the payment_id."""
        return handle_delete_payment(client, payment_id)

    @mcp.tool()
    def get_income_summary(
        date_min: str | None = None,
        date_max: str | None = None,
    ) -> dict:
        """Total revenue received in a date range, broken down by month.
        date_min / date_max: YYYY-MM-DD (e.g. 2025-01-01 / 2025-12-31)."""
        return handle_get_income_summary(client, date_min, date_max)

    # -- expenses -------------------------------------------------------------

    @mcp.tool()
    def list_expense_categories() -> dict:
        """List expense category IDs (needed when creating an expense).
        FreshBooks does not return category names via the API — use the IDs
        and the parent_id hierarchy to identify the right category."""
        return handle_list_expense_categories(client)

    @mcp.tool()
    def create_expense(
        amount: float,
        category_id: int,
        date: str,
        vendor: str = "",
        notes: str = "",
        client_id: int | None = None,
    ) -> dict:
        """Log a new expense. Call list_expense_categories first to get category_id.
        date: YYYY-MM-DD. amount in your account's default currency."""
        return handle_create_expense(client, amount, category_id, date, vendor, notes, client_id)

    @mcp.tool()
    def list_expenses(
        date_min: str | None = None,
        date_max: str | None = None,
        client_id: int | None = None,
    ) -> dict:
        """List expenses. date_min / date_max: YYYY-MM-DD.
        Returns vendor, amount, category, and date for each expense."""
        return handle_list_expenses(client, date_min, date_max, client_id)

    @mcp.tool()
    def get_profit_loss(
        date_min: str | None = None,
        date_max: str | None = None,
    ) -> dict:
        """Net profit = total payments received minus total expenses for the period.
        date_min / date_max: YYYY-MM-DD."""
        return handle_get_profit_loss(client, date_min, date_max)

    # -- items / catalog ------------------------------------------------------

    @mcp.tool()
    def list_items() -> dict:
        """List your product/service catalog (reusable line items for invoices)."""
        return handle_list_items(client)

    @mcp.tool()
    def create_item(
        name: str,
        unit_cost: float,
        description: str = "",
        tax_id: int | None = None,
    ) -> dict:
        """Add a product or service to your catalog.
        Call list_taxes to get tax_id if you want tax applied automatically."""
        return handle_create_item(client, name, unit_cost, description, tax_id)

    # -- taxes ----------------------------------------------------------------

    @mcp.tool()
    def list_taxes() -> dict:
        """List configured tax rates (GST, HST, VAT, etc.) and their IDs."""
        return handle_list_taxes(client)

    @mcp.tool()
    def create_tax(name: str, amount: float, compound: bool = False) -> dict:
        """Create a tax rate. amount is the percentage (e.g. 13.0 for 13%).
        compound: true if this tax applies on top of another tax."""
        return handle_create_tax(client, name, amount, compound)

    # -- estimates ------------------------------------------------------------

    @mcp.tool()
    def create_estimate(
        client_id: int,
        lines: list[dict],
        notes: str = "",
        currency_code: str = "USD",
    ) -> dict:
        """Create a quote/proposal for a client.
        lines: list of dicts with name, description, qty, unit_cost.
        Call list_clients for client_id."""
        return handle_create_estimate(client, client_id, lines, notes, currency_code)

    @mcp.tool()
    def list_estimates(
        date_min: str | None = None,
        date_max: str | None = None,
        client_id: int | None = None,
        status: str | None = None,
    ) -> dict:
        """List estimates/quotes. status: draft | sent | viewed | accepted | declined."""
        return handle_list_estimates(client, date_min, date_max, client_id, status)

    # -- invoice update -------------------------------------------------------

    @mcp.tool()
    def update_invoice(
        invoice_id: int,
        notes: str | None = None,
        due_offset_days: int | None = None,
        po_number: str | None = None,
    ) -> dict:
        """Edit fields on an existing invoice. Only provided fields are updated.
        Call list_invoices to get invoice_id."""
        return handle_update_invoice(client, invoice_id, notes, due_offset_days, po_number)

    # -- staff ----------------------------------------------------------------

    @mcp.tool()
    def list_staff() -> dict:
        """List team members on your FreshBooks account."""
        return handle_list_staff(client)

    # -- recurring invoices ---------------------------------------------------

    @mcp.tool()
    def list_recurring_invoices() -> dict:
        """List recurring/auto-billing invoice templates."""
        return handle_list_recurring_invoices(client)

    # -- accounts aging -------------------------------------------------------

    @mcp.tool()
    def get_accounts_aging() -> dict:
        """Accounts receivable aging report — who owes you money and how overdue.
        Breaks outstanding balances into current, 1-30, 31-60, 61-90, and 90+ day buckets."""
        return handle_get_accounts_aging(client)

    # -- client management ----------------------------------------------------

    @mcp.tool()
    def create_client(
        fname: str,
        lname: str,
        email: str = "",
        organization: str = "",
        phone: str = "",
    ) -> dict:
        """Create a new client. fname and lname are required."""
        return handle_create_client(client, fname, lname, email, organization, phone)

    return mcp


def main() -> None:  # pragma: no cover - process entrypoint
    logging.basicConfig(level=logging.INFO)
    from .auth_manager import AuthManager

    config = Config.load()
    auth = AuthManager(config)
    client = FreshBooksClient(config, auth)
    server = build_server(config, client)
    server.run()


if __name__ == "__main__":  # pragma: no cover
    main()
