---
status: draft
date: {{YYYY-MM-DD}}
---
<!-- PHASE ROADMAP — the SA's decomposition of the LOCKED architecture into a dependency-ordered build
sequence. The Senior consumes ONE phase at a time. Copy to roadmap.md, fill EVERY {{...}} marker, then
run validate_roadmap before publish. Each phase MUST declare an Increment (what is deliverable) and a
Verification (how to confirm it is done) — otherwise the Senior cannot build to it. Keep the
`### Phase N — <title>` header shape; .claude/harness/architecture.py validates against it. -->

## Phases

### Phase 1 — {{title}}
{{What this phase builds and why it is first (its dependencies, if any).}}
**Increment:** {{the deliverable, demoable end-to-end slice this phase produces}}
**Verification:** {{the exact command or observable state that confirms this phase is done}}

### Phase 2 — {{title}}
{{What this phase builds and what earlier phase it depends on.}}
**Increment:** {{the deliverable for this phase}}
**Verification:** {{how to confirm this phase is done}}
