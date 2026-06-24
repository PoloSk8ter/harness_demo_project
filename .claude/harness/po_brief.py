"""
po_brief.py — Product Owner pack mechanism (role-pipeline harness, Phase 2).

Two pure functions the `validate-product` PO pipeline composes:
- clarity_score(goal, constraints, criteria): the weighted clarity metric (live validate-idea A5),
  on a /10 scale.
- validate_brief(text, min_clarity): a structural completeness gate over a product-brief's markdown —
  returns a list of problem strings (empty = well-formed and publishable).

Domain-neutral: no domain vocabulary, no LLM, no I/O beyond the passed text. The REASONING lives in
the SKILL.md; only the deterministic checks live here, so they can be unit-tested. The required
section list below is the single source of truth shared with product-brief.template.md.
"""

import math
import re

from harness_utils import HTML_COMMENT_RE, scan_placeholders  # shared placeholder helpers

# --- clarity_score ------------------------------------------------------------------------------

_WEIGHTS = (0.40, 0.30, 0.30)  # goal, constraints, criteria — must sum to 1.0


def _clamp(x: float, lo: float = 0.0, hi: float = 10.0) -> float:
    v = float(x)
    if not math.isfinite(v):  # reject NaN/inf rather than silently clamping NaN UP to the max (10)
        raise ValueError(f"clarity sub-score must be a finite number, got {x!r}")
    return max(lo, min(hi, v))


def read_min_clarity(context_text: str, default: float = 7.0) -> float:
    """Read the publish clarity threshold from HARNESS-CONTEXT text (policy lives in data, not here).

    Looks for a `min_clarity: <n>` line (optionally a `- ` list item). Fails SAFE to `default` in every
    ambiguous case — no slot, a value inside an HTML comment, or an unparseable / negative value — so a
    misconfigured threshold never crashes the gate and the mechanism stays project-overridable.
    """
    text = HTML_COMMENT_RE.sub("", context_text)  # never read a commented-out value as policy
    m = re.search(r"^\s*-?\s*min_clarity:\s*(\S+)", text, re.MULTILINE)
    if not m:
        return default
    try:
        value = float(m.group(1))
    except ValueError:
        return default  # garbage like "8.0.0" falls back instead of raising an uncaught traceback
    return value if value >= 0 else default


def clarity_score(goal: float, constraints: float, criteria: float) -> float:
    """Weighted clarity on a /10 scale: goal 0.40, constraints 0.30, criteria 0.30.

    Each input is clamped to [0, 10] and the result is rounded to one decimal. This is the
    deterministic half of validate-idea A5 — the prose judgment that produces the three sub-scores
    lives in the skill; the arithmetic lives here.
    """
    g, c, k = _clamp(goal), _clamp(constraints), _clamp(criteria)
    wg, wc, wk = _WEIGHTS
    return round(g * wg + c * wc + k * wk, 1)


# --- validate_brief -----------------------------------------------------------------------------

# Single source of truth for the brief skeleton — product-brief.template.md MUST carry exactly these
# section headers (T5 asserts the template ↔ this list stay in sync, killing schema-last drift).
REQUIRED_SECTIONS: list[str] = [
    "Idea",
    "Who It's For",
    "What It Must Do",
    "How It Should Work",
    "Evidence",
    "Strategic Fit",
    "Cost / Effort Tier",
    "Dual Verdict",
    "Product Judgment",
    "Acceptance",
]

ALLOWED_VERDICTS = {"BUILD NOW", "BUILD LATER", "DON'T BUILD"}

_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.DOTALL)


def _frontmatter_field(block: str, key: str):
    m = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", block, re.MULTILINE)
    return m.group(1) if m else None


def _has_section(text: str, name: str) -> bool:
    return bool(re.search(rf"^#{{1,6}}\s*{re.escape(name)}\s*$", text, re.MULTILINE | re.IGNORECASE))


def _section_body(text: str, name: str) -> str:
    """The text under section `name`, from its header to the next top-level (`##`) header or EOF.

    Subsections (`###`) of `name` are included; the next sibling `## ...` ends it. Empty if absent.
    Note (review r2 F11, accepted): this does not parse code fences — a ```-fenced line that looks
    like `## ...` inside the section would be read as the next boundary. A non-technical product brief
    is not expected to fence a `##` line inside the Dual Verdict block, so this is left as-is.
    """
    m = re.search(rf"^#{{1,6}}\s*{re.escape(name)}\s*$", text, re.MULTILINE | re.IGNORECASE)
    if not m:
        return ""
    start = m.end()
    nxt = re.search(r"^##(?!#)\s", text[start:], re.MULTILINE)
    return text[start : start + nxt.start()] if nxt else text[start:]


def validate_brief(text: str, min_clarity: float = 7.0) -> list[str]:
    """Return a list of structural problems with a product-brief (empty list = publishable).

    Checks (all reported, not short-circuited): leading frontmatter present with status /
    product_verdict / clarity_score; status is `draft` (publish flips it to ready); product_verdict
    is one of the allowed values; clarity_score parses and is >= min_clarity; every required section
    present; both case-for AND case-against present (no one-sided verdict); confidence + falsifiers
    present.
    """
    problems: list[str] = []

    fm = _FRONTMATTER_RE.match(text)
    if not fm:
        problems.append("missing leading frontmatter (---...---) with status/product_verdict/clarity_score")
        block = ""
    else:
        block = fm.group(1)

    status = _frontmatter_field(block, "status")
    if status is None:
        problems.append("frontmatter missing 'status'")
    elif status != "draft":
        problems.append(f"status must be 'draft' before publish (publish flips it to ready), got {status!r}")

    verdict = _frontmatter_field(block, "product_verdict")
    if verdict is None:
        problems.append("frontmatter missing 'product_verdict'")
    elif verdict not in ALLOWED_VERDICTS:
        problems.append(f"product_verdict must be one of {sorted(ALLOWED_VERDICTS)}, got {verdict!r}")

    raw_clarity = _frontmatter_field(block, "clarity_score")
    if raw_clarity is None:
        problems.append("frontmatter missing 'clarity_score'")
    else:
        try:
            clarity = float(raw_clarity)
        except ValueError:
            problems.append(f"clarity_score is not a number: {raw_clarity!r}")
        else:
            if clarity < min_clarity:
                problems.append(f"clarity_score {clarity} is below the publish threshold {min_clarity}")

    for name in REQUIRED_SECTIONS:
        if not _has_section(text, name):
            problems.append(f"missing required section: {name!r}")

    # the dual-verdict checks are scoped to the `## Dual Verdict` section body — a mention in the
    # Idea (or anywhere else) must NOT satisfy them (structural-only contract; semantic refutation
    # quality is the SA review's job, design §6).
    dv = _section_body(text, "Dual Verdict").lower()
    if "case-for" not in dv:
        problems.append("dual-verdict section missing the case-for")
    if "case-against" not in dv:
        problems.append("dual-verdict section missing the case-against (a one-sided verdict is banned)")
    if "confidence" not in dv:
        problems.append("dual-verdict section missing a confidence level")
    if "falsifier" not in dv:
        problems.append("dual-verdict section missing falsifiers (what would flip this)")

    # residual unfilled `{{...}}` template markers — completeness signal (shared via harness_utils).
    leftover = scan_placeholders(text)
    if leftover:
        problems.append("unfilled placeholder(s) remain — fill every {{...}}: " + ", ".join(leftover[:5]))

    return problems
