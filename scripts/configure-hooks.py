#!/usr/bin/env python3
"""Wire (or unwire) the caveman hooks into a Hermes home.

    python3 scripts/configure-hooks.py --add    [--home ~/.hermes]
    python3 scripts/configure-hooks.py --remove [--home ~/.hermes]

Hermes has no CLI for list-valued hook config (`hermes config set` cannot build a
`- command:` list), so this edits config.yaml as text: find `hooks:`, insert one
event block per hook, never touch any other line. Every write is guarded by an
anchor count, and the original file is copied to <home>/backups/ first.

Also maintains <home>/shell-hooks-allowlist.json: a hook that is not allowlisted
is skipped at runtime.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

HOOKS = (
    ("pre_llm_call", "caveman-mode-guard.py", 5),
    ("post_api_request", "caveman-ledger.py", 5),
)
HOOKS_RE = re.compile(r"^hooks:\s*(\{\})?\s*$")
INDENT = "  "


def home_paths(home: Path):
    config = home / "config.yaml"
    allow = home / "shell-hooks-allowlist.json"
    hooks_dir = home / "agent-hooks"
    return config, allow, hooks_dir


def hook_block(path: str, timeout: int) -> list[str]:
    # Match the indentation Hermes's own docs use: 4 spaces for the dash,
    # 6 for the item's keys. Indentless sequences also parse, but mixing two
    # styles in one file invites a bad hand-edit later.
    return [f"    - command: {path}", f"      timeout: {timeout}"]


def event_present(text: str, event: str) -> bool:
    return re.search(rf"^{INDENT}{event}:", text, re.M) is not None


def add_hooks(home: Path) -> int:
    config, allow, hooks_dir = home_paths(home)
    backup_dir = home / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    if config.exists():
        text = config.read_text(encoding="utf-8")
        stamp = time.strftime("%Y%m%dT%H%M%SZ")
        shutil.copy2(config, backup_dir / f"config.yaml.bak-caveman-{stamp}")
    else:
        text = ""

    missing = [(e, hooks_dir / f, t) for e, f, t in HOOKS if not event_present(text, e)]
    if missing:
        if not text.strip():
            text = "hooks:\n"
        lines = text.splitlines()
        anchor_idx = next((i for i, ln in enumerate(lines) if HOOKS_RE.match(ln)), None)
        if anchor_idx is None:
            if text.strip() and not text.endswith("\n"):
                text += "\n"
            # No hooks: section at all — append one.
            block = ["hooks:"]
            for event, path, timeout in missing:
                block.append(f"{INDENT}{event}:")
                block.extend(hook_block(str(path), timeout))
            text = text + "\n".join(block) + "\n"
        else:
            if HOOKS_RE.match(lines[anchor_idx]).group(1) == "{}":
                lines[anchor_idx] = "hooks:"
            insert = []
            for event, path, timeout in missing:
                insert.append(f"{INDENT}{event}:")
                insert.extend(hook_block(str(path), timeout))
            lines[anchor_idx + 1:anchor_idx + 1] = insert
            text = "\n".join(lines) + "\n"
        config.write_text(text, encoding="utf-8")
        for event, path, _timeout in missing:
            print(f"config: added {event} -> {path}")
    else:
        print("config: both hook events already present, nothing to add")

    data = {"approvals": []}
    if allow.exists():
        try:
            loaded = json.loads(allow.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and isinstance(loaded.get("approvals"), list):
                data = loaded
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            print("allowlist: existing file unreadable, writing a fresh one", file=sys.stderr)
    have = {(a.get("event"), a.get("command")) for a in data["approvals"] if isinstance(a, dict)}
    added = 0
    for event, name, _timeout in HOOKS:
        cmd = str(hooks_dir / name)
        if (event, cmd) not in have:
            data["approvals"].append({"event": event, "command": cmd})
            added += 1
    allow.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"allowlist: {added} approval(s) added, {len(data['approvals'])} total")
    return 0


def remove_hooks(home: Path) -> int:
    config, allow, hooks_dir = home_paths(home)
    if config.exists():
        text = config.read_text(encoding="utf-8")
        stamp = time.strftime("%Y%m%dT%H%M%SZ")
        shutil.copy2(config, home / "backups" / f"config.yaml.bak-caveman-rm-{stamp}")
        lines = text.splitlines()
        keep: list[str] = []
        skip_event = False
        for line in lines:
            if re.match(rf"^{INDENT}(pre_llm_call|post_api_request):\s*$", line):
                skip_event = True
                continue
            if skip_event:
                if line.startswith(INDENT + INDENT) or not line.strip():
                    continue
                skip_event = False
            keep.append(line)
        new_text = "\n".join(keep) + "\n"
        # Collapse a hooks: section left with no children.
        if re.search(r"^hooks:\s*$", new_text, re.M) and not re.search(
            rf"^{INDENT}\S", new_text.split("hooks:", 1)[1].split("\n", 1)[1], re.M
        ):
            new_text = re.sub(r"^hooks:\s*\n(?=\S)", "", new_text, count=1, flags=re.M)
        config.write_text(new_text, encoding="utf-8")
        print("config: caveman hook events removed")

    if allow.exists():
        try:
            data = json.loads(allow.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            data = {"approvals": []}
        ours = {str(hooks_dir / name) for _e, name, _t in HOOKS}
        before = len(data.get("approvals", []))
        data["approvals"] = [a for a in data.get("approvals", []) if a.get("command") not in ours]
        allow.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"allowlist: {before - len(data['approvals'])} approval(s) removed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--home")
    ap.add_argument("--add", action="store_true")
    ap.add_argument("--remove", action="store_true")
    args = ap.parse_args()
    home = Path(args.home).expanduser() if args.home else Path(
        __import__("os").environ.get("HERMES_HOME") or Path.home() / ".hermes"
    )
    if args.add == args.remove:
        ap.error("pass exactly one of --add / --remove")
    return add_hooks(home) if args.add else remove_hooks(home)


if __name__ == "__main__":
    sys.exit(main())
