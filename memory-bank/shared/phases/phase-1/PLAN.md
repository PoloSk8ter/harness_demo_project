---
status: ready
date: 2026-06-25
---
<!-- TASK BREAKDOWN — Phase 1 "Contracts & walking skeleton" (roadmap §Phase 1), split into
parallel-safe, file-owned tasks (DESIGN §8). Consumes the LOCKED architecture v1 (Seams A–F + ADRs)
and ONLY roadmap Phase 1. Validated with task_split.validate_task_breakdown before publish.

Scope of this phase (from the roadmap): build the shared Pydantic schemas, the state_keys registry,
the simulated fixture-backed store + its function-tool wrappers (Seam C, E-schemas), and a
make_sequential([triage_stub, router_stub, synthesizer_stub]) shell (Seam F) that returns a FinalReply
end-to-end, with root_agent discoverable. STUBS ONLY — no real classifier (Phase 3), no guardrail
callback (Phase 2), no specialists (Phases 3–5).

Parallel-safety (mechanism-enforced): same Group ⇒ disjoint Files; a dependent task goes in a LATER
group; every task owns ≥1 file; each task runs on its own task/<id> branch. -->

## Tasks

### Task T1 — Project scaffold & test harness
Stands up the buildable/testable walking-skeleton infra: the dependency manifest pinned to the
adk_studio runtime, and the pytest configuration that locks the two-tier verification marker. Binds to
Seam F (orchestration infra) and ADR-0004 / Invariant 9 — it registers the `@pytest.mark.llm` marker so
real-model evals are excluded from the default suite, and makes `pytest -q -m "not llm"` the gate.
`pyproject.toml` sets `pythonpath = ["."]` so `banking_assistant` imports as a PEP-420 namespace package
until T6 adds its `__init__.py` (see Notes). `requirements.txt` pins `google-adk==1.16.0` + `pydantic`
+ `pytest` (the adk_studio pinned runtime, ADR-0001).
**Group:** group-1
**Files:** requirements.txt, pyproject.toml, tests/conftest.py
**Dependencies:** none
**Assignee:** junior-1
**Verification:** `pip install -r requirements.txt` succeeds AND `python -m pytest --markers` lists `@pytest.mark.llm` (the locked marker, Invariant 9).

