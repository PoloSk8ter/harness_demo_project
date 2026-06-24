---
status: draft
date: {{YYYY-MM-DD}}
---
<!-- COMPLETION RECORD — the Junior's ship artifact for ONE task (DESIGN §2). Copy to
memory-bank/shared/completions/<task-id>.md, fill EVERY {{...}} marker, then run
validate_completion_record before publish. Records what shipped + the conformance result; if a locked
design flaw was found, note the change-request (reopen) filed to the SA (DESIGN §9). Keep the four
`## ` section headers — .claude/harness/conformance_check.py validates against them. -->

## Task
{{task id + the module seam / ADR this task implemented, from the Senior's task-breakdown}}

## Files Changed
{{the files this task changed — must all be within the task's OWNED set (check_file_scope)}}

## Tests
{{the test command(s) run and the result — RED→GREEN history + full suite green}}

## Conformance
- Scope: {{changed files within the task's owned set — check_file_scope result}}
- Allowlist: {{frameworks used are on the company library allowlist — check_allowlist result}}
- ADRs/conventions: {{how the code conforms to the locked ADRs + the library conventions.md}}
- Change-request: {{none, OR the reopen filed to the SA and why (DESIGN §9)}}
