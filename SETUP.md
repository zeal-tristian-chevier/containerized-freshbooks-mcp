# CHEVS Garage — Complete Setup Guide

This guide takes a brand-new computer from zero to a fully running call processor.
Clone the repo, follow the steps once, and the system runs itself forever after.

---

## How It Works

```
Phone call ends
      ↓
Audio file uploads to Google Drive (automatic on Android, one tap on iPhone)
      ↓
Google Drive for Desktop syncs it to watch_folder/ on your PC/Mac
      ↓
Docker container detects the new file (runs 24/7, restarts on reboot)
      ↓
Whisper transcribes the audio locally — free, no internet required
      ↓
Claude extracts: customer name, ATV, work needed, parts, follow-ups
      ↓
FreshBooks: client created/updated + estimate created automatically
      ↓
Email summary sent to you, follow-up reminders queued for Steve
```

**Cost:** $0/month beyond your existing Claude Code subscription.

---

## What You Need

| Software | Purpose | Free? |
|---|---|---|
| Docker Desktop | Runs the processor in a container | Yes |
| Git | Clone/push the repo | Yes |
| Claude Code CLI | Powers the AI extraction | Subscription |
| Google Drive for Desktop | Syncs phone recordings to your PC/Mac | Yes |
| Cube ACR (Android) | Records phone calls automatically | Free tier |

---

## Part 1 — Install Prerequisites

### Windows

**1. Docker Desktop**
1. Download from docker.com/products/docker-desktop → **Download for Windows**
2. Run the installer (requires restart)
3. After restart, open Docker Desktop — wait for it to say "Engine running"
4. Settings → General → check **Start Docker Desktop when you log in**

**2. Git**
```powershell
winget install Git.Git
# Restart PowerShell after this
```

**3. Claude Code CLI**
```powershell
npm install -g @anthropic-ai/claude-code
claude login
# Follow the browser prompt to sign in with your Anthropic account
```
> If `npm` isn't found, install Node.js first: `winget install OpenJS.NodeJS`

