"""
task_split.py — the Senior Engineer mechanism (role-pipeline harness, new mechanism #2:
split-for-parallelism, DESIGN §8).

Two groups of pure functions:

Parallel-safety analysis — the testable guarantee for locked decision #5 (no two concurrent tasks
edit the same file):
  parse_tasks(text)            → list[dict] {id, group, files, deps} from the `### Task <id>` blocks
  find_file_collisions(tasks)  → a file owned by >1 task in ONE parallel group (not disjoint →
                                 unsafe to run concurrently)
  find_intra_group_deps(tasks) → a task depending on another task in the SAME group (a
                                 contradiction — dependent work cannot run concurrently)

Structural gate — validate before publish:
  validate_task_breakdown(text) → list[str] of problems (empty = publishable)

No domain vocabulary, no LLM, no I/O beyond the text passed in. The REASONING lives in the SKILL;
only the deterministic checks live here so they can be unit-tested. Policy (what frameworks, which
seams) comes from the architecture/roadmap the Senior reads, never hardcoded here.
"""

import re

from harness_utils import HTML_COMMENT_RE, PLACEHOLDER_RE, canonical_path, scan_placeholders

# ── shared regexes ────────────────────────────────────────────────────────────────────────────────

_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.DOTALL)
_TASK_HEADER_RE = re.compile(r"^###\s+Task\s+(\S+)", re.MULTILINE | re.IGNORECASE)

# Field forms anchored on `**Field:**` (optional opening `**`, colon REQUIRED). A line merely starting
# with the word but no colon is prose, not a field (the roadmap r2 F6r lesson, carried forward). Group 1
# captures the OPENING bold marker so _field_value strips the matching CLOSING `**` only when the field
# was actually bolded — never from an unbolded value that legitimately starts with `**` (review F3).
_FIELD_RES = {
    "group": re.compile(r"^\s*(\*{0,2})Group\s*:\s*(.*)$", re.MULTILINE | re.IGNORECASE),
    "files": re.compile(r"^\s*(\*{0,2})Files\s*:\s*(.*)$", re.MULTILINE | re.IGNORECASE),
    "deps": re.compile(r"^\s*(\*{0,2})Dependencies\s*:\s*(.*)$", re.MULTILINE | re.IGNORECASE),
    "assignee": re.compile(r"^\s*(\*{0,2})Assignee\s*:\s*(.*)$", re.MULTILINE | re.IGNORECASE),
}
_VERIFICATION_RE = re.compile(r"^\s*\*{0,2}Verification\s*:", re.MULTILINE | re.IGNORECASE)

_NONE_TOKENS = {"none", "-", "n/a", "na", ""}


def _has_fill_marker(v: str) -> bool:
    """True iff `v` contains a COMPLETE `{{...}}` fill marker — the same thing scan_placeholders
    blocks publish on. A field is treated as 'unfilled' ONLY by this predicate, so collision-safety
    never depends on a malformed/partial brace (review F1): a stray `{{` is NOT 'unfilled', so its
    real files still parse and a lone stray marker still trips the empty-ownership check."""
    return bool(PLACEHOLDER_RE.search(v))


def _fm(text: str):
    m = _FRONTMATTER_RE.match(text)
    return m.group(1) if m else None


# ── parsing ─────────────────────────────────────────────────────────────────────────────────────

def _norm_file(f: str) -> str:
    """Display form of a file path: separators normalized to '/', surrounding whitespace stripped."""
    return f.replace("\\", "/").strip()


def _filekey(f: str) -> str:
    """Conservative collision key — delegates to the shared `canonical_path` (harness_utils) so the
    Senior's collision check and the Junior's scope check decide "same file" identically.

    A *missed* collision lets two agents edit one file (catastrophic — the exact thing decision #5
    exists to prevent); an *over-flagged* collision merely forces the two tasks to run sequentially
    (harmless). `canonical_path` collapses `./`, `//`, `../` (review F2) and case-folds, mapping MORE
    spellings onto one key, never fewer — keeping the conservative bias and staying OS-invariant.
    """
    return canonical_path(f)


def _is_brace_token(tok: str) -> bool:
    """A token carrying a DOUBLE brace (`{{` or `}}`) is a fill-marker fragment, never a real file/dep
    id — drop it so a malformed marker cannot masquerade as an owned file (review F1). Keyed on the
    DOUBLE brace, not a single `{`/`}`, so a legal (if unusual) source filename like `gen{x}.py` is kept
    as a real owned file and its collision is still caught (review r2 F6) — every fill-marker form uses
    `{{`/`}}`, so this still drops all of them."""
    return "{{" in tok or "}}" in tok