### Task T2 — Shared Pydantic schemas (Seam E)
Builds the four shared output schemas the whole pipeline contracts on (Seam E, "owns the shared Pydantic
schemas"): `RouteDecision{ route: Literal[balance, transactions, card_action, fraud, clarify], reason }`
(Seam B label set), `FinalReply` (the single finalized reply, Seam E/Invariant 2), `EscalationRecord`
(flagged item + context, Seam D4/Invariant 4), `CardActionDraft` (Seam D3/Invariant 3). Every field
carries a `Field(..., description=...)` per the adk_studio schema convention. Deterministic — pure
Pydantic, no model.
**Group:** group-2
**Files:** banking_assistant/schemas.py, tests/test_schemas.py
**Dependencies:** T1
**Assignee:** junior-1
**Verification:** `pytest -q -m "not llm" tests/test_schemas.py` green — valid instances construct; an out-of-enum `RouteDecision.route` is rejected; a missing required field on each schema raises `ValidationError`.

### Task T3 — State-key registry (Seam F / Invariant 8)
Builds `banking_assistant/state_keys.py` — the single registry of canonical session-state keys through
which all shared data flows (Invariant 8: "shared data flows only through the declared state_keys
registry"; Seam F). Defines at minimum the keys for the route decision, the confirmation token (read by
`set_card_state`, Invariant 3), the final reply, and the escalation record, using the adk_studio
`state.app/user/temp` prefix helpers where a scope applies. No business logic — names only.
**Group:** group-2
**Files:** banking_assistant/state_keys.py, tests/test_state_keys.py
**Dependencies:** T1
**Assignee:** junior-2
**Verification:** `pytest -q -m "not llm" tests/test_state_keys.py` green — every key is a unique, non-empty string; the confirmation-token and route keys are present and importable by name.

### Task T4 — Simulated banking store + fixtures (Seam C, data layer)
Builds the deterministic, fixture-backed store that is the single source of simulated truth (Seam C,
Invariant 5: simulated data, identity assumed). `banking_assistant/store.py` holds the fixtures
(accounts, balances, transactions, per-card lock state) and read/mutate accessors over them. This is the
data layer ONLY — the ADK function-tool wrappers are T5. No model, fully deterministic.
**Group:** group-2
**Files:** banking_assistant/store.py, tests/test_store.py
**Dependencies:** T1
**Assignee:** junior-3
**Verification:** `pytest -q -m "not llm" tests/test_store.py` green — balance, transactions, and card-state reads return the fixture values; results are stable across repeated calls (deterministic).

### Task T5 — Seam C function-tool wrappers
Wraps the T4 store as the four ADK function tools the router will hold (Seam C contract): `get_balance`,
`list_transactions`, `get_card_state` (read-only, return `str(JSON)`), and `set_card_state(card_id,
action, confirmation_token, tool_context)` which **refuses to mutate unless a valid confirmation token is
present in state** (Invariant 3 / ADR-0002 — the structural write-safety guarantee; reads the token via
the T3 registry key). The tool and its enforcement are built here because Seam C is one cohesive
contract; the card-action *specialist* (Seam D3) and its two-turn eval remain Phase 4 (no scope creep).
**Group:** group-3
**Files:** banking_assistant/tools.py, tests/test_tools.py
**Dependencies:** T3, T4
**Assignee:** junior-2
**Verification:** `pytest -q -m "not llm" tests/test_tools.py` green — read tools return the fixture data as JSON; `set_card_state` refuses (no state change) without a valid token and succeeds with one.

### Task T6 — Orchestration shell + root_agent (Seam F)
Builds the walking-skeleton pipeline: three stub agents via the factory (Invariant 6, never raw
`LlmAgent`) — `triage_stub`, `router_stub` (`disallow_transfer_to_parent/peers=True`, ADR-0003),
`synthesizer_stub` (`output_schema=FinalReply`) — composed with
`make_sequential("banking_assistant", [...])`; models resolve per tier from
`ADK_MODEL_TRIAGE/_ROUTER/_SYNTH` (Seam F tier config). `banking_assistant/__init__.py` exposes
`root_agent` for discovery. The Phase-1 router stub does NOT attach the Seam C tools (that is Phase 3),
so this task is independent of T5. The end-to-end `run_agent` smoke is `@pytest.mark.llm` (opt-in,
EXCLUDED from the default suite per ADR-0004 / Invariant 9); the default-suite test asserts the shell's
structure without a model.
**Group:** group-3
**Files:** banking_assistant/agent.py, banking_assistant/__init__.py, tests/test_shell.py, tests/test_smoke.py
**Dependencies:** T2, T3
**Assignee:** junior-1
**Verification:** `pytest -q -m "not llm" tests/test_shell.py` green — `banking_assistant.root_agent` is importable/discoverable and is a sequential of exactly three stub sub-agents; the opt-in `pytest -m llm tests/test_smoke.py` returns a parseable `FinalReply`-shaped result for `run_agent(root_agent, "hi")`.

## Notes (for the building Juniors — not validated, context only)

- **Packaging:** during group-2/group-3, `banking_assistant/` has NO `__init__.py` and imports as a
  PEP-420 namespace package (T1 sets `pythonpath = ["."]`). Do NOT add a `banking_assistant/__init__.py`
  in any task except T6 — T6 is its sole owner (it adds `from .agent import root_agent` for discovery).
  Tests import absolute, e.g. `from banking_assistant.schemas import FinalReply`.
- **Two-tier verification (ADR-0004 / Invariant 9):** the default gate is `pytest -q -m "not llm"`
  (deterministic seam tests only). Any test that calls `run_agent` (real Gemini) MUST be marked
  `@pytest.mark.llm`. Never wire a model-spending test into the default suite.
- **Branches:** one task = one `task/T<n>` branch, changing ONLY that task's owned Files. group-2's
  three tasks (T2/T3/T4) and group-3's two (T5/T6) have disjoint file sets and merge cleanly.
