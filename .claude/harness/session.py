"""
session.py — the SESSION spine (role-pipeline harness, Phase 8).

Per-role short-term memory + the relearn queue. Pure functions + a thin CLI. This is the SESSION
spine (resume/pause/destale), DISTINCT from the COORDINATION spine (handoff/board): the coordination
spine moves an artifact between roles (a lateral handoff); the session spine carries a single role's
working state across its OWN sessions (a temporal handoff) and decides that role's next action.

`next_action()` is a pure, deterministic reduction of the shared bus + my lane to ONE action, in a
fixed priority. The gate-4-before-gate-5 ordering is LOAD-BEARING: a role must never abandon in-flight
work to start a fresh task.

    1 HALT   (role unset/unknown)            fail-closed, mirrors access_guard
    2 REVISE (pipeline[role] == "bounced")   my artifact was kicked back — downstream blocked on me
    3 REVIEW (an upstream artifact "ready")  the pipeline waits on my acceptance gate
    4 RESUME (an in-flight .continue-here)   finish what I started before starting new work
    5 START  (a READY task assigned to me)   new work
    6 IDLE   (nothing actionable)

Routing is bus-only + topology — no reviews-log archaeology, no file I/O here (the CLI parses).
"""

import json
from pathlib import Path

import board
import task_split
from board import ROLES

# author→reviewer topology: who reviews whose published artifact. The forward edges are the linear
# ROLES order (each stage reviews the PREVIOUS stage's artifact); the one back-edge is the Senior
# reviewing the Junior's completion records (board.py / CODEOWNERS: junior WRITES, senior ACCEPTS).
_REVIEWS = {
    "sa": ("po",),
    "senior": ("sa", "junior"),
    "junior": ("senior",),
}


def next_action(role, pipeline, my_task_states, has_continue_here):
    """Reduce the shared bus + my lane to ONE next action. Pure — no file I/O (the CLI does parsing).

    role              : the acting role (po|sa|senior|junior); None/unknown → halt (fail-closed).
    pipeline          : {role: bus-status} parsed from pipeline-status.md.
    my_task_states    : list of (task_id, state) for my tasks (state from board.task_state).
    has_continue_here : True if my lane has an unresolved .continue-here.md (an in-flight task).
    Returns {"action", "target", "reason"}.
    """
    if not role or role not in ROLES:
        return {"action": "halt", "target": None,
                "reason": "acting_as is unset/unknown — set your role before resuming (fail-closed)."}

    if pipeline.get(role) == "bounced":
        return {"action": "revise", "target": role,
                "reason": "your published artifact was bounced/reopened — revise it first; "
                          "downstream is blocked on you."}

    waiting = [a for a in _REVIEWS.get(role, ()) if pipeline.get(a) == "ready"]
    if waiting:
        return {"action": "review", "target": waiting,
                "reason": f"upstream {waiting} published and awaits your acceptance — the pipeline "
                          "waits on your gate."}

    if has_continue_here:
        return {"action": "resume_task", "target": None,
                "reason": "you have an in-flight task (.continue-here.md) — finish it before new work."}

    ready = [tid for tid, state in my_task_states if state == "READY"]
    if ready:
        # "to start" — neutral: the CLI passes only MY tasks when --me is set, or ALL tasks in the
        # no-name fallback, so this reason must not claim "assigned to you" (it may not be).
        return {"action": "start_task", "target": ready[0],
                "reason": f"next READY task to start: {ready[0]}."}

    return {"action": "idle", "target": None,
            "reason": "nothing actionable — you're blocked or done; check the board (status --me)."}


# --- the relearn queue: per-lane staging the Stop hook fills, pause drains, resume nets ----------

def queue_path(role: str, root: str = ".") -> str:
    """Posix path to a role's relearn queue: <root>/memory-bank/<role>/.relearn-queue.jsonl.

    Validates the role (defense-in-depth: never interpolate an unvalidated role into a path)."""
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r} — must be one of {ROLES}")
    root = str(root).replace("\\", "/").rstrip("/")
    return f"{root}/memory-bank/{role}/.relearn-queue.jsonl"


def enqueue_learning(role: str, item: dict, root: str = ".") -> None:
    """Append one candidate learning to the role's queue (one JSON object per line)."""
    p = Path(queue_path(role, root))
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item) + "\n")


def read_queue(role: str, root: str = ".") -> list:
    """All queued candidates. Missing file → [] (never crash); a malformed line is skipped."""
    p = Path(queue_path(role, root))
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


def clear_queue(role: str, root: str = ".") -> None:
    """Empty the queue (pause clears it after draining; a missing file is a no-op)."""
    p = Path(queue_path(role, root))
    if p.exists():
        p.write_text("", encoding="utf-8")


# --- thin CLI for the resume / pause skills ------------------------------------------------------

def _my_task_states(tasks, pipeline, done_ids, me):
    """The (task_id, state) list resume's gate 5 reads. Respects the architecture-lock gate the board
    enforces (DESIGN §9): if the SA artifact is not `accepted`, no task is assignable → all GATED, so
    next_action will not tell a role to START before the design is locked. me=None → the UNFILTERED
    list (the no-board-name fallback)."""
    selected = board.filter_for_assignee(tasks, me) if me else tasks
    gated = pipeline.get("sa") != "accepted"
    if gated:
        return [(t["id"], "GATED") for t in selected]
    return [(t["id"], board.task_state(t, done_ids)[0]) for t in selected]


def _cli(argv=None) -> None:
    import argparse

    ap = argparse.ArgumentParser(description="session spine — next-action routing / relearn queue")
    sub = ap.add_subparsers(dest="action", required=True)

    na = sub.add_parser("next-action")
    na.add_argument("--role", required=True)
    na.add_argument("--me", default=None, help="board-assignee name; omit = unfiltered (no-name fallback)")
    na.add_argument("--plan", required=True)
    na.add_argument("--pipeline-status", default="memory-bank/shared/pipeline-status.md")
    na.add_argument("--reviews-log", default="memory-bank/shared/reviews/log.jsonl")
    na.add_argument("--lane", required=True, help="my role lane dir, e.g. memory-bank/senior")

    q = sub.add_parser("queue")
    q.add_argument("--role", required=True)
    q.add_argument("--root", default=".")
    grp = q.add_mutually_exclusive_group()
    grp.add_argument("--show", action="store_true")
    grp.add_argument("--clear", action="store_true")

    args = ap.parse_args(argv)

    if args.action == "next-action":
        tasks = task_split.parse_tasks(Path(args.plan).read_text(encoding="utf-8"))
        pipeline = board.parse_pipeline_status(Path(args.pipeline_status).read_text(encoding="utf-8"))
        done = board.done_task_ids(board._load_records(args.reviews_log))
        my_states = _my_task_states(tasks, pipeline, done, args.me)
        has_ch = (Path(args.lane) / ".continue-here.md").exists()
        decision = next_action(args.role, pipeline, my_states, has_ch)
        decision["name_unset"] = args.me is None
        print(json.dumps(decision))
    else:  # queue
        if args.clear:
            clear_queue(args.role, args.root)
            print(f"queue: cleared {queue_path(args.role, args.root)}")
        else:  # --show (default)
            print(json.dumps(read_queue(args.role, args.root)))


if __name__ == "__main__":
    _cli()
