---
name: ingest
description: Capture new material from _inbox/ (call transcripts, notes, dropped files) into proposed knowledge-base updates for CHEVS Garage.
---

# Skill: Ingest new material

Turn new material from `_inbox/` into proposed knowledge-base notes.

1. Read all files in `_inbox/`. Also read the existing `knowledge-base/` notes for context.
2. For each piece of new material, extract durable facts only:
   - Customer names, machines (year/make/model), work requested
   - Parts needed or ordered, ETA if known
   - Decisions made during the call
   - Follow-up commitments and deadlines
   - Anything that updates or contradicts an existing note
   Skip conversational filler and anything already captured.
3. Draft each update as a note with frontmatter (title, source, date, status: extracted)
   into `_proposed/`. Always record which source file it came from.
   - New customer info → draft addition to `knowledge-base/customers.md`
   - New pending item → draft addition to `knowledge-base/open-loops.md`
   - New decision → draft addition to `knowledge-base/decisions.md`
   - Changed fact → note the contradiction and propose a supersession
4. Flag anything sensitive (payment info, personal data) — describe it, don't copy it in.
5. Write a short SUMMARY of what's proposed and any conflicts for Tristian to review.

Never write directly to `knowledge-base/`. Leave `_inbox/` files in place — Tristian moves
or deletes them after review.
