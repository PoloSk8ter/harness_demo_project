<!-- HARNESS-CONTEXT — the ONE project-policy file every component reads (runtime-read model).
Copy to HARNESS-CONTEXT.md in your project root and fill it in. The project's CLAUDE.md @-imports it
so every session auto-loads it. Components NEVER hardcode any of the values below — they read them here.
Keep this file the single source of project policy. -->

# HARNESS-CONTEXT — <project name>

## project
- name: banking-assistant
- one_line: A guardrail-fronted, multi-specialist conversational banking assistant (reference build on adk_studio / Google ADK, simulated data).

## stack
- test_command: pytest -q -m "not llm"     # what the `tdd` and `ship` skills run
- package_manager: pip+requirements.txt
- source_dirs: banking_assistant/                       # what the `conform` skill scopes to

## invariants
# The project's P0 rules. The Senior `check` and the Junior `conform` read THIS list — they are not
# baked into any component. One line each.
- <e.g. money values use a fixed-decimal type, never float>
- <e.g. user data is sanitized before any external API call>
- <e.g. modules in source_dirs do not import each other across declared seams>

## glossary
# Optional. Domain terms with one-line canonical definitions (shared CONTEXT.md is the live copy).
- <Term>: <one-line meaning>

## framework_library
- path: C:/Users/jytee/infopro_harness_engineering_sdlc/infopro_harness/framework-library       # SA allowlist + Junior conventions/exemplars
- ref: 2026-06-24-snapshot (adk_studio ADMITTED)

## thresholds
# Project policy values the components read (never hardcoded in a component). One per line.
- min_clarity: 7.0        # the PO `validate` gate won't publish a brief scoring below this (0–10 scale)

## role
# Per INSTANCE. `apply_harness.py --role <role>` writes your role to a gitignored `.claude/role` (the
# per-instance file the access guard reads) AND installs only that role's skills — so normally you set
# NOTHING here, and your role can't ride a commit and flip the whole team's. The `acting_as` line below
# is only the SOLO / manual fallback, read when `.claude/role` is absent. Leave it as the placeholder
# unless you are running without `--role`.
- acting_as: <po | sa | senior | junior>   # SOLO/manual fallback only — `apply --role` writes .claude/role instead
- name: <your-board-assignee-name>   # the name the Senior assigns your tasks to (board `status --me`);
                                      # `resume` uses it to find YOUR READY tasks. If blank, `resume`
                                      # still routes gates 1–4 and shows ALL READY tasks at gate 5.
                                      # (Add a `name:` line to your gitignored `.claude/role` to keep it per-instance too.)
