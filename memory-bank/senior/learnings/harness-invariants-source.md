# Senior review-craft: the enforced invariants live in architecture.md, not HARNESS-CONTEXT.md

**Kind:** role_instinct · **Captured:** 2026-06-25 (during Phase 1 split, reviewing SA architecture v1)

## The instinct
When reviewing the SA's architecture, do NOT bounce over the `## invariants` section in
`HARNESS-CONTEXT.md` still showing placeholder text (`<e.g. money values...>`). That is a **tooling
limitation, not an SA defect**:

- `context_init.set_field` (the only guard-safe writer for HARNESS-CONTEXT.md) rewrites `- key: value`
  fields ONLY — its regex is `^(-\s*<key>:\s*)...`. The invariants are free-text list items (`- <rule>`,
  no key), so the mechanism literally cannot fill them.
- No role's lane includes `HARNESS-CONTEXT.md`, so the access guard blocks any tool-write to it anyway.
- `conformance_check.py` / `architecture.py` do not mechanically parse the invariants list; enforcement
  is the human `check`/`conform` reading it.

So the **canonical, complete invariants list lives in `architecture.md`'s `## Invariants` section**
(the SA authors it there, labeled "the P0 rules the Senior `check` and Junior `conform` enforce"). Read
those, not the HARNESS-CONTEXT placeholder.

## How to apply
- At `review`: treat architecture.md's Invariants as the enforced set; the HARNESS-CONTEXT placeholder
  is not a bounce reason.
- At `check`/`split`: spec-bind tasks to architecture.md's invariants (e.g. Inv 3 confirm-then-execute,
  Inv 8 seam isolation, Inv 9 two-tier verification).
- It is still worth surfacing to a human harness owner as a real gap (the documented enforcement source
  in CLAUDE.md §5 — HARNESS-CONTEXT invariants — can't be populated for list-style rules). Surfaced this
  session.
