---
name: curate
description: Weekly health check on the CHEVS Garage knowledge base — find stale notes, gaps, contradictions, and open loops with no recent activity.
---

# Skill: Curate (run weekly)

Keep the vault healthy. Read `knowledge-base/` and `_inbox/`; write findings to `_proposed/`.

Report and propose fixes for:
- **Stale notes** — entries older than 60 days that haven't been updated and may be outdated
- **Contradictions** — two notes that disagree on the same fact
- **Open loops with no activity** — items in `open-loops.md` with no update in 14+ days
- **Unverified facts** — entries still marked `extracted` or `inferred` that Tristian should confirm
- **Gaps** — obvious things the shop clearly cares about that the vault doesn't cover yet
  (e.g., a recurring customer mentioned in a transcript but not in `customers.md`)
- **Unprocessed inbox** — files sitting in `_inbox/` that haven't been ingested

Output:
1. A short health report (what's good, what needs attention)
2. Any proposed edits in `_proposed/`

Recommend; never auto-change `knowledge-base/`.
