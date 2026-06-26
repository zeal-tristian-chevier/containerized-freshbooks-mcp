# CHEVS Garage Call Processor — Windows Docker startup script
# Run once: .\docker-start.ps1
# After that, container auto-restarts on boot (Docker Desktop must be running)

Set-Location $PSScriptRoot

# Create reminders.db if it doesn't exist (Docker needs a file to bind-mount, not a dir)
if (-not (Test-Path "reminders.db")) {
    New-Item -ItemType File "reminders.db" | Out-Null
    Write-Host "Created reminders.db"
}

# Create watch_folder if needed
New-Item -ItemType Directory -Force "watch_folder\processed" | Out-Null

# Build and start
Write-Host "Building container (first run installs Node, Claude Code, Whisper — takes a few minutes)..."
docker compose up -d --build

Write-Host ""
Write-Host "Container started. To view logs:"
Write-Host "  docker compose logs -f"
Write-Host ""
Write-Host "To stop:"
Write-Host "  docker compose down"
