---
status: draft
feature: {{feature-slug}}
product_verdict: {{BUILD NOW | BUILD LATER | DON'T BUILD}}
clarity_score: {{X.X}}
date: {{YYYY-MM-DD}}
owner_role: po
---
<!-- FEATURE VALIDATION — one validated feature within the product (NOT the whole-product brief). The
PO writes one of these per feature/idea into memory-bank/shared/specs/<date>-<feature>-validation.md;
the team READS them; the product-brief.md is the curated rollup of all of them. Copy this file, fill
EVERY {{...}} marker, then validate it with po_brief.validate_brief (it shares the brief's section set,
so the same rigor applies per feature). Keep the section headers exactly as below. Fill markers are
{{...}} (NOT <...>) so the completeness scan never collides with prose like "latency < 200ms".
Domain-neutral: no domain vocabulary. -->

# Feature — {{one-line feature description}}

## Idea
{{Restate the feature in 2-3 sentences, so the SA/Senior can't misread it.}}

## Who It's For
{{The actual user of this feature. What does it cost them today, and what do they do instead?}}

## What It Must Do
{{The requirements, in non-technical terms — what the feature must accomplish, not how.}}
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
{{2-4 named frameworks applied. Where does this feature sit vs. the product goal, and what's the
opportunity cost of building it now versus the other features in specs/?}}

## Cost / Effort Tier
{{Generic effort/risk tier — NOT a domain price. How much effort/risk to prove it, what guards reduce that.}}

## Dual Verdict
{{Decision #6: sourced + adversarial. Both sides are mandatory; a one-sided verdict is banned.}}
### Case-for
{{The grounded argument to build it.}}
### Case-against
{{The independent adversarial refutation (adversarial-refute).}}
**Confidence:** {{high | medium | low}}
**Falsifiers (what would flip this):** {{the assumption that, if proven wrong, kills the feature}}

## Product Judgment
{{BUILD NOW | BUILD LATER | DON'T BUILD — and why, in one paragraph. clarity_score above is
goal*0.40 + constraints*0.30 + criteria*0.30 via po_brief.clarity_score.}}

## Acceptance
{{The minimal, observable proof that this feature does what this doc says — how the SA/PM will know.}}
