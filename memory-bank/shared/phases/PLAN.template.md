---
status: draft
date: {{YYYY-MM-DD}}
---
<!-- TASK BREAKDOWN — the Senior's decomposition of ONE roadmap phase into parallel-safe tasks
(DESIGN §8). Copy to memory-bank/shared/phases/phase-N/PLAN.md, fill EVERY {{...}} marker, then run
validate_task_breakdown before publish.

Parallel-safety rules (the mechanism enforces these):
  • Tasks in the SAME `Group:` run concurrently — their `Files:` sets MUST be disjoint.
  • A task that depends on another goes in a LATER group (different `Group:`), never the same one.
  • Every task must OWN at least one file; each parallel task runs on its own branch/worktree.
  • Split along the SA's module seams; make each task a thin vertical slice where possible.
Keep the `### Task <id> — <title>` header shape and the four bold fields; .claude/harness/task_split.py
validates against them. -->

## Tasks

### Task T1 — {{title}}
{{What this task builds and which architecture seam / ADR it implements.}}
**Group:** {{parallel-group label, e.g. group-1 — same group ⇒ files MUST be disjoint}}
**Files:** {{comma-separated files this task OWNS — disjoint from every other task in the same Group}}
**Dependencies:** {{task ids this needs first, or none}}
**Verification:** {{the exact command or observable state that confirms this task is done}}

### Task T2 — {{title}}
{{What this task builds and which seam / ADR it implements.}}
**Group:** {{parallel-group label — a task depending on T1 goes in a LATER group, not this one}}
**Files:** {{comma-separated files this task OWNS}}
**Dependencies:** {{task ids, or none}}
**Verification:** {{how to confirm this task is done}}
