"""
access_guard.py — role-access guard (role-pipeline harness, new mechanism #5).

A PreToolUse hook on Edit/Write that mechanically PROHIBITS a role from writing outside its lane and
owned shared files (the access matrix in CLAUDE.md §5.1). The authorization logic is pure + tested;
the hook glue reads the tool input from stdin and the acting role from HARNESS-CONTEXT.md.

Fail-closed EVERYWHERE: unset / unknown / ambiguous role denies; a path that lexically escapes the repo
(`..`) or is absolute-outside-repo is denied; an Edit/Write payload that is empty, non-JSON, non-object,
or path-less is denied; and any unexpected error denies (exit 2). PreToolUse semantics: exit 2 BLOCKS;
exit 1 / other non-zero is NON-blocking — so the guard must only ever exit 0 (allow) or 2 (deny).

Limitation (lexical): containment is checked lexically. A symlink INSIDE a lane that points outside it
(`memory-bank/po/link -> ../../sa`) is not detected — paths are not realpath-resolved (that would touch
the filesystem and only work for existing paths). Shared status files (pipeline-status.md,
reviews/log.jsonl) are written only by the publish/review gate via Python I/O (not Edit/Write), so they
are never intercepted and are denied to direct edits by design.
"""

import json
import posixpath
import re
import sys
from pathlib import Path

ROLES = ("po", "sa", "senior", "junior")


def _clean_relpath(path: str):
    """Lexically normalize to a repo-relative posix path. None if it escapes the repo or is absolute."""
    p = posixpath.normpath(path.replace("\\", "/"))
    if posixpath.isabs(p) or p == ".." or p.startswith("../") or p == ".":
        return None
    return p


def _under(path: str, prefix: str) -> bool:
    """True if `path` is a file under directory `prefix` (collision-safe: prefix ends with '/')."""
    prefix = prefix.rstrip("/") + "/"
    return path.startswith(prefix)


def allowed_write(role: str, path: str, source_dirs) -> bool:
    """Pure authorization: may `role` write `path`? Normalizes `..`/`.` first so traversal can't escape."""
    p = _clean_relpath(path)
    if p is None:
        return False  # escaped the repo or absolute → never a writable lane path
    if p == "memory-bank/shared/CONTEXT.md":
        return True  # the glossary — the one shared file all roles maintain (grill), per DESIGN §5.1
    if role == "po":
        return (
            _under(p, "memory-bank/po/")
            or p == "memory-bank/shared/product-brief.md"
            or _under(p, "memory-bank/shared/specs/")
            or p == "memory-bank/shared/decision-log.md"
        )
    if role == "sa":
        return (
            _under(p, "memory-bank/sa/")
            or p == "memory-bank/shared/architecture.md"
            or _under(p, "memory-bank/shared/docs/adr/")
            or p == "memory-bank/shared/roadmap.md"
        )
    if role == "senior":
        return _under(p, "memory-bank/senior/") or bool(
            re.fullmatch(r"memory-bank/shared/phases/.+/PLAN\.md", p)  # require a phase subdir (DESIGN §5)
        )
    if role == "junior":
        if _under(p, "memory-bank/junior/") or _under(p, "memory-bank/shared/completions/"):
            return True  # private lane + its shared ship records (the gate-accepted completion artifact)
        return any(_under(p, d) for d in (source_dirs or []))
    return False


def decide(role: str, path: str, source_dirs):
    """Return (allow, reason). Unset/unknown role and repo-escaping paths fail closed."""
    if not role:
        return False, "acting_as is unset/ambiguous in HARNESS-CONTEXT.md — set your role before writing."
    if role not in ROLES:
        return False, f"unknown role {role!r} — must be one of {ROLES}."
    if allowed_write(role, path, source_dirs):
        return True, "ok"
    return False, (
        f"role {role!r} may not write {path} — outside its lane/owned files (or escapes the repo). "
        "See the access matrix in CLAUDE.md; shared status goes through the publish/review gate."
    )


