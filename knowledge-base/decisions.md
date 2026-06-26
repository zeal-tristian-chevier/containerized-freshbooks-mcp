---
title: Decisions & Why
source: owner
date: 2026-06-26
status: verified
---

# Decisions & Why

A record of significant business decisions and their reasoning.
Useful context before making similar decisions again.

## 2026 — Automated call processor
- **Decision:** Build a local call transcription and FreshBooks automation system
- **Why:** Reduce time spent on computer data entry after customer calls; shop phone is
  already recorded via Cube ACR on Android
- **Stack:** faster-whisper (local), Claude Code CLI, FreshBooks MCP, Docker
- **Trade-off considered:** Cloud-based automation (n8n, Make.com) was ruled out for cost;
  Anthropic API key approach was ruled out in favour of existing Claude Code subscription

## 2026 — Docker containerization
- **Decision:** Run call processor in Docker so it can be cloned to any machine without setup
- **Why:** Owner has two computers; wanted one-command deploy on a new system

## [Add decisions as they come up]