def _split_files(value: str) -> list[str]:
    """Comma-separated owned files (paths may contain '/', so split on ',' only); drops none-like and
    any brace-fragment token."""
    out = []
    for part in value.split(","):
        f = _norm_file(part)
        if f and f.lower() not in _NONE_TOKENS and not _is_brace_token(f):
            out.append(f)
    return out


def _split_deps(value: str) -> list[str]:
    """Task ids this task depends on; split on commas/whitespace, drop none-like + brace-fragment."""
    out = []
    for part in re.split(r"[,\s]+", value.strip()):
        d = part.strip()
        if d and d.lower() not in _NONE_TOKENS and not _is_brace_token(d):
            out.append(d)
    return out


def _split_blocks(text: str) -> list[str]:
    """Split into per-task blocks; each kept block begins with a `### Task <id>` header."""
    blocks = re.split(r"(?=^###\s+Task\s+\S)", text, flags=re.MULTILINE | re.IGNORECASE)
    return [b for b in blocks if re.match(r"^###\s+Task\s+\S", b, re.IGNORECASE)]


def _field_value(m: "re.Match") -> str:
    """Extract a field's value from its match, stripping the CLOSING `**` of a `**Field:** value`
    bold ONLY when the field was actually bolded (group 1 == '**').

    The field regex's group 1 captures the OPENING bold; the captured value (group 2) still carries
    the closing `**`. Conditioning the strip on the opening bold means an UNBOLDED field whose value
    legitimately starts with `**` (e.g. a recursive glob `**/*.py`) is left intact (review F3).
    """
    opening, raw = m.group(1), m.group(2).strip()
    if opening == "**" and raw.startswith("**"):
        raw = raw[2:].strip()
    return raw


def parse_tasks(text: str) -> list[dict]:
    """Parse `### Task <id>` blocks into [{id, group, files, deps, files_unfilled, deps_unfilled}].

    `group` is None when absent or still a COMPLETE `{{placeholder}}`; `files`/`deps` always parse
    every VALIDLY-spelled token (brace fragments dropped), even when a placeholder co-occurs, so
    collision analysis never loses a real file (review F1). The `*_unfilled` flags fire ONLY on a
    complete `{{...}}` marker (the thing scan_placeholders blocks on) — used so the validator does not
    mistake an unfilled field for a genuinely empty one. Comments are NOT stripped here.
    """
    tasks = []
    for block in _split_blocks(text):
        tid = re.match(r"^###\s+Task\s+(\S+)", block, re.IGNORECASE).group(1)
        task = {"id": tid, "group": None, "files": [], "deps": [], "assignee": None,
                "files_unfilled": False, "deps_unfilled": False}
        g = _FIELD_RES["group"].search(block)
        if g:
            v = _field_value(g)
            task["group"] = None if (not v or _has_fill_marker(v)) else v
        f = _FIELD_RES["files"].search(block)
        if f:
            v = _field_value(f)
            task["files"] = _split_files(v)          # ALWAYS parse real files (brace fragments dropped)
            task["files_unfilled"] = _has_fill_marker(v)   # an additional flag, never a reason to drop a file
        d = _FIELD_RES["deps"].search(block)
        if d:
            v = _field_value(d)
            # deps split on whitespace, which would shred a multi-word `{{placeholder}}` into brace-less
            # words (bogus ids); so when a COMPLETE marker is present, skip parsing — scan_placeholders
            # blocks publish anyway. (Unlike files, a comma-split file token keeps its braces and drops
            # cleanly, so files can always-parse without this skip.) A malformed marker still parses.
            if _has_fill_marker(v):
                task["deps_unfilled"] = True
            else:
                task["deps"] = _split_deps(v)
        a = _FIELD_RES["assignee"].search(block)
        if a:
            v = _field_value(a)
            # optional; an absent field or an unfilled {{...}} marker leaves assignee = None
            task["assignee"] = None if (not v or _has_fill_marker(v)) else v
        tasks.append(task)
    return tasks


# ── parallel-safety analysis (locked decision #5) ───────────────────────────────────────────────

def find_file_collisions(tasks: list[dict]) -> list[dict]:
    """Files owned by >1 DISTINCT task within ONE parallel group (not disjoint → unsafe concurrency).

    Returns one record per (group, file) collision: {group, file, tasks}. Files shared across
    DIFFERENT groups are fine — those tasks are sequential, never co-edited.
    """
    collisions: list[dict] = []
    by_group: dict = {}
    for t in tasks:
        by_group.setdefault(t["group"], []).append(t)
    for group, members in by_group.items():
        owners: dict = {}  # filekey -> {"display": str, "tasks": [ids]}
        for t in members:
            for f in t["files"]:
                entry = owners.setdefault(_filekey(f), {"display": _norm_file(f), "tasks": []})
                if t["id"] not in entry["tasks"]:  # distinct tasks only (ignore a self-dup file)
                    entry["tasks"].append(t["id"])
        for entry in owners.values():
            if len(entry["tasks"]) > 1:
                collisions.append(
                    {"group": group, "file": entry["display"], "tasks": entry["tasks"]}
                )
    return collisions


