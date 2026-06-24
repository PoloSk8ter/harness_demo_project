# Pipeline Status

Bus state — where each role's handoff currently stands. The `publish`/`review` gate (handoff.py)
updates one line per role. Statuses: `draft` → `ready` → `accepted` | `bounced` (→ back to `draft`).

- po: accepted
- sa: ready
- senior: draft
- junior: draft
