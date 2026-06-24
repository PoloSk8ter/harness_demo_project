"""
harness_utils.py — shared low-level helpers used by multiple mechanism modules.

Centralised here so the regexes never silently diverge across po_brief, architecture, or any future
validator that needs the same check.
"""

import posixpath
import re

# HTML comment strip — used before any placeholder scan so guidance comments in templates don't trip it.
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)

# Fill markers use `{{…}}`, NOT `<…>`. `<…>` collides with prose (inequalities, generics) causing
# false-denies (review r2 F9). `{{` never occurs in prose; `[^{}]` spans newlines for multi-line markers.
PLACEHOLDER_RE = re.compile(r"\{\{[^{}]+\}\}")


def scan_placeholders(text: str) -> list[str]:
    """Return unfilled `{{...}}` fill markers remaining in `text` (HTML comments stripped first).

    An empty list means no unfilled markers. Used by every artifact validator that enforces
    completeness (po_brief.validate_brief, architecture.validate_architecture, etc.).
    """
    clean = HTML_COMMENT_RE.sub("", text)
    return sorted(set(PLACEHOLDER_RE.findall(clean)))


def canonical_path(f: str) -> str:
    """Canonical identity for a file path: separators normalized to '/', surrounding whitespace
    stripped, case-folded, and `./` `//` `..` segments collapsed via posixpath.normpath.

    The collision-side path identity (task_split._filekey: two same-group tasks must not own one file).
    It case-FOLDS because collision's safe direction is to OVER-merge → over-flag → force serialization
    (harmless); a missed collision corrupts a file (catastrophic). Lexical only — no filesystem touch
    (same lineage as access_guard's containment check).

    NOT for scope checks — see scope_path, whose safe direction on the case axis is the INVERSE.
    """
    return posixpath.normpath(f.replace("\\", "/").strip().lower())


def scope_path(f: str) -> str:
    """Case-SENSITIVE path identity: separators normalized to '/', whitespace stripped, `./` `//` `..`
    collapsed via normpath — but NOT case-folded.

    The scope-side path identity (conformance_check.check_file_scope: a Junior's changed file must be
    one its task OWNS). Scope's safe direction is the INVERSE of collision's (role-harness Phase 5 F1):
    a changed file is presumed NOT owned unless it IS owned, so it must NOT case-fold — on a
    case-sensitive filesystem `src/Core.py` is a DIFFERENT file from `src/core.py` and must be flagged
    as out-of-scope (over-flagging is harmless — it just makes the Junior confirm/rename; under-flagging
    lets a Junior edit another task's case-sibling undetected, a code-level breach of decision #5).
    Differs from canonical_path on EXACTLY the case axis, deliberately, because the two checks use the
    "same file?" verdict in opposite polarity. Always case-sensitive → OS-invariant verdict.
    """
    return posixpath.normpath(f.replace("\\", "/").strip())
