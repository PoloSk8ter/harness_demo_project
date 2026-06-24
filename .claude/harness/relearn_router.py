"""
relearn_router.py — route a relearned item to its content tier + destination (role-pipeline harness).

The relern loop's deterministic brain: an item's `kind` maps to one of three tiers, and each tier has
a destination. The skill (`relearn`) does the detect/triage/net flow; this module decides WHERE a
learning lands so "what to relearn differs per user" is enforced by tier, not by ad-hoc choice.

Tiers:
- team → shared knowledge store (docs/solutions/), committed, everyone.
- role → the role lane's learnings/, shared within a role.
- user → the user-local store (~/.claude/skills/learned/), keyed by user, NEVER committed.
"""

import os

TIERS = ("team", "role", "user")
ROLES = ("po", "sa", "senior", "junior")

_KIND_TO_TIER = {
    "solution": "team",
    "root_cause": "team",
    "bugfix": "team",
    "role_instinct": "role",
    "personal": "user",
}


def classify_tier(item: dict) -> str:
    """Map a relearn item (by its `kind`) to its content tier."""
    kind = item.get("kind")
    if kind not in _KIND_TO_TIER:
        raise ValueError(f"unknown relearn kind {kind!r} — expected one of {tuple(_KIND_TO_TIER)}")
    return _KIND_TO_TIER[kind]


def destination(tier: str, role: str = None, root: str = ".", home: str = None) -> str:
    """Where a learning of `tier` is stored (posix path, no trailing slash)."""
    root = root.replace("\\", "/").rstrip("/")
    if tier == "team":
        return f"{root}/docs/solutions"
    if tier == "role":
        if not role:
            raise ValueError("the 'role' tier requires a role")
        if role not in ROLES:  # defense-in-depth: never interpolate an unvalidated role into a path
            raise ValueError(f"unknown role {role!r} — must be one of {ROLES}")
        return f"{root}/memory-bank/{role}/learnings"
    if tier == "user":
        h = (home if home is not None else os.path.expanduser("~")).replace("\\", "/").rstrip("/")
        return f"{h}/.claude/skills/learned"
    raise ValueError(f"unknown tier {tier!r} — expected one of {TIERS}")
