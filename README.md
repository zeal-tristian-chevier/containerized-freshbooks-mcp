# CHEVS Garage — FreshBooks MCP + Call Processor

Two systems in one repo:

1. **FreshBooks MCP server** — 29 tools that let Claude query and update FreshBooks directly (invoices, clients, estimates, expenses, payments, timesheets, reports).
2. **Call Processor** — records customer phone calls, transcribes them locally with Whisper, extracts job details with Claude, and automatically creates FreshBooks clients/estimates + schedules follow-up reminders.

**Cost:** $0/month beyond your existing Claude Code subscription.

---

## Quick Start

**Full setup from a new machine:** follow [SETUP.md](SETUP.md).

**FreshBooks MCP only (no call processor):** follow [GETTING_STARTED.md](GETTING_STARTED.md).

```bash
git clone https://github.com/zeal-tristian-chevier/containerized-freshbooks-mcp.git
cd containerized-freshbooks-mcp
```

---

## Call Processor — How It Works

```
Phone call ends
      ↓
Cube ACR auto-uploads audio to Google Drive (Android)
or iOS 18 one-tap share to Google Drive (iPhone)
      ↓
Google Drive for Desktop syncs to watch_folder/ on your PC/Mac
      ↓
Docker container detects the new file (runs 24/7)
      ↓
Whisper transcribes audio locally — free, no internet needed
      ↓
Claude extracts: customer, ATV, work needed, parts, follow-ups
      ↓
FreshBooks: client created/updated + estimate created
      ↓
Email summary sent + follow-up reminders queued
```

---

## FreshBooks MCP — Tools (29 total)

**Time tracking**
- `check_timesheet` — report logged/missing/under-logged days for a day, week, or month
- `log_time` — log hours per weekday against a project, with PTO exclusion and dry-run

**Clients & estimates**
- `list_clients` · `create_client`
- `list_estimates` · `create_estimate`

**Invoices & payments**
- `list_invoices` · `get_invoice` · `create_invoice` · `update_invoice` · `send_invoice` · `void_invoice`
- `list_payments` · `apply_payment` · `delete_payment`

**Expenses**
- `list_expenses` · `create_expense` · `list_expense_categories`

**Items, taxes & services**
- `list_items` · `create_item`
- `list_taxes` · `create_tax`
- `list_services` · `list_staff`

**Projects & reports**
- `list_projects` · `list_recurring_invoices`
- `get_profit_loss` · `get_income_summary` · `get_accounts_aging`

---

## Architecture

| Module | Responsibility |
|---|---|
| `freshbooks_mcp/server.py` | MCP interface — 29 tool definitions + testable `handle_*` functions |
| `freshbooks_mcp/freshbooks_client.py` | HTTP wrapper: auth injection, 401→refresh→retry, pagination |
| `freshbooks_mcp/auth_manager.py` | OAuth2 lifecycle: refresh, token rotation, bootstrap CLI |
| `freshbooks_mcp/token_store.py` | Pluggable storage: OS keychain or Fernet-encrypted file |
| `freshbooks_mcp/transformers.py` | Pure date math, unit conversion, report building |
| `call_processor/pipeline.py` | Orchestrates transcribe → extract → FreshBooks → notify |
| `call_processor/transcriber.py` | Local Whisper transcription (faster-whisper, CPU) |
| `call_processor/extractor.py` | Runs `claude -p` to extract structured job data |
| `call_processor/actions.py` | FreshBooks client/estimate creation |
| `call_processor/scheduler.py` | APScheduler + SQLite reminder queue |
| `call_processor/watcher.py` | watchdog folder monitor |

---

## Configuration

All settings in `.env` (copy from `.env.example`).

**FreshBooks OAuth** — credentials from my.freshbooks.com → Developer → your app:

| Variable | Required | Notes |
|---|---|---|
| `FRESHBOOKS_CLIENT_ID` | ✅ | OAuth app client id |
| `FRESHBOOKS_CLIENT_SECRET` | ✅ | OAuth app secret |
| `FRESHBOOKS_REDIRECT_URI` | ✅ | Must exactly match the app setting (e.g. `https://localhost/callback`) |
| `FRESHBOOKS_TOKEN_BACKEND` | — | `keyring` (default) or `file` |
| `FRESHBOOKS_TOKEN_PATH` | — | Encrypted token file path (file backend) |
| `FRESHBOOKS_TOKEN_KEY` | — | Fernet key for file backend |
| `TZ` | — | Timezone for day boundaries (default `America/Toronto`) |
| `DEFAULT_DAILY_HOURS` | — | Expected hours/day (default `8`) |

**Call Processor:**

| Variable | Notes |
|---|---|
| `WHISPER_MODEL` | `tiny` / `base` (default) / `small` / `medium` |
| `NOTIFY_EMAIL` | Your email — receives a summary after each call |
| `EMPLOYEE_EMAIL` | Employee email for task reminders |
| `SMTP_USER` / `SMTP_PASS` | Gmail credentials (use an App Password) |

---

## Docker

Two containers, two Dockerfiles:

| File | What it builds |
|---|---|
| `Dockerfile` | MCP server — used by Claude Code/Desktop to query FreshBooks |
| `Dockerfile.processor` | Call processor — runs 24/7, watches for new audio files |

Start the call processor:
```bash
# Windows
.\docker-start.ps1

# macOS
bash docker-start.sh
```

Register the MCP server with Claude Code (`.mcp.json`):
```json
{
  "mcpServers": {
    "freshbooks": {
      "command": "docker",
      "args": ["compose", "-f", "/ABS/PATH/TO/docker-compose.yml", "run", "--rm", "-T", "app"]
    }
  }
}
```

---

## API Notes

Verified live against the FreshBooks v3 API:

- **Two hosts.** Auth on `https://auth.freshbooks.com/oauth/authorize`; all data calls on `https://api.freshbooks.com`.
- **Rotating refresh tokens.** Each refresh invalidates the old token. The new token is persisted before use, under a lock.
- **Time entries use `businessId`** (not accountId). `duration` is in seconds; `started_at` is UTC with milliseconds + `Z`.
- **Date filters on payments/expenses** are silently ignored by the API — filtering is done client-side after fetching.
- **Expense category names** are always null in the v3 API for system categories.
- **Accounts aging report** returns 404 on some account types — falls back to computing aging from outstanding invoice data.

---

## Security

- **Token storage** — OS keychain by default; encrypted-file fallback uses Fernet with the key in env (never co-located with the ciphertext), `0600` permissions, and atomic writes.
- **No secret leakage** — `TokenSet` masks values in `repr`; token payloads are never logged.
- **Safe writes** — `log_time` requires an explicit `project_id`, defaults to `skip_existing=true`, supports `dry_run`, never logs weekends.
- **Compromise recovery** — revoke in the FreshBooks Developer Portal, then re-run `freshbooks-mcp-auth`.

---

## Development

```bash
pytest            # unit tests

# or in Docker:
docker build --target test -t freshbooks-mcp:test . && docker run --rm freshbooks-mcp:test
```

---

## License

Internal / private. Not licensed for distribution.