**4. Google Drive for Desktop**
1. Download from drive.google.com/drive/download
2. Install → sign in with your Google account
3. Preferences → **My Drive sync options** → choose **Mirror files**
4. Note your local sync path (usually `C:\Users\YourName\Google Drive\My Drive\`)

---

### macOS

**1. Homebrew** (package manager — skip if already installed)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**2. Docker Desktop**
```bash
brew install --cask docker
open /Applications/Docker.app
# Wait for "Engine running" in the menu bar icon
```
Then: Docker menu bar icon → Preferences → General → check **Start at Login**

**3. Git**
```bash
brew install git
```

**4. Claude Code CLI**
```bash
brew install node
npm install -g @anthropic-ai/claude-code
claude login
# Follow the browser prompt
```

**5. Google Drive for Desktop**
```bash
brew install --cask google-drive
open "/Applications/Google Drive.app"
# Sign in → Preferences → Mirror files
```
Local path will be:
`~/Library/CloudStorage/GoogleDrive-youremail@gmail.com/My Drive/`

---

## Part 2 — Get the Code

### First computer (creating the repo)

```powershell
# Windows
cd C:\Users\tristian\Desktop\Projects\freshbooks-timesheet-mcp
git init
git add .
git commit -m "initial"
```

Then on GitHub (github.com):
1. Click **+** → **New repository**
2. Name it `chevs-call-processor` (or anything you like)
3. Set to **Private**
4. Do NOT initialize with README (you already have files)
5. Click **Create repository**
6. Copy the two commands GitHub shows under "push an existing repository":
```bash
git remote add origin https://github.com/YOUR_USERNAME/chevs-call-processor.git
git branch -M main
git push -u origin main
```

### Any other computer (cloning)

```bash
# Windows
git clone https://github.com/YOUR_USERNAME/chevs-call-processor.git C:\Users\YourName\Desktop\Projects\freshbooks-timesheet-mcp

# macOS
git clone https://github.com/YOUR_USERNAME/chevs-call-processor.git ~/Projects/freshbooks-timesheet-mcp
```

> Secrets (`.env`, `docker.env`, `secrets/`) are gitignored — they never leave
> the machine they were created on. You copy them separately (Part 8 covers this).

---

## Part 3 — FreshBooks Auth (one-time)

The FreshBooks token is stored in `secrets/tokens.enc`. You only do this once.
On subsequent machines, copy the `secrets/` folder instead of repeating this.

**Windows:**
```powershell
cd C:\Users\tristian\Desktop\Projects\freshbooks-timesheet-mcp
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
.venv\Scripts\python -m freshbooks_mcp.auth
```

**macOS:**
```bash
cd ~/Projects/freshbooks-timesheet-mcp
python3.11 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m freshbooks_mcp.auth
```

A browser will open → sign in to FreshBooks → authorize the app → you'll see
"Authentication successful". The token is saved to `secrets/tokens.enc`.

---

## Part 4 — Configure Environment

**Step 1 — Create your `.env`**

```powershell
# Windows
copy .env.example .env
notepad .env

# macOS
cp .env.example .env
nano .env
```

Fill in these values (everything else can stay as the default):

```ini
# FreshBooks OAuth app (from my.freshbooks.com → Developer → your app)
FRESHBOOKS_CLIENT_ID=your_client_id_here
FRESHBOOKS_CLIENT_SECRET=your_client_secret_here

# Token file (Docker overrides this automatically — just set it to the file path)
FRESHBOOKS_TOKEN_BACKEND=file
FRESHBOOKS_TOKEN_PATH=secrets/tokens.enc

# The Fernet key printed when you first ran the auth setup
# (check your terminal output from Part 3, or secrets/secret.key if it was saved)
FRESHBOOKS_TOKEN_KEY=your_fernet_key_here

# Call Processor
NOTIFY_EMAIL=tmchevierbusiness@gmail.com
EMPLOYEE_EMAIL=steves_email@example.com
SMTP_USER=tmchevierbusiness@gmail.com
SMTP_PASS=xxxx xxxx xxxx xxxx
```

**Getting a Gmail App Password** (required — your regular Gmail password won't work):
1. Go to myaccount.google.com → Security
2. Enable **2-Step Verification** if not already on
3. Search **App Passwords** → Create → name it "CHEVS Processor"
4. Copy the 16-character password into `SMTP_PASS`

---

**Step 2 — Create your `docker.env`**

```powershell
# Windows
copy docker.env.example docker.env
notepad docker.env

# macOS
cp docker.env.example docker.env
nano docker.env
```

**Windows** — replace `YourUsername` with your actual Windows username:
```ini
CLAUDE_CONFIG_DIR=C:\Users\YourUsername\.claude
CLAUDE_JSON_FILE=C:\Users\YourUsername\.claude.json
```
> Run `echo $env:USERNAME` in PowerShell to confirm your username.

**macOS** — comment out the Windows lines and uncomment the macOS lines:
```ini
# CLAUDE_CONFIG_DIR=C:\Users\YourUsername\.claude
# CLAUDE_JSON_FILE=C:\Users\YourUsername\.claude.json
CLAUDE_CONFIG_DIR=/Users/yourusername/.claude
CLAUDE_JSON_FILE=/Users/yourusername/.claude.json
```
> Run `whoami` in Terminal to confirm your username.

---

## Part 5 — Phone Setup

### Android Shop Phone (Fully Automatic)

**Install Cube ACR:**
1. Play Store → search **Cube ACR** → Install
2. Open it → grant all permissions (Microphone, Phone, Storage)
3. Make a test call — you should see a floating mic icon during the call

**Enable auto-upload to Google Drive:**
1. Cube ACR → menu (≡) → Settings → **Cloud services**
2. Tap **Google Drive** → sign in with the same Google account used on your PC
3. Set upload folder to: `CHEVS-Calls`
4. Enable **Auto upload** → **After call ends**

Every call now uploads automatically when it ends. Nothing to do after this.

---

### iPhone Personal Phone (iOS 18+)

**Check your iOS version:** Settings → General → About → iOS Version

**iOS 18 built-in recording:**
1. During any call, tap the **Record** button (top of screen)
2. iOS announces the recording to both parties (legal requirement)
3. Recording saves to the **Notes** app when the call ends

**Share to Google Drive:**
1. Open Notes → find the recording
2. Tap it → Share → **Save to Drive** → navigate to **CHEVS-Calls** → Save

**Optional one-tap shortcut:**
1. Open the **Shortcuts** app
2. New shortcut → add action: **Get Notes** (filter: most recent) → **Share** → **Save to Google Drive** → folder: CHEVS-Calls
3. Add to Home Screen — one tap after each call

**iOS 17 or older — Google Voice:**
1. Set up a free number at voice.google.com
2. During a call, press **4** on your keypad to start recording
3. Recordings save to Google Drive automatically under **My Drive → Call Recordings**
4. Move them to `CHEVS-Calls` (or update `WATCH_FOLDER` in `config.py`)

---

## Part 6 — Link Google Drive to watch_folder

The watch_folder is where the processor looks for new audio files.
Link it to your Google Drive CHEVS-Calls folder so recordings arrive automatically.

### Windows

```powershell
# Adjust the Google Drive path if yours is different
$drive = "$env:USERPROFILE\Google Drive\My Drive\CHEVS-Calls"
$watch = "C:\Users\tristian\Desktop\Projects\freshbooks-timesheet-mcp\watch_folder"

New-Item -ItemType Directory -Force $drive
Remove-Item $watch -Recurse -Force -ErrorAction SilentlyContinue
cmd /c mklink /J $watch $drive
Write-Host "Linked."
```

### macOS

```bash
DRIVE="$HOME/Library/CloudStorage/GoogleDrive-tmchevierbusiness@gmail.com/My Drive/CHEVS-Calls"
WATCH="$HOME/Projects/freshbooks-timesheet-mcp/watch_folder"

mkdir -p "$DRIVE"
rm -rf "$WATCH"
ln -s "$DRIVE" "$WATCH"
echo "Linked."
```
> Check your exact Google Drive folder name in Finder → Locations → Google Drive
> if the path above doesn't exist.

---

## Part 7 — Start the Container

**Windows:**
```powershell
cd C:\Users\tristian\Desktop\Projects\freshbooks-timesheet-mcp
.\docker-start.ps1
```

**macOS:**
```bash
cd ~/Projects/freshbooks-timesheet-mcp
bash docker-start.sh
```

**First run takes 5–10 minutes** — it installs Node.js, Claude Code, ffmpeg, and
Python packages inside the image. Subsequent starts take a few seconds.

**Watch the output:**
```bash
docker compose logs -f
```

You should see:
```
CHEVS Garage Call Processor
[WATCHER] Watching /app/watch_folder
[SCHEDULER] Started.
Ready. Drop audio files into watch_folder/ to process them.
```

**Common commands:**
```bash
docker compose logs -f          # live logs
docker compose down             # stop
docker compose up -d            # start (no rebuild)
docker compose up -d --build    # rebuild after code changes
docker compose restart          # restart without rebuild
```

---

## Part 8 — Moving to a New Computer

The repo contains all the code. The three things NOT in the repo that you need
to carry over are:

| File/Folder | What it is | How to transfer |
|---|---|---|
| `secrets/` | FreshBooks encrypted token | USB drive / secure file share |
| `.env` | All credentials and config | USB drive / secure file share |
| `docker.env` | Local paths for Claude auth | Re-create on the new machine (Part 4 Step 2) |

**Steps on the new machine:**
1. Install prerequisites (Part 1)
2. `git clone` the repo (Part 2)
3. Copy `secrets/` and `.env` from old machine into the cloned folder
4. Re-create `docker.env` for the new machine's username (Part 4 Step 2)
5. Link Google Drive (Part 6)
6. Run the startup script (Part 7)

That's it. No FreshBooks auth flow, no Python setup, no Whisper download (first
audio file re-downloads the model ~150MB — only once per machine).

---

## Testing

Drop any short audio file (.mp3, .m4a, .wav) into `watch_folder/` and watch the logs:

```
[WATCHER] New audio: test.m4a
[PIPELINE] Processing: test.m4a
[TRANSCRIBER] Loading Whisper model... (first run — one-time download)
[TRANSCRIBER] 45s audio transcribed → 312 chars
[EXTRACTOR] Sending to Claude...
[EXTRACTOR] Customer: John Smith | ATV: 2019 Polaris RZR 900
[ACTIONS] Created client: John Smith (FreshBooks id=12345)
[ACTIONS] Created estimate id=67890
[SCHEDULER] Reminder: 2026-06-28 → Call when parts arrive
[PIPELINE] Done.
```

Check:
- FreshBooks → client and estimate visible
- Your email inbox → summary received
- `watch_folder/processed/` → the file moved there

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `docker compose` not found | Use `docker-compose` (hyphen) instead — older Docker versions |
| Container exits immediately | Run `docker compose logs` to see the error |
| `claude: command not found` inside container | The image installs Claude Code at build time — try `docker compose up -d --build` to rebuild |
| Claude auth fails in container | Make sure `docker.env` has the correct path to `~/.claude` on your machine |
| FreshBooks 401 Unauthorized | Re-run auth: `.venv/Scripts/python -m freshbooks_mcp.auth` (Windows) or `.venv/bin/python -m freshbooks_mcp.auth` (macOS), then restart the container |
| Files not appearing in watch_folder | Confirm Google Drive for Desktop is running and set to **Mirror** (not Stream) mode |
| Whisper is slow | Set `WHISPER_MODEL=tiny` in `.env` — 3x faster, slightly less accurate |
| Email not sending | The `SMTP_PASS` must be a Gmail **App Password** (16 chars), not your regular password |
| Cube ACR not recording | Android Settings → Apps → Cube ACR → Permissions → enable Microphone and Phone |

---

## File Reference

```
freshbooks-timesheet-mcp/
├── SETUP.md                  ← you are here
├── Dockerfile.processor      container definition for call processor
├── docker-compose.yml        service + volume config
├── docker-start.ps1          Windows one-command startup
├── docker-start.sh           macOS one-command startup
├── docker.env.example        template for docker.env (committed to git)
├── docker.env                your local paths — NOT in git
├── .env.example              template for .env (committed to git)
├── .env                      your credentials — NOT in git
├── secrets/                  FreshBooks token — NOT in git
├── watch_folder/             audio input (linked to Google Drive) — NOT in git
│   └── processed/            successfully processed files land here
├── reminders.db              reminder queue — NOT in git
├── call_processor/
│   ├── config.py             loads .env settings
│   ├── transcriber.py        Whisper audio → text
│   ├── extractor.py          Claude text → structured data
│   ├── actions.py            FreshBooks API calls
│   ├── scheduler.py          reminder queue (APScheduler + SQLite)
│   ├── notifier.py           email notifications
│   ├── watcher.py            folder monitoring (watchdog)
│   ├── pipeline.py           orchestrates all the above
│   └── main.py               entry point
└── freshbooks_mcp/           FreshBooks API client (shared with MCP server)
```
