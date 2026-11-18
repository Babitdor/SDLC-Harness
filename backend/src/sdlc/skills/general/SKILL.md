---
name: general
description: Cross-cutting rules that apply to every SDLC artifact and every Mermaid model: traceability, placeholder hygiene, ID stability and the self-improvement loop. Read alongside the per-artifact skill.
license: proprietary
---

## When to use

Every session. The per-diagram and per-artifact skills carry the specifics;
this file carries the rules that hold everywhere and collects LEARNED entries
that do not belong to a single skill.

## Rules

- **Traceability over completeness.** An artifact with fewer elements, each
  traceable to an input, beats a fuller one containing invented content.
- **IDs are stable.** Never renumber an existing REQ/US/AC/ADR/TC/BI id; add
  the next number instead.
- **Placeholders are failures.** `<requirement text>`, `TODO`, `TBD` and
  `lorem ipsum` in an output artifact mean the artifact is not done.
- **Read once.** Read each input artifact and skill file once per session, then
  work from message history. Re-reading is the single largest avoidable cost.
- **Edit, do not rewrite.** `edit_file` for a change; `write_file` only to
  create a file that does not exist yet — and never for a `LEARNED.md`.
- **Degraded validation must be reported.** If a validator says it fell back to
  a structural check, say that in your summary. Never call it "validated".

## Common failure modes

- Reporting an artifact as done while a validator still reports errors.
- Appending a long prose block to a `LEARNED.md` "No new fixes" entry: these
  files are read in full every session, so prose there is a permanent token tax.
