#!/bin/bash
# CHEVS Garage Call Processor — macOS Docker startup script
# Run once: bash docker-start.sh
# After that, container auto-restarts on boot (Docker Desktop must be running)

set -e
cd "$(dirname "$0")"

# Swap docker.env to macOS paths
USERNAME=$(whoami)
sed -i '' "s|^CLAUDE_CONFIG_DIR=.*|# CLAUDE_CONFIG_DIR=C:\\\\Users\\\\tristian\\\\.claude|" docker.env
sed -i '' "s|^CLAUDE_JSON_FILE=.*|# CLAUDE_JSON_FILE=C:\\\\Users\\\\tristian\\\\.claude.json|" docker.env
sed -i '' "s|^# CLAUDE_CONFIG_DIR=/Users/.*|CLAUDE_CONFIG_DIR=/Users/$USERNAME/.claude|" docker.env
sed -i '' "s|^# CLAUDE_JSON_FILE=/Users/.*|CLAUDE_JSON_FILE=/Users/$USERNAME/.claude.json|" docker.env
echo "docker.env updated for macOS ($USERNAME)"

# Create reminders.db if it doesn't exist (Docker needs a file, not a dir)
touch reminders.db
mkdir -p watch_folder/processed

echo "Building container (first run takes a few minutes)..."
docker compose up -d --build

echo ""
echo "Container started. To view logs:"
echo "  docker compose logs -f"
echo ""
echo "To stop:"
echo "  docker compose down"
