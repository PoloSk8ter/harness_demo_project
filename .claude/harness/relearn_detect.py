"""
relearn_detect.py — the relearn loop's Stop-hook auto-detector (role-pipeline harness, Phase 8).

Two parts:
  detect_learnings(text)  — PURE, tested: scan session text for learning signals → candidate items.
  main()                  — the Stop-hook glue: read the hook JSON on stdin, scan the last assistant
                            turn of the transcript, and STAGE each candidate into the acting role's
                            relearn queue (session.enqueue_learning). It assigns NO tier — /pause
                            triages each candidate. Fail-safe: ALWAYS exit 0 (a Stop hook must never
                            wedge or block a session).

The loop: Stop hook STAGES → /pause DRAINS (triage→route→clear) → /resume NETS undrained.
"""

import json
import re
import sys
from pathlib import Path

import access_guard
import session

# conservative success-signal triggers (case-insensitive, per line). Kept tight so false positives are
# rare; /pause is the judgment gate, so a miss is recoverable and a stray is one line to skip.
_TRIGGERS = [
    (re.compile(r"that worked", re.I), "that-worked"),
    (re.compile(r"it'?s fixed|fixed it", re.I), "fixed"),
    (re.compile(r"tests?\s+(?:now\s+)?pass(?:es)?|now passes", re.I), "tests-pass"),
    (re.compile(r"figured it out", re.I), "figured-out"),
    (re.compile(r"root cause\b", re.I), "root-cause"),
    (re.compile(r"solved it", re.I), "solved"),
]
_RED = re.compile(r"\bRED\b")
_GREEN = re.compile(r"\bGREEN\b")


def detect_learnings(text: str) -> list:
    """Scan `text` for learning signals → list of candidate items {"signal","text"}.

    Per-line phrase triggers + a whole-text RED→GREEN transition. Candidates carry NO `kind` (pause
    assigns the tier). Deduped by (signal, text) so a repeated identical trigger line yields one item.
    """
    seen = set()
    items = []

    def add(signal, line):
        key = (signal, line)
        if key not in seen:
            seen.add(key)
            items.append({"signal": signal, "text": line})

    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        for rx, label in _TRIGGERS:
            if rx.search(line):
                add(label, line)

    if _RED.search(text or "") and _GREEN.search(text or ""):
        # the RED→GREEN narrative: a reproducer went red then green — a captured fix
        green_line = next((l.strip() for l in (text or "").splitlines() if _GREEN.search(l)), "RED→GREEN")
        add("red-green", green_line)

    return items


# --- Stop-hook glue ------------------------------------------------------------------------------

def _last_assistant_text(transcript_path: str) -> str:
    """Text of the last assistant turn in a Claude Code transcript jsonl. Tolerant: a missing or
    malformed transcript → '' (the detector simply finds nothing).

    The REAL Claude Code transcript nests the message under rec["message"] (rec["message"]["role"] ==
    "assistant"), and `content` is a BLOCK LIST of {type: thinking|text|tool_use, …}. We keep only the
    `text` blocks (the visible assistant message). A flat {role, content} record is tolerated too
    (defensive), but the nested shape is what production emits."""
    p = Path(transcript_path)
    if not p.exists():
        return ""
    last = ""
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict):
            continue
        # nested (real) shape: rec["message"]; fall back to a flat rec for robustness
        msg = rec.get("message") if isinstance(rec.get("message"), dict) else rec
        if not isinstance(msg, dict) or msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        if isinstance(content, list):  # block list → keep ONLY the text blocks
            text = " ".join(b.get("text", "") for b in content
                            if isinstance(b, dict) and b.get("type") == "text")
        elif isinstance(content, str):
            text = content
        else:
            text = msg.get("text", "") if isinstance(msg.get("text"), str) else ""
        if text:
            last = text
    return last


def main() -> None:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
        transcript = data.get("transcript_path", "") if isinstance(data, dict) else ""
        text = _last_assistant_text(transcript) if transcript else ""
        items = detect_learnings(text)
        if items:
            # per-instance .claude/role wins; HARNESS-CONTEXT acting_as = fallback (same as the guard)
            role, _name = access_guard.read_role(Path.cwd())
            if role:  # can't stage without a lane — skip silently if the role is unset
                for it in items:
                    session.enqueue_learning(role, it)
    except Exception:  # noqa: BLE001 — fail-safe: a Stop hook must never wedge or block a session
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
