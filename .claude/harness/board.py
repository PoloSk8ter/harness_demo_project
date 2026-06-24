"""
board.py — the coordination board (role-pipeline harness, Phase 6).

A zero-infra team board generated FROM files that already exist — the Senior's task-breakdown
(`PLAN.md`), the per-role bus (`pipeline-status.md`), and the review audit trail (`reviews/log.jsonl`).
There is no server and no new status field: a task's "done" is DERIVED from the review gate (an
`accept` for that task's shared completion record, reversed by a later `reopen`), so the board can never
drift from the gate.

Pure functions (testable) + a thin CLI:
  parse_pipeline_status(text)        → {role: status} from the `- <role>: <status>` lines
  completion_taskid(path)            → the task id in `…/completions/<id>.md`, else None
  last_verdict_by_artifact(records)  → {artifact: last verdict} (append-order: last wins)
  done_task_ids(records)             → {task ids whose completion's last verdict is `accept`}
  task_state(task, done_ids)         → (DONE|BLOCKED|WIP|READY, blocked_on)
  render_board(tasks, pipeline, done)→ the BOARD.md markdown (stage gates + per-task table)
  filter_for_assignee(tasks, name)   → the subset assigned to `name` (for `status --me`)

No domain vocabulary, no LLM. Policy (paths) comes from the CLI args / HARNESS-CONTEXT defaults.
"""

import json
import re
from pathlib import Path

from task_split import parse_tasks  # the board reads the same task records the Senior publishes

ROLES = ("po", "sa", "senior", "junior")

_PIPELINE_RE = re.compile(r"^\s*-\s*(\w+)\s*:\s*(\S+)\s*$", re.MULTILINE)
# a completion record is the per-task shared ship artifact `…/completions/<id>.md` (Phase 6 done-signal)
_COMPLETION_RE = re.compile(r"(?:^|/)completions/([^/]+)\.md$", re.IGNORECASE)


def parse_pipeline_status(text: str) -> dict:
    """{role: status} from the bus lines (`- po: accepted`). Unlisted roles simply don't appear."""
    return {m.group(1).lower(): m.group(2) for m in _PIPELINE_RE.finditer(text)}


def completion_taskid(artifact_path: str):
    """The task id encoded in a shared completion artifact path `…/completions/<id>.md`, else None.

    Backslashes are normalized to '/' first so a Windows-style path matches identically. Any other
    artifact (a brief, a private-lane file) returns None — only shared completion records signal DONE.
    """
    norm = artifact_path.replace("\\", "/")
    m = _COMPLETION_RE.search(norm)
    return m.group(1) if m else None


def last_verdict_by_artifact(records) -> dict:
    """{artifact: last verdict}. The review log is append-only, so iterating in order and overwriting
    leaves the CURRENT verdict per artifact (a `reopen` after an `accept` correctly wins)."""
    last: dict = {}
    for rec in records:
        artifact = rec.get("artifact")
        verdict = rec.get("verdict")
        if artifact and verdict:
            last[artifact] = verdict
    return last


def done_task_ids(records) -> set:
    """Task ids whose completion record's CURRENT verdict is `accept`. Non-completion artifacts and
    artifacts last bounced/reopened are excluded — so the board's DONE follows the gate exactly."""
    done = set()
    for artifact, verdict in last_verdict_by_artifact(records).items():
        tid = completion_taskid(artifact)
        if tid is not None and verdict == "accept":
            done.add(tid)
    return done


def task_state(task: dict, done_ids: set):
    """Return (state, blocked_on). DONE if accepted; else BLOCKED on any not-done dependency; else WIP
    when it has an assignee, else READY (claimable). blocked_on is the list of not-done dep ids."""
    if task["id"] in done_ids:
        return "DONE", []
    blocked_on = [d for d in task.get("deps", []) if d not in done_ids]
    if blocked_on:
        return "BLOCKED", blocked_on
    return ("WIP" if task.get("assignee") else "READY"), []


def render_board(tasks, pipeline: dict, done_ids: set) -> str:
    """The BOARD.md markdown: a stage-gate header + a per-task table. If the SA artifact is not yet
    `accepted`, the architecture isn't locked — prepend a banner AND render every task as GATED, so no
    task is shown as assignable until the design is locked (DESIGN §9 / Phase-6 R7)."""
    gated = pipeline.get("sa") != "accepted"
    gates = " · ".join(f"{r.upper()}: {pipeline.get(r, '—')}" for r in ROLES)

    lines = ["# Board (generated — do not hand-edit)", "", f"Stage gates — {gates}"]
    if gated:
        lines += ["", "⛔ architecture not locked — no tasks assignable yet"]
    lines += ["", "| Task | State | Assignee | Blocked-on |", "|---|---|---|---|"]
    for t in tasks:
        if gated:
            state, blocked = "GATED", []
        else:
            state, blocked = task_state(t, done_ids)
        assignee = t.get("assignee") or "—"
        blocked_s = ", ".join(blocked) if blocked else "—"
        lines.append(f"| {t['id']} | {state} | {assignee} | {blocked_s} |")
    return "\n".join(lines) + "\n"


def filter_for_assignee(tasks, name: str):
    """The subset of tasks assigned to `name` — the `status --me` view (pull-based awareness)."""
    return [t for t in tasks if t.get("assignee") == name]


# --- thin CLI for the `board` skill ------------------------------------------------------------

def _load_records(path) -> list:
    """Parse a jsonl review log; tolerate a missing file or a malformed line (never crash the board)."""
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _cli() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="coordination board (generate BOARD.md / show my queue)")
    sub = ap.add_subparsers(dest="action", required=True)
    for name in ("board", "status"):
        sp = sub.add_parser(name)
        sp.add_argument("--plan", required=True)
        sp.add_argument("--pipeline-status", default="memory-bank/shared/pipeline-status.md")
        sp.add_argument("--reviews-log", default="memory-bank/shared/reviews/log.jsonl")
        if name == "board":
            sp.add_argument("--out", default="memory-bank/shared/BOARD.md")
        else:
            sp.add_argument("--me", required=True)
    args = ap.parse_args()

    tasks = parse_tasks(Path(args.plan).read_text(encoding="utf-8"))
    pipeline = parse_pipeline_status(Path(args.pipeline_status).read_text(encoding="utf-8"))
    done = done_task_ids(_load_records(args.reviews_log))

    if args.action == "board":
        Path(args.out).write_text(render_board(tasks, pipeline, done), encoding="utf-8")
        print(f"board: wrote {args.out} ({len(tasks)} tasks)")
    else:  # status --me <name>
        print(render_board(filter_for_assignee(tasks, args.me), pipeline, done))


if __name__ == "__main__":
    _cli()
