# senior — working state (short-term memory)

Updated: 2026-06-25

## Current task
- none — between tasks. Phase 1 split is fully published (PLAN.md ready). Next Senior work is Phase 2
  split, but only AFTER the Junior has built+merged Phase 1 (each phase consumes the prior).

## In flight (artifact + status)
- none. memory-bank/shared/phases/phase-1/PLAN.md is published (bus: senior = ready), handed to Junior.

## Done this session
- Reviewed + ACCEPTED the SA's architecture.md (v1, locked) and roadmap.md (verify + refute + allowlist
  check: `check_allowlist(['adk_studio']) == []`). Both → accepted in reviews/log.jsonl.
- Split roadmap Phase 1 ("Contracts & walking skeleton") into 6 parallel-safe tasks (3 groups, disjoint
  files): T1 scaffold → {T2 schemas, T3 state_keys, T4 store} → {T5 tools, T6 shell+root_agent}.
- Coverage gate PASS; validate_task_breakdown → []; published through gate; regenerated BOARD.md.

## Next / open questions
- Junior's move now: review/accept the task-breakdown, then build T1 (only unblocked task) → T2/T3/T4
  unblock → T5/T6. When all 6 are accepted/DONE, I run `/split` on roadmap Phase 2 (Guardrail safety
  gate, Seam A). Re-run `board.py` after each Junior completion accept so DONE/BLOCKED stay current.
- Decision baked into the Phase-1 plan to remember: `set_card_state` token enforcement is built in
  Phase 1 (Seam C is one contract); only the card-action *specialist* (D3) + two-turn eval are Phase 4.
- run_agent smoke is `@pytest.mark.llm` (opt-in), NOT in the default `pytest -q -m "not llm"` suite
  (ADR-0004 / Invariant 9).

## Blocked on
- The whole Phase-2 split is blocked on Junior completing Phase 1. Nothing actionable for Senior until
  then.
