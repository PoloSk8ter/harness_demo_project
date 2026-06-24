"""apply_harness.py — install the role-pipeline harness into an existing project's .claude/ (Phase 7).

Two tiers:
  SHARED (always): harness/ mechanisms → .claude/harness/, the guard hook MERGED into .claude/settings.json,
    memory-bank/ templates, HARNESS-CONTEXT.template.md → HARNESS-CONTEXT.md (if absent), the CLAUDE.md block.
  ROLE (--role):   ONLY that role's mapped skills → .claude/skills/, which is gitignored so per-role
    capability scoping survives every branch merge (committed skills would be unified on merge → propagate).

Idempotent: re-running never duplicates the hook or the .gitignore line, and never clobbers existing
settings/skills/context. The 2-remote / one-way subtree update model is documented in docs/ADOPTION.md.

Usage:  python apply_harness.py <target-project-root> --role junior
        python apply_harness.py <target-project-root>            # omit --role = all skills (solo mode)
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

# CORE = the universal primitives every role composes; role-specific skills are added per role.
# `init` is universal: it does the brownfield project intake (detect stack + seed the allowlist); on a
# greenfield repo it is a no-op (the SA writes the stack at /architect). The per-instance ROLE is NOT a
# skill — `apply --role` writes it to the gitignored .claude/role, read by access_guard.read_role.
CORE = {"grill", "research", "refute", "brainstorm", "relearn", "publish", "review", "board",
        "resume", "pause", "destale", "init"}
ROLE_SKILLS = {
    "po": CORE | {"validate"},
    "sa": CORE | {"architect", "seams", "vet-lib"},
    "senior": CORE | {"split", "check", "replan"},
    "junior": CORE | {"tdd", "code-review", "investigate", "conform", "ship", "build"},
}
ALL_SKILLS = CORE.union(*ROLE_SKILLS.values())

GITIGNORE_LINE = ".claude/skills/"
# the per-lane relearn queue stages candidate learnings (some user-tier) before /pause routes them —
# keep it out of git so a staged personal item never rides a branch.
RELEARN_QUEUE_GLOB = "**/.relearn-queue.jsonl"
# the per-instance role (Option B) — gitignored like .claude/skills/, so one dev's role can't ride a
# commit and flip the whole team's. Written by `apply --role`, read by access_guard.read_role.
ROLE_FILE_LINE = ".claude/role"
CLAUDE_MARKER = "<!-- role-harness -->"


def skills_for(role):
    """The set of skill names a role installs. role None/'all' → every skill (solo/sequential mode)."""
    if role in (None, "all"):
        return set(ALL_SKILLS)
    if role not in ROLE_SKILLS:
        raise ValueError(f"unknown role {role!r} — one of {sorted(ROLE_SKILLS)} or None/'all'")
    return set(ROLE_SKILLS[role])


def _copy_harness(src_root: Path, claude_dir: Path) -> None:
    dst = claude_dir / "harness"
    dst.mkdir(parents=True, exist_ok=True)
    for py in (src_root / "harness").glob("*.py"):   # flat glob — never ships harness/tests/
        shutil.copy2(py, dst / py.name)


def _copy_skills(src_root: Path, claude_dir: Path, role) -> None:
    dst = claude_dir / "skills"
    for name in sorted(skills_for(role)):
        d = dst / name
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_root / "skills" / name / "SKILL.md", d / "SKILL.md")


def _merge_hook(src_root: Path, claude_dir: Path) -> None:
    """Merge EVERY hook event in the template (the PreToolUse access guard + the Stop relearn-detector)
    into the project's settings.json, idempotently (membership by command). Never clobbers existing
    hooks; re-running adds nothing already wired."""
    template = json.loads((src_root / ".claude" / "settings.template.json").read_text(encoding="utf-8"))
    settings_path = claude_dir / "settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.exists() else {}
    hooks = settings.setdefault("hooks", {})
    for event, entries in template.get("hooks", {}).items():
        bucket = hooks.setdefault(event, [])
        present = {h.get("command") for e in bucket for h in e.get("hooks", [])}
        for entry in entries:
            cmds = {h.get("command") for h in entry.get("hooks", [])}
            if not (cmds & present):  # none of this entry's commands are wired yet
                bucket.append(entry)
                present |= cmds
    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")


def _copy_tree_if_absent(src: Path, dst: Path) -> None:
    """Copy a directory tree, skipping any file that already exists in dst (never clobber the user's work)."""
    if not src.exists():
        return
    for item in src.rglob("*"):
        if item.is_dir() or "__pycache__" in item.parts or item.suffix == ".pyc":
            continue
        target = dst / item.relative_to(src)
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)


