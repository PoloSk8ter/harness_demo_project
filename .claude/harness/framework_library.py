"""
framework_library.py — the company framework-library reader (role-pipeline harness, new mechanism #3).

The framework library is a standalone, versioned repo (design §7). Each framework is a directory:
    <library_root>/<framework>/
        ALLOWED          # presence of this marker = on the allowlist (the SA may design with it)
        conventions.md   # how this company writes it (read by the Junior)
        exemplars/       # canonical snippets (read by the Junior)

The SA reads it as an allowlist (`is_allowed` / `check_allowlist`); the Junior locates the how-to
assets (`conventions_path` / `exemplars_path`). All name->path lookups are TRAVERSAL-SAFE and
fail-closed: an unsafe framework name is never "allowed" and never resolves to a path (same discipline
as access_guard — a name fed to the filesystem is exactly where a bypass hides). No domain vocabulary;
no hardcoded framework, stack, or path — the root comes from HARNESS-CONTEXT `framework_library.path`.
"""

import re
from pathlib import Path

# A framework name is a single safe directory segment. The positive allowlist rejects path separators
# and drive/colon forms; the explicit `.`/`..` reject closes the parent-ref hole (which would match the
# regex because `.` is permitted). Anything else -> None -> fail-closed (not allowed, no path).
_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9._+-]+$")


def _clean_framework_name(name) -> str | None:
    if not isinstance(name, str):
        return None
    n = name.strip()
    if n in ("", ".", "..") or not _SAFE_NAME_RE.match(n):
        return None
    return n


# All lookups match names EXACTLY against the real on-disk entries, never via `Path(...).is_file()`,
# whose case-folding differs by OS (Windows folds, Linux does not). Matching `d.name == n` makes the
# allowlist IDENTICAL on Windows and Linux — a library authored on one OS resolves the same on CI.

def _entry_dir(library_root, name: str):
    """The child directory of `library_root` named EXACTLY `name`, or None — so `ALLOWED-FW` cannot
    resolve to `allowed-fw` via Windows case-folding (review F2)."""
    root = Path(library_root)
    if not root.is_dir():
        return None
    return next((d for d in root.iterdir() if d.is_dir() and d.name == name), None)


def _has_marker(entry_dir) -> bool:
    """True iff `entry_dir` holds a file named EXACTLY `ALLOWED` (not `allowed`/`Allowed`) — review F1."""
    return any(c.name == "ALLOWED" and c.is_file() for c in entry_dir.iterdir())


def is_allowed(framework, library_root) -> bool:
    """True iff `<library_root>/<framework>/ALLOWED` exists by EXACT name. Unsafe names fail-closed."""
    n = _clean_framework_name(framework)
    if n is None:
        return False
    d = _entry_dir(library_root, n)
    return d is not None and _has_marker(d)


def list_allowed(library_root) -> list[str]:
    """Every framework on the allowlist (directories carrying an exact `ALLOWED` marker), sorted."""
    root = Path(library_root)
    if not root.is_dir():
        return []
    return sorted(d.name for d in root.iterdir() if d.is_dir() and _has_marker(d))


def check_allowlist(frameworks, library_root) -> list[str]:
    """The frameworks NOT on the allowlist (violations). Empty list = all allowed. An unsafe name can
    never be allowed, so it is always reported as a violation, never silently accepted."""
    return [f for f in frameworks if not is_allowed(f, library_root)]


def _entry_child(framework, library_root, child_name: str, want_dir: bool) -> str | None:
    n = _clean_framework_name(framework)
    if n is None:
        return None
    d = _entry_dir(library_root, n)
    if d is None:
        return None
    pred = (lambda c: c.is_dir()) if want_dir else (lambda c: c.is_file())
    return next((str(c) for c in d.iterdir() if c.name == child_name and pred(c)), None)


def conventions_path(framework, library_root) -> str | None:
    """Path to a framework's `conventions.md` (exact name), or None if unsafe/absent."""
    return _entry_child(framework, library_root, "conventions.md", want_dir=False)


def exemplars_path(framework, library_root) -> str | None:
    """Path to a framework's `exemplars/` dir (exact name), or None if unsafe/absent."""
    return _entry_child(framework, library_root, "exemplars", want_dir=True)
