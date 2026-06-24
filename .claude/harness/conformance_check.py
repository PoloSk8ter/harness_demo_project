"""
conformance_check.py — the Junior Engineer mechanism (role-pipeline harness, DESIGN §4/§7/§9, §5.1).

Two pure structural checks the Junior runs before shipping:

  check_file_scope(changed_files, owned_files) → the files the Junior changed that are NOT in its
    task's owned set — the CODE-level enforcement of locked decision #5 (§5.1). access_guard already
    blocks writes outside the lane / source_dirs, but it does NOT know the per-TASK owned set; this
    does. Shares harness_utils.canonical_path with the Senior's collision key so "same file" is decided
    identically on both sides of the boundary.
  validate_completion_record(text) → structural problems with the Junior's ship artifact (empty = ok).

The SEMANTIC conformance — does the code violate a locked ADR or a library convention (§9/§7) — is the
Junior's READ (prose, in the conformance-check SKILL); the library-allowlist half reuses
framework_library.check_allowlist. Only the deterministic structural checks live here. No domain
vocabulary, no LLM, no I/O beyond the text/lists passed in.
"""

import re

from harness_utils import HTML_COMMENT_RE, scan_placeholders, scope_path

# ── check_file_scope (locked decision #5, code level) ───────────────────────────────────────────


def _display(f: str) -> str:
    """Readable form of a path for the violation message: separators normalized, whitespace stripped."""
    return f.replace("\\", "/").strip()


def check_file_scope(changed_files, owned_files) -> list[str]:
    """Return the changed files NOT owned by the task (sorted, display form) — a code-boundary
    violation (decision #5). An empty list means every change is in-scope.

    Comparison uses `scope_path` — a CASE-SENSITIVE identity (separator/`.`/`..` normalized, NOT
    case-folded). A same-case alias of an owned file (`./src/core.py` ≡ `src/core.py`) is the same file
    and is NOT flagged; but a CASE variant (`src/Core.py` vs owned `src/core.py`) is a different file on
    a case-sensitive FS and IS flagged. Scope's safe direction is the INVERSE of the collision key's:
    here under-flagging is catastrophic (a Junior edits another task's file undetected), so the check
    errs toward flagging — which is why it must NOT reuse the case-folding canonical_path (Phase 5 F1).
    """
    owned = {scope_path(f) for f in owned_files}
    return sorted({_display(f) for f in changed_files if scope_path(f) not in owned})


# ── validate_completion_record ──────────────────────────────────────────────────────────────────

_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.DOTALL)

REQUIRED_RECORD_SECTIONS: list[str] = ["Task", "Files Changed", "Tests", "Conformance"]


def _has_section(text: str, name: str) -> bool:
    return bool(re.search(rf"^#{{1,6}}\s*{re.escape(name)}\s*$", text, re.MULTILINE | re.IGNORECASE))


def validate_completion_record(text: str) -> list[str]:
    """Return structural problems with a Junior completion record (empty = publishable).

    Checks (all reported): leading frontmatter present; the 4 required sections (Task / Files Changed /
    Tests / Conformance) present over the comment-stripped body; no unfilled {{...}}. The handoff
    `status:` field is the gate's, not checked here (same universal-gate split as the other validators).
    """
    problems: list[str] = []

    if not _FRONTMATTER_RE.match(text):
        problems.append("missing leading frontmatter (---...---)")

    # section checks run over the comment-stripped body, so a header present ONLY inside an HTML comment
    # does not satisfy them (consistent with scan_placeholders).
    body = HTML_COMMENT_RE.sub("", text)
    for name in REQUIRED_RECORD_SECTIONS:
        if not _has_section(body, name):
            problems.append(f"missing required section: {name!r}")

    leftover = scan_placeholders(text)
    if leftover:
        problems.append(
            "unfilled placeholder(s) remain — fill every {{...}}: " + ", ".join(leftover[:5])
        )

    return problems
