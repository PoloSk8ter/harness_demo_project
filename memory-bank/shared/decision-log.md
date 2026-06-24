---
owner_role: po
---
<!-- DECISION LOG — the running record of LOCKED, cross-cutting product decisions (the ones that span
features and constrain the SA/Senior/Junior). The PO appends one entry per locked call; the team READS
it. This is the project "constitution" the consistency-gate / review reads. Append newest at the top.-->

# Decision Log

## 2026-06-25 — Guardrail screens first, and re-checks last
- **Decision:** Every inbound message passes the guardrail BEFORE any specialist runs; the finalized
  reply is re-checked against the same safety boundary BEFORE it is returned. The guardrail refuses
  (politely, clearly) rather than guessing when a request is out of scope, unsafe, or ambiguous.
- **Rationale:** In this domain a refusing boundary + human oversight are non-negotiable (CFPB holds
  these assistants to the human-agent standard; an audit broke 24/24 tested bots). Screening first
  keeps unsafe input away from specialists; re-checking last stops a finalizer from softening a refusal.
- **Rejected:** Letting specialists self-police, or guardrailing only the input — both leave a hole.
- **Affects:** all specialists, the router, the finalizer (SA architecture, Senior task split).

## 2026-06-25 — One message routes to exactly one specialist; the finalizer does not merge
- **Decision:** The router classifies each message to exactly ONE of the four competencies and invokes
  that single specialist. The finalizer formats and safety-checks that single reply; it does NOT merge
  outputs from multiple specialists.
- **Rationale:** Matches the "route to a specialist" intent, keeps control flow legible and traceable,
  and avoids multi-output coordination failure modes in a reference build.
- **Rejected:** Fan-out to multiple specialists with a merging synthesizer — more power, more failure
  surface, not needed for the MVP. Revisit only if compound multi-domain messages become a goal.
- **Affects:** router, finalizer/synthesizer (SA architecture, Senior task split).

## 2026-06-25 — State-changing actions are confirm-then-execute
- **Decision:** No action that changes account state (card lock / unlock, and any future write) fires on
  detected intent alone. The assistant drafts the action, requires an explicit user confirmation, then
  executes and reports the result. A declined confirmation leaves state unchanged.
- **Rationale:** Irreversible/state-changing operations must not trigger on a model's intent guess;
  explicit confirmation is the write-safety guard.
- **Rejected:** Auto-execute on intent (too risky); advise-only (too weak — the demo must show a safe
  write path end to end).
- **Affects:** card-actions specialist; the pattern binds any future write specialist (SA, Senior, Junior).

## 2026-06-25 — Reference/demo scope: simulated data, identity assumed
- **Decision:** Banking data is simulated and the user's identity is assumed (sign-in / authentication is
  OUT of scope). The deliverable is the working multi-specialist composition, not a production system.
- **Rationale:** Removes the dangerous surfaces (real money, real personal data, credentials,
  integrations) so the build can prove the safe-composition pattern at low risk.
- **Rejected:** Real data / real auth (out of scope for a reference build; would invert the risk tier).
- **Affects:** every specialist and the guardrail (SA architecture, Senior + Junior implementation).

## 2026-06-25 — Fraud escalation is a structured handoff plus acknowledgement (no live human)
- **Decision:** Suspected-fraud handling produces a STRUCTURED escalation record (flagged item + enough
  context for a human to act) AND returns a "a specialist will follow up" acknowledgement to the user.
  It does NOT depend on a live human being available in the conversation.
- **Rationale:** Makes escalation observable and testable without a staffed human channel, while still
  satisfying the domain's human-oversight requirement.
- **Rejected:** Live real-time transfer (needs staffing, untestable in a demo); a canned message with no
  record (not actually an escalation).
- **Affects:** fraud-escalation specialist (SA architecture, Senior + Junior implementation).
