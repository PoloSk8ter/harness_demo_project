# SA role-instinct — `framework_library.path` may be an unfilled placeholder; wire it before the allowlist gate

**Tier:** role (sa) · **Captured:** 2026-06-25 (banking-assistant v1 design)

## The trap
On a greenfield adoption, HARNESS-CONTEXT's `framework_library.path` can still be the `<…>` placeholder.
If it is, the allowlist gate is silently meaningless: `framework_library.check_allowlist([...], <path>)`
and `architecture.validate_architecture(..., library_root=<path>)` will report **every** framework as a
violation — because a non-existent `library_root` dir makes `is_allowed` return False for all of them. You
can stare at a framework that's genuinely ADMITTED and watch the gate reject it.

## The fix (and the non-obvious bit)
1. Don't assume the path is wired. If it's a placeholder, **get the real path** (ask the user — it lives in
   a separate, standalone library repo, not this one).
2. Write it with the guard-safe writer — `context_init.py` writes **any** `key: value` field, not just the
   three `stack` fields the `/architect` skill spells out:
   ```bash
   python ".claude/harness/context_init.py" write --section framework_library --key path --value "<lib-root>"
   ```
   (`context_init` uses plain Python I/O, so the access guard never blocks it — same reason it can write the
   stack before any role is set.)
3. **Verify before designing:** `framework_library.list_allowed("<lib-root>")` should list real entries, and
   `check_allowlist([your_frameworks], "<lib-root>")` should return `[]`.

## Why it matters
The allowlist is a *hard* gate (only allowlisted frameworks may enter `## Stack`), but it fails **open into a
false negative** when misconfigured — it rejects everything rather than warning that the root is missing. A
green `list_allowed` is the cheap proof the gate is actually live. See [[design-notes]].
