---
status: accepted
lock: locked
version: v1
date: 2026-06-25
---
<!-- ARCHITECTURE — the Solution Architect's ONE handoff artifact (LOCKED v1). status: stays draft until
the publish gate flips it to ready; lock: locked + version are the architecture's own commitment (§9). -->

## Overview
A reference conversational banking assistant that takes one user message and returns one finalized reply,
built as the company's canonical **orchestrator + specialists** agent system on `adk_studio` (the team's
standard layer over Google ADK). Every message is screened by a guardrail before anything else; an in-scope
message is classified to exactly one of four competencies — account & balance, transaction history, card
actions, suspected-fraud escalation — handled by that single specialist, then formatted and re-screened
before it is returned. Banking data is simulated and the user's identity is assumed; the deliverable is the
working, safe composition, not a production deployment. The design's load-bearing idea is that the three
safety guarantees (screen-first, confirm-before-write, structured escalation) are enforced by **code at
fixed seams**, not by the model's discretion — so they hold even when the model mis-routes or is jailbroken.

## Module Seams
The declared boundaries the Senior splits parallel work along. Each is a named contract two modules agree on;
specialists never import one another, and shared data crosses only through the `state_keys.py` registry
(Seam F). See ADR-0001 for the seam rationale and ADR-0002 for why the safety seams are structural.

- **Seam A — Guardrail (safety boundary):** a fail-closed `before_model_callback` at the pipeline entry
  (`safe(on_error="raise")`) plus a pinned `static_instruction`, plus a final re-check on the synthesizer.
  Contract: `screen(message, state) -> Allow | Refuse(reason)` ahead of the fixed pipeline (no specialist
  runs on unscreened input); `recheck(reply) -> ok | Refuse` before return (the finalizer cannot soften a
  refusal). Refuse is terminal. (ADR-0002.)
- **Seam B — Route decision (triage/classifier):** an adk_studio triage agent that emits exactly one label.
  Contract: writes `RouteDecision{ route ∈ [balance, transactions, card_action, fraud, clarify], reason }`
  to state key `route`. One label only; `disallow_transfer_to_parent/peers=True`. (ADR-0003.)
- **Seam C — Simulated banking store + tools:** a deterministic, fixture-backed store exposed as ADK
  function tools. Contract: `get_balance(account_id) -> str(JSON)`, `list_transactions(account_id, …) ->
  str(JSON)`, `get_card_state(card_id) -> str`, and `set_card_state(card_id, action, confirmation_token,
  tool_context) -> str` — where `set_card_state` **refuses to mutate unless a valid confirmation token is
  present in state**. The single source of simulated truth. (Invariant 3; ADR-0002.)
- **Seam D — Specialists (four, parallel-disjoint):** each a leaf agent (skill + optional schema) attached
  to the router as `AgentTool(agent=…, skip_summarization=True)`. Contract: each reads only Seam C tools and
  the Seam B route, and writes its result to a known `output_key`. D1 balance, D2 transactions (read-only);
  D3 card_action (confirm-then-execute via `set_card_state`); D4 fraud_escalation (emits `EscalationRecord`
  + acknowledgement). Disjoint files → the Senior parallelizes these.
- **Seam E — Synthesizer + shared schemas:** `answer_agent` with `output_schema=FinalReply` formats the
  single specialist's output and **never merges** multiple specialists; Seam A's re-check runs on its exit.
  Owns the shared Pydantic schemas: `RouteDecision`, `FinalReply`, `EscalationRecord`, `CardActionDraft`.
- **Seam F — Orchestration shell:** `make_sequential("banking_assistant", [guardrail/triage, router,
  synthesizer])` + `state_keys.py` registry + tier config (`ADK_MODEL_TRIAGE/_ROUTER/_SYNTH`) + `root_agent`
  discovery in `__init__.py`. The integration seam; depends on the A–E contracts.

## Stack
Every framework is on the company allowlist (`framework_library.check_allowlist(['adk_studio']) == []`,
verified against `framework_library.path`).

- **adk_studio** — the team's standard layer over Google ADK; chosen because its canonical
  `make_sequential([triage, router, synthesizer])` shape *is* the brief's refuse → route → specialise →
  finalize composition, and it standardizes exactly the cross-cutting concerns a safety-critical reference
  must get right: fail-safe callbacks (guardrail fails closed, telemetry fails open), structured-output
  safety, token telemetry, and the `run_agent` eval harness. Every agent is built through the factory
  (`make_agent` / `make_*`) — never a raw `LlmAgent`. Pinned runtime (of adk_studio, not separately chosen):
  `google-adk==1.16.0`; Gemini models resolved per tier from env; Pydantic schemas via ADK. Rejected
  alternatives — a single tool-using agent (the brief's falsifier, kept as the comparison baseline), a raw
  `LlmAgent` (violates the conventions), and a pure-stdlib reimplementation (never exercises the company
  stack the reference exists to demonstrate). See ADR-0001.

## Invariants
The P0 rules the Senior `check` and the Junior `conform` enforce. One line each.

- **1. Guardrail-first & recheck-last.** Every inbound message is screened before any specialist runs, and
  the finalized reply is re-screened before return; a refusal is terminal and the finalizer must not soften
  it. (Decision-log; enforced by Seam A.)
- **2. Exactly one specialist.** One message routes to exactly one specialist; the synthesizer formats that
  single reply and never merges multiple specialists. (Decision-log; Seams B + D + E.)
- **3. Confirm-then-execute is tool-enforced.** No state-changing action executes without a valid explicit
  confirmation token; `set_card_state` enforces it — model intent alone never fires a write. (Decision-log;
  Seam C.)
- **4. Structured escalation.** Suspected fraud produces a structured `EscalationRecord` (flagged item +
  context) AND a follow-up acknowledgement; no live-human dependency. (Decision-log; Seam D4 + E.)
- **5. Reference scope.** Banking data is simulated and identity is assumed; no real money, no real PII, no
  external integration beyond the LLM provider. (Decision-log.)
- **6. Build through the factory.** Every agent is constructed via `adk_studio.make_agent`/`make_*` — never a
  raw `LlmAgent`; tools live on the router, `output_schema` on the synthesizer (the router/synthesizer
  split). (adk_studio conventions.)
- **7. Fail-closed safety callbacks.** Safety-critical before-callbacks (the guardrail, the prompt-builder)
  fail CLOSED (`safe(on_error="raise")`); telemetry/after-callbacks fail open. (adk_studio conventions; the
  backbone of invariant 1.)
- **8. Seam isolation.** Specialists do not import one another; shared data flows only through the declared
  `state_keys.py` registry. (Seam discipline.)
- **9. Two-tier verification.** Real-model evals (`run_agent`) are marked `@pytest.mark.llm` and excluded
  from the default `pytest -q -m "not llm"` suite; the default/CI suite is the deterministic seam tests (the
  safety mechanics) only. (ADR-0004; respects adk_studio's tracked no-offline-mock caveat.)

## Architecture Decisions
- **ADR-0001** — Build on adk_studio's canonical orchestrator + specialists shape
  (memory-bank/shared/docs/adr/ADR-0001.md).
- **ADR-0002** — Safety is structural, not model-dependent (memory-bank/shared/docs/adr/ADR-0002.md).
- **ADR-0003** — Route to exactly one specialist; AgentTool call-and-return, no merge
  (memory-bank/shared/docs/adr/ADR-0003.md).
- **ADR-0004** — Two-tier verification: deterministic seam tests + tolerant real-model evals
  (memory-bank/shared/docs/adr/ADR-0004.md).
