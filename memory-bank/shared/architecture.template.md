---
status: draft
lock: locked
version: v1
date: {{YYYY-MM-DD}}
---
<!-- ARCHITECTURE — the Solution Architect's ONE handoff artifact. Frontmatter MUST be the first bytes.
Two ORTHOGONAL fields: `status:` is the handoff lifecycle the gate manages (draft → ready on publish →
accepted by the Senior) — leave it `draft`; `lock: locked` + `version:` are the architecture's own lock
(DESIGN §9), set by you (the SA) and validated by architecture.py. Copy to architecture.md, fill EVERY
{{...}} marker, then run design-architecture step 7 (validate_architecture) before publish. Keep section
headers exactly as below — .claude/harness/architecture.py validates against them. -->

## Overview
{{One-paragraph description of the system — what it is, what problem it solves, and how it fits the
product-brief. No tech jargon; the PO should be able to read this.}}

## Module Seams
{{The declared boundaries between modules. Each seam is a named public interface two modules agree on,
enabling parallel, conflict-free development. See ADR-0001 for the seam rationale.}}

- **Seam A — {{name}}:** {{what crosses this boundary and the contract}}
- **Seam B — {{name}}:** {{what crosses this boundary and the contract}}

## Stack
{{Every framework chosen for this product. Each MUST be on the company allowlist
(.claude/harness/framework_library.py check_allowlist). Pass this list to validate_architecture.}}

- {{framework-name}} — {{why chosen over alternatives}}

## Invariants
{{The P0 rules the Junior's code must never violate. These are read by validate_architecture and
conformance-check. One line each.}}

- {{e.g. money values use a fixed-decimal type, never float}}
- {{e.g. user data is sanitized before any external API call}}

## Architecture Decisions
{{Key decisions and their ADR references. At least one ADR-NNNN reference is required.}}

- ADR-0001 — {{brief decision title}} (see memory-bank/shared/docs/adr/ADR-0001.md)
