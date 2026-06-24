"""
architecture.py — the Solution Architect mechanism (role-pipeline harness, new mechanism #4).

Three groups of pure functions:

Lock / version
  parse_lock(text)         → (status, version) from the leading frontmatter
  bump_version(version)    → v(N+1)  — used when the SA amends + re-locks after a change-request

Structural gate — validate before publish
  validate_architecture(text, frameworks, library_root) → list[str] of problems
  validate_roadmap(text)                                → list[str] of problems

No domain vocabulary, no LLM, no I/O beyond the text passed in. The REASONING lives in the SKILL;
only the deterministic checks live here so they can be unit-tested. Policy (thresholds, allowed
statuses) comes from the caller / HARNESS-CONTEXT, never hardcoded here.
"""

import re
from typing import Optional

from framework_library import check_allowlist
from harness_utils import HTML_COMMENT_RE, scan_placeholders

# ── shared helpers ────────────────────────────────────────────────────────────────────────────────

_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.DOTALL)


def _fm(text: str) -> Optional[str]:
    m = _FRONTMATTER_RE.match(text)
    return m.group(1) if m else None


def _fm_field(block: str, key: str) -> Optional[str]:
    m = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", block, re.MULTILINE)
    return m.group(1) if m else None


def _has_section(text: str, name: str) -> bool:
    return bool(re.search(rf"^#{{1,6}}\s*{re.escape(name)}\s*$", text, re.MULTILINE | re.IGNORECASE))


# ── lock / version ────────────────────────────────────────────────────────────────────────────────

def parse_lock(text: str) -> tuple[str, str]:
    """Return (lock, version) from the leading YAML frontmatter.

    The architecture's LOCK lives in its own `lock:` field — NOT in `status:`, which is the universal
    handoff lifecycle (draft→ready→accepted) the gate manages. The two are orthogonal: an architecture
    can be `status: draft` (not yet published) while `lock: locked` (the SA has committed to the design).

    Raises ValueError if the frontmatter is absent, or if `lock` or `version` is missing.
    """
    block = _fm(text)
    if block is None:
        raise ValueError("no leading frontmatter (---...---) found")
    lock = _fm_field(block, "lock")
    if lock is None:
        raise ValueError("frontmatter missing 'lock'")
    version = _fm_field(block, "version")
    if version is None:
        raise ValueError("frontmatter missing 'version'")
    return lock, version


_VERSION_RE = re.compile(r"^v(\d+)$")


def bump_version(version: str) -> str:
    """Return v(N+1). Raises ValueError if `version` is not in the form `vN`."""
    m = _VERSION_RE.match(version)
    if not m:
        raise ValueError(f"version must be in the form 'vN' (e.g. v1), got {version!r}")
    return f"v{int(m.group(1)) + 1}"


# ── validate_architecture ─────────────────────────────────────────────────────────────────────────

REQUIRED_ARCH_SECTIONS: list[str] = [
    "Overview",
    "Module Seams",
    "Stack",
    "Invariants",
    "Architecture Decisions",
]


