---
status: ready
date: 2026-06-25
---
<!-- PHASE ROADMAP — the SA's decomposition of the LOCKED architecture (v1) into a dependency-ordered build
sequence. The Senior consumes ONE phase at a time. Each phase declares an Increment + a Verification. -->

## Phases

### Phase 1 — Contracts & walking skeleton
First because every later phase builds against these contracts. Build the shared Pydantic schemas
(`RouteDecision`, `FinalReply`, `EscalationRecord`, `CardActionDraft`), the `state_keys.py` registry, the
simulated banking store + fixtures + its function-tool wrappers (Seam C, E-schemas), and a
`make_sequential([triage_stub, router_stub, synthesizer_stub])` shell (Seam F) that returns a `FinalReply`
end-to-end. No real classification or specialists yet — stubs only.
**Increment:** `run_agent(root, "hi")` returns a parseable `FinalReply`; the store returns fixture data via
a function tool; `root_agent` is discoverable.
**Verification:** `pytest -q -m "not llm"` green — store unit tests + schema-validation tests pass; a
`run_agent` smoke test returns a `FinalReply`-shaped result.

### Phase 2 — Guardrail safety gate (Seam A)
Depends on Phase 1's shell. Add the fail-closed `before_model_callback` at the pipeline entry, the pinned
`static_instruction` guardrail, and the synthesizer-exit re-check. This is the ADR-0002 backbone.
**Increment:** out-of-scope, unsafe, and ambiguous messages are refused before any specialist runs, and a
softened reply is caught by the exit re-check; refusal is terminal.
**Verification:** deterministic test — the guardrail callback fails CLOSED on crafted unsafe input with no
specialist in `.tool_calls()`; llm-eval (`@pytest.mark.llm`) — "what's the weather" and an unsafe message
are refused; an ambiguous message is clarified or refused, not mis-routed.

### Phase 3 — Read specialists + routing (Seam B + D1 + D2)
Depends on Phases 1–2. Replace the triage stub with the real classifier (one `RouteDecision` label) and wire
the balance (D1) and transactions (D2) specialists as `AgentTool`s on the router, reading the store.
**Increment:** balance and transaction questions return the correct simulated data via the one correct
specialist.
**Verification:** llm-eval — a balance question fires the balance tool and yields the correct figure; a
transaction question fires the transactions tool and yields the correct items; exactly one specialist tool
fires per turn (`.tool_calls()`).

### Phase 4 — Card-action specialist: confirm-then-execute (Seam D3)
Depends on Phases 1–3. Add the card-actions specialist: draft a `CardActionDraft`, require explicit
confirmation, then call `set_card_state` — which itself enforces the confirmation token (Invariant 3).
**Increment:** "lock my card" returns a confirmation prompt and the card locks ONLY after the user confirms;
declining leaves the card unchanged.
**Verification:** deterministic test — `set_card_state` refuses to mutate without a valid token and succeeds
with one (the structural guarantee); llm-eval — two-turn run: turn 1 produces a draft with no state change,
a confirm turn locks the card, a decline turn leaves it unchanged.

### Phase 5 — Fraud-escalation specialist (Seam D4)
Depends on Phases 1–2 (independent of 3–4; could run in parallel with 4). Add the fraud specialist: emit a
structured `EscalationRecord` (flagged item + context) plus a follow-up acknowledgement; no live human.
**Increment:** "I didn't make this charge" produces an `EscalationRecord` AND a "a specialist will follow up"
acknowledgement to the user.
**Verification:** deterministic test — an `EscalationRecord` validates with its required fields present;
llm-eval — a fraud message leaves an `EscalationRecord` in `.state` and the acknowledgement in `.text`.

### Phase 6 — Acceptance script (end-to-end, the brief's six checks)
Last; depends on Phases 1–5. Wire the full assistant and encode the brief's 6-check scripted conversation as
an opt-in eval suite asserting observable signals (per ADR-0004), exercising every path once.
**Increment:** all six acceptance checks (balance, transactions, confirm-then-execute lock + decline, fraud
escalation, out-of-scope + unsafe refusal, ambiguous handling) pass once each.
**Verification:** `pytest -m llm tests/acceptance` (run deliberately) — all six cases pass; the deterministic
suite `pytest -q -m "not llm"` stays green.
