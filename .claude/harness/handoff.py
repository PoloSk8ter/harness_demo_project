"""
handoff.py — the publish/review handoff gate state machine (role-pipeline harness, new mechanism #1).

Tested core shared by the `publish` and `review` skills. Pure transition logic + thin file I/O.
The artifact's lifecycle status lives in its LEADING markdown frontmatter `status:`; the bus state
lives in `memory-bank/shared/pipeline-status.md`; the backward-arrow audit trail is appended to
`memory-bank/shared/reviews/log.jsonl` (both under shared/, per design §5 / §5.1).

State machine:
    draft  --publish-->  ready  --accept-->  accepted
                         ready  --bounce-->  bounced  --revise-->  draft

Any other transition is invalid and raises. Bounce `iteration` is derived by counting prior bounce
records for the artifact (not hand-passed), so the cap/escalate signal reflects reality.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

_PathLike = Union[str, Path]

# --- transition table ----------------------------------------------------------------------------

_TRANSITIONS: dict[str, dict[str, str]] = {
    "publish": {"draft": "ready"},
    "accept": {"ready": "accepted"},
    "bounce": {"ready": "bounced"},
    "revise": {"bounced": "draft"},
    # change-request (design §9): a flaw found in downstream dev — AFTER the artifact was accepted —
    # re-opens the locked artifact back into the revise cycle, so the author can amend + re-publish at
    # v(N+1) and the downstream re-accepts. Without this, `accepted` is terminal and §9's "not a trap"
    # promise cannot execute (review 3b F1).
    "reopen": {"accepted": "bounced"},
}


def next_status(current: str, action: str) -> str:
    """Return the status after applying `action` to `current`, or raise ValueError if invalid."""
    table = _TRANSITIONS.get(action)
    if table is None:
        raise ValueError(f"unknown action: {action!r}")
    if current not in table:
        raise ValueError(f"cannot {action!r} from status {current!r}")
    return table[current]


# --- artifact status (LEADING YAML frontmatter `status:`) ----------------------------------------
# The status contract lives ONLY in the leading `---...---` block. A `status:` line in the body
# (prose, a table, a quoted bounce reason) must never be read or rewritten.

_STATUS_RE = re.compile(r"^status:\s*(\S+)\s*$", re.MULTILINE)
_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.DOTALL)


def _frontmatter(text: str) -> Optional[re.Match]:
    """Match the leading `---...---` block (group(1) = its inner content), or None if absent."""
    return _FRONTMATTER_RE.match(text)


def read_status(path: _PathLike) -> str:
    text = Path(path).read_text(encoding="utf-8")
    fm = _frontmatter(text)
    if not fm:
        raise ValueError(f"no leading frontmatter (---...---) in {path}")
    m = _STATUS_RE.search(fm.group(1))
    if not m:
        raise ValueError(f"no 'status:' field in frontmatter of {path}")
    return m.group(1)


def set_status(path: _PathLike, status: str) -> None:
    """Rewrite only the `status:` line inside the leading frontmatter; everything else untouched.

    Uses a function replacement so a status value containing a backslash is never interpreted as a
    regex backreference (cf. update_pipeline_status).
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    repl = lambda _m: f"status: {status}"  # noqa: E731

    fm = _frontmatter(text)
    if not fm:
        raise ValueError(f"no leading frontmatter (---...---) in {path}")
    new_block, n = _STATUS_RE.subn(repl, fm.group(1), count=1)
    if n == 0:
        raise ValueError(f"no 'status:' field in frontmatter of {path}")
    new_text = text[: fm.start(1)] + new_block + text[fm.end(1) :]
    p.write_text(new_text, encoding="utf-8")


# --- pipeline-status bus (one `- <role>: <status>` line per role) --------------------------------

