# SA design notes — banking-assistant (v1)

Working trail behind the locked `architecture.md` + ADRs + `roadmap.md`. Not a handoff artifact.

## 1. Review of the upstream brief (gate)
- `product-brief.md` reviewed (verify + refute) and **ACCEPTED** (`ready → accepted`, iteration 1).
- **Verify:** all sections present (clarity 8.4, BUILD NOW); four competencies cleanly scoped; the safety
  composition is unambiguous (guardrail screens first + re-checks last, route-to-exactly-one,
  confirm-then-execute, structured escalation); the 5 locked calls in `decision-log.md` are consistent
  with it; the 6-check acceptance script is concrete and fully observable.
- **Refute:** the brief never says *how* classification happens (LLM vs deterministic) and never pins the
  simulated-data shape — but those are legitimately **SA** decisions, not brief defects. Its own
  case-against (multi-agent vs single-agent) is a falsifier for me to weigh, not a blocker. No real defect.

## 2. Grill — the one ambiguity driven out
The brief pulls two ways: "conversational / free-text" (→ real NLU / an LLM) vs. "no external integration
surface" + a *deterministic* acceptance script + "reference/demo of the composition." HARNESS-CONTEXT's
`framework_library.path` was an unfilled placeholder, so no allowlist was visible. Asked the user once.
**Resolution:** the framework library lives at
`C:/Users/jytee/infopro_harness_engineering_sdlc/infopro_harness/framework-library`; it admits
**`adk_studio`** (the team's standard layer over Google ADK 1.16). So the build is LLM-backed via the
company's blessed agent stack — *not* a stdlib reimplementation. Path now written into HARNESS-CONTEXT.

## 3. Brainstorm — ≥3 approaches, one chosen
1. **adk_studio orchestrator + specialists** *(CHOSEN)* — `make_sequential([guardrail/triage, router,
   synthesizer])`; specialists as `AgentTool`s on the router; simulated store as function tools. IS the
   allowlisted, conventionalized shape and IS the brief's refuse→route→specialise→finalize composition.
2. **Single capable agent + tools + safety prompt** *(rejected — the brief's headline falsifier)* — cheaper/
   lower-latency, but the deliverable is the *multi-specialist composition itself*, and the company shape is
   orchestrator+specialists. Kept live as the baseline the acceptance script can later measure against.
3. **Pure-Python stdlib reimplementation** *(rejected)* — deterministic, but reinvents the commodity shell and
   never exercises the company agent stack this reference exists to demonstrate.
4. **Raw `google-adk` LlmAgent** *(rejected)* — violates the conventions (never raw `LlmAgent`); loses
   telemetry / fail-safe callbacks / structured-output safety.

## 4. The load-bearing insight → ADR-0002
**Safety is structural, not model-dependent.** The three safety guarantees are enforced by code at
deterministic seams (fail-closed before-callback guardrail; tool-enforced confirmation token for writes;
Pydantic escalation record), so safety holds even under LLM mis-routing or jailbreak — directly answering
the brief's adversarial-robustness case-against, and making the safety mechanics deterministically testable
without the model (→ ADR-0004 two-tier verification).

## 5. Seams (disjoint boundaries for the Senior's parallel split)
A Guardrail · B Route-decision · C Simulated store + tools · D 4 specialists (parallel) · E Synthesizer +
shared schemas · F Orchestration shell. See `architecture.md` for the contracts.

## 6. Allowlist check
`framework_library.check_allowlist(['adk_studio'], <lib>) == []` ✓ — no `vet-lib` needed (adk_studio is
already ADMITTED, 2026-06-24).