def _write_role_file(claude_dir: Path, role: str) -> None:
    """Write the per-instance role to `.claude/role`, (re)setting only the `acting_as:` line and
    PRESERVING every other line — notably a user-added `name:` (the docs invite one). The documented
    update flow re-runs `apply --role`, so an unconditional overwrite would silently wipe the name and
    degrade `resume`; this keeps it."""
    rf = claude_dir / "role"
    lines = rf.read_text(encoding="utf-8").splitlines() if rf.exists() else []
    out, seen = [], False
    for ln in lines:
        if re.match(r"^\s*-?\s*acting_as:", ln):
            out.append(f"acting_as: {role}")
            seen = True
        else:
            out.append(ln)
    if not seen:
        out.insert(0, f"acting_as: {role}")
    rf.write_text("\n".join(out) + "\n", encoding="utf-8")


def _ensure_gitignore(target_root: Path) -> None:
    gi = target_root / ".gitignore"
    text = gi.read_text(encoding="utf-8") if gi.exists() else ""
    lines = text.splitlines()
    to_add = [ln for ln in (GITIGNORE_LINE, RELEARN_QUEUE_GLOB, ROLE_FILE_LINE) if ln not in lines]
    if not to_add:
        return
    prefix = (text.rstrip("\n") + "\n") if text.strip() else ""
    gi.write_text(prefix + "\n".join(to_add) + "\n", encoding="utf-8")


def _append_claude_block(src_root: Path, target_root: Path) -> None:
    block_path = src_root / "CLAUDE.md.template"
    if not block_path.exists():
        return
    block = block_path.read_text(encoding="utf-8")
    claude = target_root / "CLAUDE.md"
    existing = claude.read_text(encoding="utf-8") if claude.exists() else ""
    if CLAUDE_MARKER in existing or block.strip() and block.strip() in existing:
        return
    prefix = (existing.rstrip("\n") + "\n\n") if existing.strip() else ""
    claude.write_text(prefix + block, encoding="utf-8")


def apply(src_root, target_root, role=None) -> None:
    """Install the harness into target_root: SHARED tier always, ROLE tier per `role`."""
    src_root, target_root = Path(src_root), Path(target_root)
    skills_for(role)  # validate the role up front (fail fast on an unknown role)
    claude_dir = target_root / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    # SHARED tier
    _copy_harness(src_root, claude_dir)
    _merge_hook(src_root, claude_dir)
    _copy_tree_if_absent(src_root / "memory-bank", target_root / "memory-bank")
    ctx_template, ctx = src_root / "HARNESS-CONTEXT.template.md", target_root / "HARNESS-CONTEXT.md"
    if ctx_template.exists() and not ctx.exists():
        shutil.copy2(ctx_template, ctx)
    _append_claude_block(src_root, target_root)

    # ROLE tier (+ gitignore so it never rides a branch)
    _copy_skills(src_root, claude_dir, role)
    if role in ROLE_SKILLS:  # a REAL role only — not None (solo) and not the "all" alias (would write a
        _write_role_file(claude_dir, role)  # bogus `acting_as: all` the guard then rejects. Install-and-go.
    _ensure_gitignore(target_root)


def _cli(argv) -> None:
    ap = argparse.ArgumentParser(description="Install the role-pipeline harness into a project's .claude/")
    ap.add_argument("target", help="path to the target project root")
    ap.add_argument("--role", default=None, help="po|sa|senior|junior (omit = all skills, solo/sequential)")
    ap.add_argument("--src", default=str(Path(__file__).resolve().parent.parent),
                    help="harness source root (defaults to this checkout)")
    ns = ap.parse_args(argv)
    apply(ns.src, ns.target, role=ns.role)
    print(f"[apply_harness] installed role={ns.role or 'all'} into {ns.target}/.claude")


if __name__ == "__main__":
    _cli(sys.argv[1:])
