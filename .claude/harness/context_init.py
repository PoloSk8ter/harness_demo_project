"""context_init.py — the ADOPTION-bootstrap mechanism (role-harness Phase 9).

Resolves the harness's chicken-and-egg: `HARNESS-CONTEXT.md` carries the project's `stack` /
`invariants`, but it lives in NO role's lane, so a tool-write (Edit/Write) would be DENIED by the
fail-closed access guard before any role is even established. context_init writes it through plain
**Python file I/O**, which the guard never intercepts — the same guard-safe pattern board.py /
handoff.py use. That is the whole reason this module exists.

What it does (filled across Phase 9 tasks):
  - detect_stack(root)   — conservative read of a project's build markers → the three `stack` fields.
  - set_field/write_context — write specific HARNESS-CONTEXT fields without clobbering the rest (T4).
  - parse_deps(root)     — dependency names from the manifest, to seed the framework allowlist (T6).
  - a thin CLI the /init and /architect skills invoke (T6).

What it does NOT do: the per-instance ROLE. That is `apply --role`'s job (it writes the gitignored
`.claude/role`, read by `access_guard.read_role`). context_init only ever touches project context,
never the role.
"""

import json
import re
from pathlib import Path

# Stack detection markers, in priority order. The FIRST matching ecosystem wins, so a polyglot repo
# resolves deterministically. Conservative by design: an undetectable field is left "" for a human
# (the SA) to fill — the harness never guesses a stack it can't see.


def detect_stack(root="."):
    """Read a project's build markers → {test_command, package_manager, source_dirs}.

    Greenfield (no markers) → all "" (nothing to detect; the SA writes the stack at /architect).
    """
    root = Path(root)
    empty = {"test_command": "", "package_manager": "", "source_dirs": ""}

    def src_dirs():
        return "src/" if (root / "src").is_dir() else "."

    # Python — pyproject.toml or requirements.txt
    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
        pm = "uv" if (root / "uv.lock").exists() else "pip"
        return {"test_command": "pytest -q", "package_manager": pm, "source_dirs": src_dirs()}

    # Node — package.json (the project's own scripts.test wins; else a conservative default)
    pkg = root / "package.json"
    if pkg.exists():
        pm = "pnpm" if (root / "pnpm-lock.yaml").exists() else "npm"
        test_command = "npm test"
        try:
            scripts = (json.loads(pkg.read_text(encoding="utf-8")) or {}).get("scripts") or {}
            if isinstance(scripts, dict) and scripts.get("test"):
                test_command = scripts["test"]
        except (json.JSONDecodeError, OSError):
            pass
        return {"test_command": test_command, "package_manager": pm, "source_dirs": src_dirs()}

    # Rust — Cargo.toml
    if (root / "Cargo.toml").exists():
        return {"test_command": "cargo test", "package_manager": "cargo", "source_dirs": src_dirs()}

    # Go — go.mod (package-relative; no src/ convention)
    if (root / "go.mod").exists():
        return {"test_command": "go test ./...", "package_manager": "go", "source_dirs": "."}

    return empty


def set_field(text, section, key, value):
    """Replace the value of `- key:` inside the `## section` block, in-place.

    Preserves the line's trailing `# comment` and every other line of the document; changes only the
    FIRST matching key within the named section, so a same-named key in another section (e.g. `name`
    lives in both `## project` and `## role`) is untouched. Idempotent.
    """
    key_re = re.compile(r"^(-\s*" + re.escape(key) + r":\s*)(.*?)(\s*#.*)?$")
    lines = text.split("\n")
    in_section = False
    done = False
    for i, line in enumerate(lines):
        if line.startswith("## "):
            in_section = line.strip() == f"## {section}"
            continue
        if in_section and not done:
            m = key_re.match(line)
            if m:
                lines[i] = m.group(1) + value + (m.group(3) or "")
                done = True
    return "\n".join(lines)


def write_context(path, updates):
    """Apply (section, key, value) updates to HARNESS-CONTEXT.md via Python I/O (guard-safe).

    The guard intercepts Edit/Write *tool* calls, not Python file writes — same bypass board.py uses —
    which is exactly why the bootstrap (writing the file before any role is set) does not deadlock.
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    for section, key, value in updates:
        text = set_field(text, section, key, value)
    p.write_text(text, encoding="utf-8")
    return text


def parse_deps(root="."):
    """Dependency NAMES from the project's manifest(s) — to seed the SA's framework allowlist.

    requirements.txt (strip versions / extras / env-markers), package.json (`dependencies` keys only —
    not dev/build tooling), Cargo.toml (`[dependencies]` only). Missing manifest → []. Order-preserving,
    de-duplicated. Tolerant: a malformed manifest contributes nothing rather than raising.
    """
    root = Path(root)
    deps = []

    req = root / "requirements.txt"
    if req.exists():
        for line in req.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            name = re.split(r"[<>=!~;\[ ]", line, maxsplit=1)[0].strip()
            if name:
                deps.append(name)

    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8")) or {}
            deps.extend((data.get("dependencies") or {}).keys())
        except (json.JSONDecodeError, OSError):
            pass

    cargo = root / "Cargo.toml"
    if cargo.exists():
        in_deps = False
        for line in cargo.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("["):
                in_deps = s == "[dependencies]"
                continue
            if in_deps and "=" in s and not s.startswith("#"):
                name = s.split("=", 1)[0].strip()
                if name:
                    deps.append(name)

    seen, out = set(), []
    for d in deps:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


def main(argv=None):
    """Thin CLI the /init and /architect skills invoke. Never touches the role — only project context."""
    import argparse

    parser = argparse.ArgumentParser(prog="context_init")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_detect = sub.add_parser("detect", help="print the detected stack as JSON")
    p_detect.add_argument("--root", default=".")

    p_seed = sub.add_parser("seed-allowlist", help="print dependency names as JSON (brownfield)")
    p_seed.add_argument("--root", default=".")

    p_write = sub.add_parser("write", help="greenfield: record a CHOSEN field value")
    p_write.add_argument("--section", required=True)
    p_write.add_argument("--key", required=True)
    p_write.add_argument("--value", required=True)
    p_write.add_argument("--path", default="HARNESS-CONTEXT.md")

    p_set = sub.add_parser("set-stack", help="brownfield: detect → write the non-empty stack fields")
    p_set.add_argument("--path", default="HARNESS-CONTEXT.md")

    args = parser.parse_args(argv)

    if args.cmd == "detect":
        print(json.dumps(detect_stack(args.root)))
    elif args.cmd == "seed-allowlist":
        print(json.dumps(parse_deps(args.root)))
    elif args.cmd == "write":
        write_context(args.path, [(args.section, args.key, args.value)])
        print(f"wrote {args.section}.{args.key}")
    elif args.cmd == "set-stack":
        path = Path(args.path)
        detected = {k: v for k, v in detect_stack(path.parent).items() if v}
        if detected:
            write_context(path, [("stack", k, v) for k, v in detected.items()])
        print(json.dumps(detected))


if __name__ == "__main__":
    main()
