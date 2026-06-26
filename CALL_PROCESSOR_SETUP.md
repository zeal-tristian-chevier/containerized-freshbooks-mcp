# CHEVS Garage — Call Processor Setup Guide

Automatically records customer calls, transcribes them, creates FreshBooks clients/estimates,
and schedules follow-up reminders. No monthly fees beyond your existing Claude Code subscription.

---

## How It Works

```
Phone call ends
      ↓
Audio file auto-uploads to Google Drive (Android) or manual share (iPhone)
      ↓
Google Drive syncs file to your PC/Mac watch_folder/
      ↓
Call processor detects new file (runs 24/7 in background)
      ↓
Whisper transcribes audio locally (free, no internet needed)
      ↓
Claude extracts: customer, ATV, work requested, parts, follow-ups
      ↓
FreshBooks: creates/updates client + estimate automatically
      ↓
Email summary sent to you + reminders scheduled for follow-ups
```

---

## Part 1 — Phone Setup

### Android Shop Phone (Fully Automatic)

**Step 1 — Install Cube ACR**
1. Open Play Store → search **Cube ACR** → install
2. Open Cube ACR → grant all permissions (microphone, phone, storage)
3. Make a test call to confirm it records (you'll see a floating mic icon during calls)

**Step 2 — Enable Google Drive auto-upload**
1. In Cube ACR → tap the menu (≡) → **Settings** → **Cloud services**
2. Tap **Google Drive** → sign in with your Google account
3. Set upload folder to `CHEVS-Calls`
4. Enable **Auto upload** → set to **After call ends**

Every call now automatically uploads an audio file to Google Drive when it finishes.

---

### iPhone Personal Phone (One Tap — iOS 18+)

> **Check your iOS version:** Settings → General → About → iOS Version.
> If below 18, see the Google Voice alternative at the bottom of this section.

**iOS 18 built-in call recording:**
1. During any call, tap the **Record** button (top of screen)
2. iOS plays an announcement to both parties that the call is being recorded
3. When the call ends, the recording saves automatically to your **Notes** app

**Sharing the recording to Google Drive:**
1. Open Notes → find the recording (listed by date/time)
2. Tap the recording → tap **Share** → tap **Save to Drive**
3. Navigate to **CHEVS-Calls** folder → tap **Save**

The file will sync to your PC/Mac and be processed within a minute.

**Optional — make it one tap with a Shortcut:**
1. Open the **Shortcuts** app on iPhone
2. Create a new shortcut: "Save last Note recording to CHEVS-Calls Drive folder"
3. Add it to your home screen — after each call, one tap shares it automatically

---

**iOS 17 or older — use Google Voice instead:**
1. Go to voice.google.com → set up a free Google Voice number (use this as your shop callback number)
2. During any incoming call, press **4** on your keypad to start recording
3. Recordings automatically appear in your Google Drive under **My Drive → Call Recordings**
4. Move them to the `CHEVS-Calls` folder (or update the sync path in the config)

---

## Part 2 — Windows PC Setup

### Prerequisites
- Python 3.11 or newer: python.org/downloads
- Claude Code installed and logged in (already done)
- Git (optional): git-scm.com

### Step 1 — Google Drive for Desktop

1. Download: drive.google.com/drive/download
2. Install and sign in with the same Google account used on the phones
3. Open Google Drive for Desktop preferences → **My Drive sync options**
4. Choose **Mirror files** (not Stream) — this keeps files locally on disk
5. Note the local sync path — it will look like:
   `C:\Users\tristian\Google Drive\My Drive\`

### Step 2 — Link the CHEVS-Calls folder to watch_folder

Open PowerShell and run:
```powershell
# Replace the Google Drive path if yours is different
$src = "$env:USERPROFILE\Google Drive\My Drive\CHEVS-Calls"
$dest = "C:\Users\tristian\Desktop\Projects\freshbooks-timesheet-mcp\watch_folder"

# Create CHEVS-Calls folder on Drive if it doesn't exist yet
New-Item -ItemType Directory -Force $src

# Create a junction (folder shortcut) so Drive syncs directly into watch_folder
# NOTE: Remove watch_folder first if it already exists as a plain folder
Remove-Item $dest -Recurse -Force -ErrorAction SilentlyContinue
cmd /c mklink /J $dest $src
Write-Host "Linked: $src → $dest"
```

> If you'd rather not use a junction, you can set Cube ACR's upload folder directly to
> `watch_folder` and skip this step — just make sure Drive mirrors to that path.

### Step 3 — Configure email notifications

Open `.env` in the project folder and fill in:
```
EMPLOYEE_EMAIL=steve@example.com        # Steve's email for task reminders
SMTP_USER=tmchevierbusiness@gmail.com
SMTP_PASS=xxxx xxxx xxxx xxxx           # Gmail App Password (see below)
```

**Getting a Gmail App Password:**
1. Go to myaccount.google.com → Security
2. Enable 2-Step Verification if not already on
3. Search for **App Passwords** → create one → name it "CHEVS Processor"
4. Copy the 16-character password → paste into `SMTP_PASS` in `.env`

### Step 4 — Run the processor

```powershell
cd C:\Users\tristian\Desktop\Projects\freshbooks-timesheet-mcp
.venv\Scripts\python.exe -m call_processor.main
```

You should see:
```
CHEVS Garage Call Processor
[WATCHER] Watching C:\...\watch_folder
[SCHEDULER] Started.
Ready. Drop audio files into watch_folder/ to process them.
```

### Step 5 — Auto-start on Windows boot (Task Scheduler)

1. Open **Task Scheduler** (search in Start menu)
2. Click **Create Basic Task** → name it `CHEVS Call Processor`
3. Trigger: **When the computer starts**
4. Action: **Start a program**
   - Program: `C:\Users\tristian\Desktop\Projects\freshbooks-timesheet-mcp\.venv\Scripts\python.exe`
   - Arguments: `-m call_processor.main`
   - Start in: `C:\Users\tristian\Desktop\Projects\freshbooks-timesheet-mcp`
5. Finish → right-click the task → Properties → check **Run whether user is logged on or not**

To check logs, add this to the Arguments field instead:
```
-m call_processor.main >> C:\Users\tristian\Desktop\Projects\chevs-processor.log 2>&1
```

---

## Part 3 — macOS Setup

### Prerequisites

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.11+
brew install python@3.11

# Install ffmpeg (required by Whisper for audio conversion)
brew install ffmpeg
```

> **Windows note:** ffmpeg is also required on Windows. Download from ffmpeg.org/download.html,
> extract it, and add the `bin` folder to your PATH. Or install via:
> `winget install ffmpeg`

### Step 1 — Clone/copy the project

```bash
cd ~/Projects
# If copying from Windows, transfer the freshbooks-timesheet-mcp folder here
# Then set up the venv:
cd freshbooks-timesheet-mcp
python3.11 -m venv .venv
.venv/bin/pip install -r requirements-processor.txt
.venv/bin/pip install -r requirements.txt   # existing MCP server deps
```

### Step 2 — Google Drive for Desktop (macOS)

1. Download from drive.google.com/drive/download
2. Install → sign in → choose **Mirror files**
3. Local path will be:
   `~/Library/CloudStorage/GoogleDrive-tmchevierbusiness@gmail.com/My Drive/`

Link CHEVS-Calls to watch_folder:
```bash
DRIVE_PATH="$HOME/Library/CloudStorage/GoogleDrive-tmchevierbusiness@gmail.com/My Drive/CHEVS-Calls"
WATCH="$HOME/Projects/freshbooks-timesheet-mcp/watch_folder"

mkdir -p "$DRIVE_PATH"
rm -rf "$WATCH"
ln -s "$DRIVE_PATH" "$WATCH"
echo "Linked: $DRIVE_PATH → $WATCH"
```

> If your Drive email is different, check the exact folder name in Finder under
> Locations → Google Drive.

### Step 3 — Configure .env (same as Windows)

```bash
cd ~/Projects/freshbooks-timesheet-mcp
nano .env
# Fill in EMPLOYEE_EMAIL, SMTP_USER, SMTP_PASS same as Windows instructions above
```

### Step 4 — Run the processor

```bash
cd ~/Projects/freshbooks-timesheet-mcp
.venv/bin/python -m call_processor.main
```

### Step 5 — Auto-start on macOS boot (LaunchAgent)

Create the file `~/Library/LaunchAgents/com.chevs.callprocessor.plist`:

```bash
cat > ~/Library/LaunchAgents/com.chevs.callprocessor.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.chevs.callprocessor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOUR_USERNAME/Projects/freshbooks-timesheet-mcp/.venv/bin/python</string>
        <string>-m</string>
        <string>call_processor.main</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USERNAME/Projects/freshbooks-timesheet-mcp</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/chevs-processor.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/chevs-processor-error.log</string>
</dict>
</plist>
EOF

# Replace YOUR_USERNAME with your actual macOS username
sed -i '' "s/YOUR_USERNAME/$(whoami)/g" ~/Library/LaunchAgents/com.chevs.callprocessor.plist

# Load it now (also runs on every future boot)
launchctl load ~/Library/LaunchAgents/com.chevs.callprocessor.plist
echo "Service started."
```

To check logs:
```bash
tail -f /tmp/chevs-processor.log
```

To stop/restart:
```bash
launchctl unload ~/Library/LaunchAgents/com.chevs.callprocessor.plist
launchctl load   ~/Library/LaunchAgents/com.chevs.callprocessor.plist
```

---

## Testing the Full Flow

**Quick test (no real call needed):**
1. Find any short audio file (voice memo, .m4a, .mp3)
2. Copy it into `watch_folder\` (Windows) or `watch_folder/` (macOS)
3. Watch the terminal — within seconds you should see:
   ```
   [WATCHER] New audio: test.m4a
   [PIPELINE] Processing: test.m4a
   [TRANSCRIBER] Loading Whisper model... (first run only — downloads ~150MB)
   [TRANSCRIBER] 45s audio → 312 chars
   [EXTRACTOR] Sending transcript to Claude...
   [EXTRACTOR] Got structured data for: John Smith
   [ACTIONS] Created new client: John Smith (id=12345)
   [ACTIONS] Created estimate id=67890
   [SCHEDULER] Reminder scheduled for 2026-06-28 → owner: Call customer when parts arrive
   [PIPELINE] Done: John Smith | 2019 Polaris RZR 900
   ```
4. Check your email for the summary
5. Check FreshBooks — client and estimate should be there

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `claude: command not found` | Make sure Claude Code is installed and in PATH. Try `where claude` (Windows) or `which claude` (macOS) |
| Whisper takes too long | Change `WHISPER_MODEL=tiny` in `.env` for faster (slightly less accurate) transcription |
| Files not appearing in watch_folder | Check Google Drive for Desktop is running and set to Mirror (not Stream) mode |
| Email not sending | Double-check the Gmail App Password — it must be an App Password, not your regular Gmail password |
| FreshBooks auth error | Re-run the auth flow: `.venv/Scripts/python.exe -m freshbooks_mcp.auth` (Windows) |
| Cube ACR not recording | On newer Android versions, go to Settings → Apps → Cube ACR → Permissions → enable Microphone and Phone |

---

## File Reference

```
freshbooks-timesheet-mcp/
├── call_processor/
│   ├── config.py        edit WHISPER_MODEL, email settings here
│   ├── extractor.py     Claude prompt for data extraction
│   ├── pipeline.py      main orchestration logic
│   └── scheduler.py     reminder queue (stored in reminders.db)
├── watch_folder/        drop audio files here
│   └── processed/       successfully processed files move here
├── reminders.db         SQLite — persists reminders across reboots
└── .env                 all configuration (credentials, email, etc.)
```
