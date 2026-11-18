# Learned Fixes — Deployment Diagrams

Append-only log of fix patterns discovered while validating this artifact.
These files are read in full during Phase A of every session, so an entry
must be one line of actual information — never prose about what was built.

Format (a no-fix session is exactly these two lines):
## Session YYYY-MM-DD
- No new fixes.

The agent reads this file in Phase A (alongside SKILL.md) and appends
new entries in Phase C after completing all files.

## Session 2026-11-17
- No new fixes.
