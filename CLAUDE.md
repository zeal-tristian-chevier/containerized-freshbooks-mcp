# CHEVS Garage — Operating Guide for Claude

This is the living memory and operating guide for CHEVS Garage. Read it before doing any work.
It covers what the business does, where knowledge lives, what tools are available, and how to
keep the knowledge base current.

---

## About the Business

**CHEVS Garage** — ATV repair and service shop.
- Owner: Tristian Chevier (tmchevierbusiness@gmail.com)
- Employee: Steve (handles shop floor work)
- Main subcontractor: Allan Blain (ATV repair labor, ~$44K/year)
- Timezone: America/Toronto

---

## Knowledge Base

The vault lives in `knowledge-base/`. Notes have frontmatter (title, source, date, status).
Three working areas:

- `knowledge-base/` — trusted, approved notes
- `_inbox/` — raw drops and call transcripts to be processed
- `_proposed/` — AI-drafted additions awaiting Tristian's approval

**Never write directly to `knowledge-base/`. Always draft to `_proposed/` first.**

Status labels: `extracted` / `inferred` / `verified` / `deprecated`

### Note files

| File | What it covers |
|---|---|
| `snapshot.md` | Business overview, current state |
| `customers.md` | Client profiles, preferences, history |
| `services.md` | What the shop does, pricing patterns |
| `people.md` | Key contacts — staff, subcontractors, suppliers |
| `decisions.md` | Past decisions and why they were made |
| `open-loops.md` | Pending items, waiting-on, unresolved threads |
| `faq.md` | Common customer questions and standard answers |

---

## Tools Available

### FreshBooks MCP (29 tools)
Use these to query and update FreshBooks directly:
- Clients: `list_clients`, `create_client`
- Invoices: `list_invoices`, `get_invoice`, `create_invoice`, `update_invoice`, `send_invoice`, `void_invoice`
- Payments: `list_payments`, `apply_payment`, `delete_payment`
- Estimates: `list_estimates`, `create_estimate`
- Expenses: `list_expenses`, `create_expense`, `list_expense_categories`
- Items/taxes: `list_items`, `create_item`, `list_taxes`, `create_tax`
- Time: `check_timesheet`, `log_time`
- Reports: `get_profit_loss`, `get_income_summary`, `get_accounts_aging`
- Discovery: `list_projects`, `list_services`, `list_staff`, `list_recurring_invoices`

### Call Processor
Runs automatically via Docker. Watches `watch_folder/` for new audio files from customer calls.
Call transcripts land in `_inbox/` after processing — run the ingest skill to incorporate them.

### Skills
- `/ingest` — capture new material from `_inbox/` and propose updates to the vault
- `/curate` — weekly health check; find stale notes, gaps, contradictions

---

## How to Work

1. **Read relevant notes first.** Cite which note each fact came from.
2. **If it isn't in the knowledge base, say so.** Don't guess.
3. **New or changed facts?** Draft into `_proposed/` and tell Tristian what changed.
4. **Before touching FreshBooks**, confirm with the relevant note (client name, job details).
5. **Sensitive material** (payment info, personal data): flag it, don't copy it into the vault.

---

## Skills

Run by typing `/ingest` or `/curate`, or "run the ingest skill."

- **ingest** — turns raw material from `_inbox/` into proposed vault notes
- **curate** — weekly review to catch stale facts, gaps, and contradictions

See `SETUP.md` for how to install skills in Claude Code.
