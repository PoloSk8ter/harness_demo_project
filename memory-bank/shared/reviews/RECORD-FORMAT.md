# Handoff review records — format

Every accept/bounce/reopen from the `review` gate appends ONE JSON object (a line) to
`memory-bank/shared/reviews/log.jsonl`. This is the backward-arrow audit trail; it is append-only.

## Record (one JSON object per line in `log.jsonl`)

```json
{"from": "<reviewer role>", "to": "<author role>", "artifact": "<lane/file>", "verdict": "accept|bounce|reopen", "reasons": "<empty for accept; the bounce/reopen reasons otherwise>", "iteration": 1, "ts": "<ISO-8601 or a placeholder>"}
```

- `from` — the role doing the review (downstream).
- `to` — the role whose artifact is reviewed (upstream).
- `verdict` — `accept` unlocks the reviewer's own work; `bounce` sends a still-`ready` artifact back;
  `reopen` is a change-request against an already-`accepted` artifact (design §9) — a flaw found in later
  dev that re-circulates the locked artifact.
- `reasons` — required and non-empty for `bounce` and `reopen`; empty string for `accept`.
- `iteration` — bounce+reopen count for this artifact (1-based). When it reaches the cap (default 3) the
  reviewer escalates to a human instead of looping again.

## Status state machine (the artifact's frontmatter `status:`)

```
draft  --publish-->  ready  --accept-->  accepted  --reopen-->  bounced   (change-request, §9)
                     ready  --bounce-->  bounced  --revise-->  draft     (author revises, republishes)
```

Any other transition is invalid and rejected by `handoff.py`. The matching role line in
`shared/pipeline-status.md` is updated on every transition.
