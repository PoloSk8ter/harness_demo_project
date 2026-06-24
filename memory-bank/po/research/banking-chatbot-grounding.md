# PO working notes — multi-agent banking chatbot (validate)

Date: 2026-06-25 · Posture: HOLD SCOPE · Status: working notes (NOT a handoff artifact)

## Grilled forks (resolved with user)
1. **Deployment context** → Reference / demo architecture. Mock/simulated banking data, identity/auth
   stubbed, the multi-agent pattern itself is the deliverable. (Removes real-money / PII / KYC scope.)
2. **Routing ↔ synthesizer** → Router picks exactly ONE specialist per message; synthesizer is a
   format-and-guard finalization layer over that single reply (NOT a multi-output merger).
3. **Card actions (writes)** → Confirm-then-execute. Bot drafts the lock/unlock, user explicitly
   confirms, THEN it executes. State-changing ops are never auto-fired on intent.
4. **Fraud escalation** → Structured handoff + acknowledgement. Produces a structured escalation record
   (flag/ticket with context) AND tells the user a human will follow up. No live-human dependency.

## Evidence (tagged)
- [confirmed] Router/"supervisor" → specialists is the canonical multi-agent pattern in LangGraph:
  routing is a dedicated decision node, adding a domain = add a specialist + update the router prompt,
  control flow is traceable. (reference.langchain.com/python/langgraph-supervisor; focused.io supervisor-vs-swarm)
- [confirmed] These exact capabilities are mainstream in production banking bots: BofA Erica — 2.5B
  interactions, 20M active users; Wells Fargo Fargo — card controls + transaction search w/ privacy
  safeguards; market $2.1B in 2025, ~24% CAGR; 54% of FIs implementing GenAI. (coinlaw.io; neontri.com)
- [confirmed] Guardrails + human oversight are required, not optional, in this domain: CFPB holds
  chatbots to the same consumer-protection standard as human agents; an audit found 24/24 tested
  banking bots exploitable. (consumerfinance.gov chatbots report; corporatecomplianceinsights.com)
- [estimated] As a reference/demo with mock data, effort is Medium and risk is Low — no real money,
  no PII, no integration surface; the orchestration is commodity (LangGraph ships supervisor templates).
- [assumption] The audience values demonstrating the *composition* (guardrail + router + typed
  specialists + confirm-then-execute + structured escalation), not production realism. If the audience
  needs real integration/compliance, mock-data scope teaches the wrong half. → falsifier.

## Strategic-fit frameworks (for the brief)
- JTBD: "resolve my banking question/action in one conversation, safely, without menus or hold music."
- Lean MVP / Build-Measure-Learn: smallest learnable unit = end-to-end pipeline, one happy path per
  specialist + one refusal + one confirm + one escalation.
- Wardley / build-vs-buy: orchestration (supervisor) is commodity → lean on it; the differentiated
  value is the domain specialists + guardrail composition + write-safety pattern → build that.
- Opportunity cost: low for a reference artifact; the cost is the latency/complexity of N agents vs a
  single tool-using agent (the case-against).

## Dual-verdict seeds
- Case-for: established pattern + real demand surface + low-risk demo scope + clear acceptance.
- Case-against (independent): 7 nodes (guardrail+router+4 specialists+synthesizer) may be
  over-engineered vs one tool-using agent; multi-agent adds latency/cost/coordination failure modes;
  the *hard* parts (real integration, compliance, adversarial robustness) are exactly what's stubbed.
- Falsifier: a single-agent-with-tools baseline that matches routing accuracy + guardrail behavior at
  lower latency/cost would un-justify the multi-agent shape.

## Clarity sub-scores (for po_brief.clarity_score)
- goal 9 (crisp after grilling), constraints 8, criteria 8 → 8.4 (> min_clarity 7.0)