def validate_architecture(
    text: str,
    frameworks: Optional[list[str]] = None,
    library_root: Optional[str] = None,
) -> list[str]:
    """Return a list of structural problems with an architecture artifact (empty = publishable).

    Checks (all reported, not short-circuited): frontmatter present with lock=locked and a version;
    5 required sections; at least one ADR-NNNN reference; every framework in `frameworks` is on the
    allowlist (when `library_root` provided); no unfilled {{...}} placeholders.

    The handoff `status:` field (draft→ready) is NOT checked here — the gate owns it. The architecture's
    own commitment state is the separate `lock:` field (DESIGN §9), which is what this validates.

    `frameworks` is supplied by the SA skill (extracted from the Stack section); the mechanism never
    parses the document for framework names — that keeps mechanism/policy separate (DESIGN §3).
    """
    problems: list[str] = []

    block = _fm(text)
    if block is None:
        problems.append("missing leading frontmatter (---...---)")
        block = ""

    lock = _fm_field(block, "lock")
    if lock is None:
        problems.append("frontmatter missing 'lock' (set lock: locked once the design is committed)")
    elif lock != "locked":
        problems.append(f"architecture must be lock: locked before publish, got {lock!r}")

    version = _fm_field(block, "version")
    if version is None:
        problems.append("frontmatter missing 'version' (e.g. version: v1)")
    elif not _VERSION_RE.match(version):
        problems.append(f"version must be in the form 'vN', got {version!r}")

    # section + ADR checks run over the comment-stripped body, so a header/ref that exists ONLY inside
    # an HTML comment does not satisfy them (consistent with scan_placeholders). Code-fence blindness is
    # an accepted residual (matches po_brief's accepted fence residual).
    body = HTML_COMMENT_RE.sub("", text)

    for name in REQUIRED_ARCH_SECTIONS:
        if not _has_section(body, name):
            problems.append(f"missing required section: {name!r}")

    # presence check: at least one ADR is referenced. `ADR-\d+` (case-insensitive) accepts ADR-1 and
    # adr-0001 — the 4-digit zero-pad is a filename convention, not a presence requirement.
    if not re.search(r"ADR-\d+", body, re.IGNORECASE):
        problems.append("no ADR reference found (reference at least one ADR, e.g. ADR-0001)")

    if frameworks:
        if not library_root:
            # fail closed — never silently skip the allowlist (the 3a spine) on caller misconfig.
            problems.append(
                "frameworks given but no library_root — cannot allowlist-check "
                "(set framework_library.path in HARNESS-CONTEXT)"
            )
        else:
            violations = check_allowlist(frameworks, library_root)
            if violations:
                problems.append(f"framework(s) not on the allowlist: {', '.join(violations)}")

    leftover = scan_placeholders(text)
    if leftover:
        problems.append(
            "unfilled placeholder(s) remain — fill every {{...}}: " + ", ".join(leftover[:5])
        )

    return problems


# ── validate_roadmap ──────────────────────────────────────────────────────────────────────────────

def validate_roadmap(text: str) -> list[str]:
    """Return a list of structural problems with a phase roadmap (empty = publishable).

    Checks: at least one `### Phase` entry present; each phase declares an `Increment` and a
    `Verification` FIELD (a line like `**Increment:**`, not just the word in prose — structural-only,
    semantic quality is the Senior's job); no unfilled {{...}} placeholders. A `### Phase` line inside a
    code fence is still counted (accepted residual, matches po_brief).
    """
    problems: list[str] = []

    phase_headers = re.findall(
        r"^###\s+Phase\s+\S", text, re.MULTILINE | re.IGNORECASE
    )
    if not phase_headers:
        problems.append("no phases found — roadmap must contain at least one '### Phase N' entry")

    # check each phase block for an Increment FIELD and a Verification FIELD (anchored on the field
    # marker `**Increment:**` / `**Verification:**`, optionally with leading `*`, NOT incidental prose).
    phase_blocks = re.split(r"(?=^###\s+Phase\s+\S)", text, flags=re.MULTILINE | re.IGNORECASE)
    for block in phase_blocks:
        if not re.search(r"^###\s+Phase\s+\S", block, re.MULTILINE | re.IGNORECASE):
            continue
        header_m = re.search(r"^###\s+(Phase[^\n]+)", block, re.MULTILINE | re.IGNORECASE)
        label = header_m.group(1).strip() if header_m else "unknown"
        # anchor on the FIELD form `**Increment:**` (optional `*`, trailing colon) — a line merely
        # starting with the word but no colon is prose, not a field (review r2 F6r).
        if not re.search(r"^\s*\*{0,2}Increment\s*:", block, re.MULTILINE | re.IGNORECASE):
            problems.append(f"{label!r}: missing an 'Increment:' field (what is deliverable in this phase)")
        if not re.search(r"^\s*\*{0,2}Verification\s*:", block, re.MULTILINE | re.IGNORECASE):
            problems.append(f"{label!r}: missing a 'Verification:' field (how to confirm this phase is done)")

    leftover = scan_placeholders(text)
    if leftover:
        problems.append(
            "unfilled placeholder(s) remain — fill every {{...}}: " + ", ".join(leftover[:5])
        )

    return problems