def parse_context(text: str):
    """Read `acting_as` and `source_dirs`. Zero or >1 acting_as lines => unset (fail closed)."""
    role = None
    acting = re.findall(r"^- acting_as:\s*(\S+)", text, re.MULTILINE)
    if len(acting) == 1 and acting[0].lower() in ROLES:  # case-insensitive; placeholder stays unset
        role = acting[0].lower()
    src = []
    m = re.search(r"^- source_dirs:\s*(.+)$", text, re.MULTILINE)
    if m:
        src = [
            s.strip().rstrip("/") + "/"
            for s in re.split(r"[,\s]+", m.group(1).strip())
            if s.strip() and not s.startswith("<")
        ]
    return role, src


def parse_role(text: str):
    """Read (role, name) from a `.claude/role` file (the per-instance role, written by `apply --role`).

    Lines are `acting_as: <role>` / `name: <name>`, with an optional leading `- `. Role is
    case-insensitive and must be a known ROLE; zero/>1 acting_as lines or a placeholder => role None
    (fail-closed, same discipline as parse_context). Returns (role|None, name|None)."""
    role = None
    acting = re.findall(r"^-?\s*acting_as:\s*(\S+)", text, re.MULTILINE)
    if len(acting) == 1 and acting[0].lower() in ROLES:
        role = acting[0].lower()
    names = re.findall(r"^-?\s*name:\s*(\S+)", text, re.MULTILINE)
    name = names[0] if (len(names) == 1 and not names[0].startswith("<")) else None
    return role, name


def read_role(root="."):
    """Resolve (role, name) for THIS instance. Precedence (Option B):

      1. a gitignored `<root>/.claude/role` (written by `apply --role`) — per-instance, wins.
      2. else fall back to `HARNESS-CONTEXT.md` `acting_as` (the SOLO/manual path; carries no name here).
      3. neither → (None, None) — fail-closed (the guard then denies every write).

    The per-instance file is why adoption is install-and-go and can't pollute the team's committed
    HARNESS-CONTEXT.md (the role rides a gitignored file, like `.claude/skills/`)."""
    root = Path(root)
    rolefile = root / ".claude" / "role"
    if rolefile.exists():
        role, name = parse_role(rolefile.read_text(encoding="utf-8", errors="replace"))
        if role:
            return role, name
    ctx = root / "HARNESS-CONTEXT.md"
    if ctx.exists():
        role, _src = parse_context(ctx.read_text(encoding="utf-8", errors="replace"))
        if role:
            return role, None
    return None, None


def _norm(file_path: str, root: Path) -> str:
    """Strip the repo-root prefix (boundary-anchored, case-insensitive). A path NOT under root is left
    as-is — so an out-of-repo absolute path stays absolute and `_clean_relpath` rejects it."""
    p = file_path.replace("\\", "/")
    root_s = str(root).replace("\\", "/").rstrip("/")
    if p.lower().startswith(root_s.lower() + "/"):
        return p[len(root_s) + 1:]
    return p


def _guard() -> None:
    raw = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()
    if not raw.strip():
        print("[role-access-guard] DENY: empty payload (fail-closed).", file=sys.stderr)
        sys.exit(2)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("[role-access-guard] DENY: unparseable Edit/Write payload (fail-closed).", file=sys.stderr)
        sys.exit(2)
    if not isinstance(data, dict):
        print("[role-access-guard] DENY: payload is not an object (fail-closed).", file=sys.stderr)
        sys.exit(2)
    file_path = (data.get("tool_input") or {}).get("file_path") or data.get("file_path")
    if not file_path:
        print("[role-access-guard] DENY: Edit/Write with no file_path (fail-closed).", file=sys.stderr)
        sys.exit(2)

    root = Path.cwd()
    role, _name = read_role(root)  # per-instance .claude/role wins; HARNESS-CONTEXT acting_as = fallback
    src = []
    ctx = root / "HARNESS-CONTEXT.md"
    if ctx.exists():  # source_dirs is project policy → always from HARNESS-CONTEXT (never the role file)
        _r, src = parse_context(ctx.read_text(encoding="utf-8", errors="replace"))

    allow, reason = decide(role, _norm(file_path, root), src)
    if not allow:
        print(f"[role-access-guard] DENY: {reason}", file=sys.stderr)
        sys.exit(2)  # exit 2 = block
    sys.exit(0)


def main() -> None:
    try:
        _guard()
    except SystemExit:
        raise  # preserve intentional exit(0)/exit(2)
    except Exception as e:  # noqa: BLE001 — fail-closed is the contract
        print(f"[role-access-guard] DENY: guard error ({type(e).__name__}) — fail-closed.", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