def find_intra_group_deps(tasks: list[dict]) -> list[dict]:
    """A task depending on another task in the SAME parallel group — a contradiction (dependent
    work cannot run concurrently). Returns {group, task, depends_on}."""
    group_of = {t["id"]: t["group"] for t in tasks}
    conflicts: list[dict] = []
    for t in tasks:
        for dep in t["deps"]:
            if group_of.get(dep) is not None and group_of[dep] == t["group"]:
                conflicts.append({"group": t["group"], "task": t["id"], "depends_on": dep})
    return conflicts


# ── validate_task_breakdown — the structural gate ───────────────────────────────────────────────

def validate_task_breakdown(text: str) -> list[str]:
    """Return a list of structural problems with a task-breakdown (empty = publishable).

    Checks (all reported, not short-circuited): frontmatter present; ≥1 `### Task` block; each task
    declares Group/Files/Dependencies/Verification FIELDS (colon-anchored, not prose); each owns ≥1
    file; task ids unique; no dependency on an unknown id; the parallel-safety core — no file
    collision within a group (decision #5) and no dependency within a group; no unfilled {{...}}.

    The handoff `status:` field is NOT checked here — the gate owns it (same universal-gate split as
    architecture/po_brief). Structural-only: whether the split truly follows the SA's seams is the
    Senior's judgment + the consistency-gate read, not a regex.
    """
    problems: list[str] = []

    if _fm(text) is None:
        problems.append("missing leading frontmatter (---...---)")

    # structural checks run over the comment-stripped body, so a header/field that exists ONLY inside
    # an HTML comment does not satisfy them (consistent with scan_placeholders).
    body = HTML_COMMENT_RE.sub("", text)

    if not _TASK_HEADER_RE.findall(body):
        problems.append("no tasks found — the breakdown must contain at least one '### Task <id>' block")

    # per-block field-presence (anchored on the FIELD form, colon required)
    for block in _split_blocks(body):
        tid = re.match(r"^###\s+Task\s+(\S+)", block, re.IGNORECASE).group(1)
        if not _FIELD_RES["group"].search(block):
            problems.append(f"task {tid!r}: missing a 'Group:' field (its parallel group)")
        if not _FIELD_RES["files"].search(block):
            problems.append(f"task {tid!r}: missing a 'Files:' field (the files it owns)")
        if not _FIELD_RES["deps"].search(block):
            problems.append(f"task {tid!r}: missing a 'Dependencies:' field (task ids it needs, or none)")
        if not _VERIFICATION_RE.search(block):
            problems.append(f"task {tid!r}: missing a 'Verification:' field (how to confirm it is done)")

    tasks = parse_tasks(body)

    # every task must OWN at least one file (the unit of parallel work). An UNFILLED files field is
    # the placeholder scan's job, not this check's — only flag a field that is genuinely empty/none.
    for t in tasks:
        if not t["files"] and not t["files_unfilled"]:
            problems.append(f"task {t['id']!r}: declares no owned files — every task must own ≥1 file")

    # duplicate ids break dependency references and the bus
    counts: dict = {}
    for t in tasks:
        counts[t["id"]] = counts.get(t["id"], 0) + 1
    for tid, n in counts.items():
        if n > 1:
            problems.append(f"duplicate task id {tid!r} ({n}×) — task ids must be unique")

    # dependency referencing a task id that does not exist
    ids = set(counts)
    for t in tasks:
        for dep in t["deps"]:
            if dep not in ids:
                problems.append(f"task {t['id']!r}: depends on unknown task {dep!r}")

    # the parallel-safety core (decision #5)
    for c in find_file_collisions(tasks):
        problems.append(
            f"parallel-safety: file {c['file']!r} is owned by {', '.join(c['tasks'])} in the same "
            f"group {c['group']!r} — owned file sets within one group must be disjoint (or make them sequential)"
        )
    for c in find_intra_group_deps(tasks):
        problems.append(
            f"task {c['task']!r} depends on {c['depends_on']!r} but both are in group {c['group']!r} — "
            f"dependent tasks cannot run concurrently; put them in different groups"
        )

    leftover = scan_placeholders(text)
    if leftover:
        problems.append(
            "unfilled placeholder(s) remain — fill every {{...}}: " + ", ".join(leftover[:5])
        )

    return problems