def update_pipeline_status(path: _PathLike, role: str, status: str) -> None:
    """Update only the line for `role`; every other role's line is left as-is."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    pattern = re.compile(rf"^(-\s*{re.escape(role)}:\s*)(\S+)\s*$", re.MULTILINE)
    new_text, n = pattern.subn(lambda m: f"{m.group(1)}{status}", text, count=1)
    if n == 0:
        raise ValueError(f"no pipeline-status line for role {role!r} in {path}")
    p.write_text(new_text, encoding="utf-8")


# --- review records (append-only jsonl audit trail) ----------------------------------------------

def make_review_record(
    from_role: str,
    to_role: str,
    artifact: str,
    verdict: str,
    reasons: str,
    iteration: int,
    ts: str = "<ts>",
) -> dict:
    if verdict not in ("accept", "bounce", "reopen"):
        raise ValueError(f"verdict must be 'accept', 'bounce', or 'reopen', got {verdict!r}")
    if verdict in ("bounce", "reopen") and not reasons:
        raise ValueError(f"a {verdict} requires non-empty reasons")
    return {
        "from": from_role,
        "to": to_role,
        "artifact": artifact,
        "verdict": verdict,
        "reasons": reasons,
        "iteration": iteration,
        "ts": ts,
    }


def append_review(log_path: _PathLike, record: dict) -> None:
    p = Path(log_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def count_bounces(log_path: _PathLike, artifact: str) -> int:
    """How many times `artifact` has ALREADY been bounced or re-opened — drives the iteration counter
    so a change-request (reopen) escalates on repeated non-convergence just like a bounce."""
    p = Path(log_path)
    if not p.exists():
        return 0
    n = 0
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue  # tolerate a hand-edited / malformed line; never crash the gate
        if rec.get("artifact") == artifact and rec.get("verdict") in ("bounce", "reopen"):
            n += 1
    return n


def should_escalate(iteration: int, cap: int = 3) -> bool:
    """True when an artifact has been bounced `cap` times without converging — raise to a human."""
    return iteration >= cap


# --- thin CLI for the publish/review skills ------------------------------------------------------

def _cli() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="publish/review handoff gate")
    sub = ap.add_subparsers(dest="action", required=True)
    for name in ("publish", "accept", "bounce", "revise", "reopen"):
        sp = sub.add_parser(name)
        sp.add_argument("--artifact", required=True)
        sp.add_argument("--pipeline-status", default="memory-bank/shared/pipeline-status.md")
        sp.add_argument("--reviews-log", default="memory-bank/shared/reviews/log.jsonl")
        if name in ("publish", "revise"):
            sp.add_argument("--role", required=True)
        else:  # accept / bounce / reopen — a review action with an audit record
            sp.add_argument("--from", dest="from_role", required=True)
            sp.add_argument("--to", dest="to_role", required=True)
            sp.add_argument("--reasons", default="")
            sp.add_argument("--cap", type=int, default=3)
    args = ap.parse_args()

    current = read_status(args.artifact)
    new = next_status(current, args.action)

    if args.action in ("publish", "revise"):
        set_status(args.artifact, new)
        update_pipeline_status(args.pipeline_status, args.role, new)
        print(f"{args.action}: {args.artifact}  {current} -> {new}")
    else:
        # Build + VALIDATE the audit record BEFORE any file mutation: a failed validation (e.g. empty
        # --reasons on a bounce/reopen) must not leave status/bus changed with no record — the
        # transition is atomic w.r.t. validation (review r2 F9). iteration is DERIVED (prior
        # bounces+reopens + 1), never hand-passed, so the cap reflects reality.
        iteration = count_bounces(args.reviews_log, args.artifact) + 1
        ts = datetime.now(timezone.utc).isoformat()
        record = make_review_record(
            args.from_role, args.to_role, args.artifact, args.action, args.reasons, iteration, ts=ts
        )
        set_status(args.artifact, new)
        update_pipeline_status(args.pipeline_status, args.to_role, new)
        append_review(args.reviews_log, record)
        line = f"{args.action}: {args.artifact}  {current} -> {new}  (iteration {iteration})"
        if args.action in ("bounce", "reopen") and should_escalate(iteration, args.cap):
            line += f"  [ESCALATE: iteration {iteration} >= cap {args.cap} — raise to a human]"
        print(line)


if __name__ == "__main__":
    _cli()
