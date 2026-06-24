---
status: draft
product_verdict: {{BUILD NOW | BUILD LATER | DON'T BUILD}}
clarity_score: {{X.X}}
date: {{YYYY-MM-DD}}
owner_role: po
---
<!-- PRODUCT BRIEF — the Product Owner's ONE handoff artifact: the curated ROLLUP of the validated
features. Per-feature validations live in memory-bank/shared/specs/<date>-<feature>-validation.md and
locked cross-cutting calls in memory-bank/shared/decision-log.md; this brief summarizes + links them
for the SA to review. The SA reviews this before designing. The frontmatter MUST stay at
the very top (the handoff gate reads `status:` from the leading ---...--- block). Copy this file to
product-brief.md in this lane, fill EVERY {{...}} marker, then run the validate-product pipeline (it
runs validate_brief + publish). Fill markers are {{...}} (NOT <...>) so the completeness scan never
collides with legitimate prose like "latency < 200ms". Keep the section headers exactly as below —
.claude/harness/po_brief.py validates against them. Domain-neutral: no domain vocabulary. -->

# Product Brief — {{one-line idea}}

## Idea
{{Restate the idea in 2-3 sentences, so the SA can't misread it.}}

## Who It's For
{{Name the actual person with the pain. What does it cost them today, and what do they do instead?}}

## What It Must Do
{{The requirements, in non-technical terms — what the product must accomplish, not how.}}
- {{Requirement one.}}
- {{Requirement two.}}

## How It Should Work
{{High-level behaviour from the user's side + the smallest observable proof that it works. No tech.}}

## Evidence
{{Sourced grounding from evidence-research. Tag every claim.}}
- [confirmed] {{a cited fact}}
- [estimated] {{a reasoned estimate}}
- [assumption] {{a stated assumption to test}}

## Strategic Fit
{{2-4 named frameworks applied (strategic-fit). Where does this sit vs. the goal, and what's the
opportunity cost of building it now?}}

## Cost / Effort Tier
{{Generic effort/risk tier (cost-tier-eval) — NOT a domain price. How much effort/risk to prove it,
and what guards reduce that.}}

## Dual Verdict
{{Decision #6: sourced + adversarial. Both sides are mandatory; a one-sided verdict is banned.}}
### Case-for
{{The grounded argument to build it.}}
### Case-against
{{The independent adversarial refutation (adversarial-refute).}}
**Confidence:** {{high | medium | low}}
**Falsifiers (what would flip this):** {{the assumption that, if proven wrong, kills the idea}}

## Product Judgment
{{BUILD NOW | BUILD LATER | DON'T BUILD — and why, in one paragraph. clarity_score above is
goal*0.40 + constraints*0.30 + criteria*0.30 via po_brief.clarity_score.}}

## Acceptance
{{The minimal, observable proof that this product does what the brief says — how the SA/PM will know.}}
