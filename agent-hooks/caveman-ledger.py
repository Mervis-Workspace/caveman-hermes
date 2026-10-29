#!/usr/bin/env python3
"""post_api_request hook — one ledger row per API call, tagged with the active mode.

This is the measurement primitive the caveman project lost when it left Claude
Code: Hermes reports exact token buckets per API call (input, output,
cache-read, cache-write, reasoning), so per-mode attribution is observed, not
estimated. Rows go to $HERMES_HOME/state/caveman-ledger.jsonl, one JSON object
per line, append-only.

Observer only: no stdout directive, always exit 0, never blocks a turn.
"""
import json
import os
import sys
import time
import importlib.machinery
import importlib.util

def _cli_path():
    """Locate the caveman CLI: explicit override, then the Hermes home, then alongside.

    CAVEMAN_CLI wins so a non-standard layout stays usable; $HERMES_HOME/bin is the
    install.sh location; the relative path covers a repo checkout used in place.
    """
    explicit = os.environ.get("CAVEMAN_CLI")
    if explicit and os.path.exists(explicit):
        return explicit
    home = os.environ.get("HERMES_HOME") or os.path.join(os.path.expanduser("~"), ".hermes")
    in_home = os.path.join(home, "bin", "caveman")
    if os.path.exists(in_home):
        return in_home
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bin", "caveman")


CLI = _cli_path()


def _load(path):
    """Import the caveman CLI as a module (no .py suffix, so load by path)."""
    spec = importlib.util.spec_from_loader(
        "caveman_cli", importlib.machinery.SourceFileLoader("caveman_cli", os.path.normpath(path)))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
def _field(payload, key):
    """Read a hook field: Hermes puts event kwargs under ``extra`` and keeps only
    tool_name/tool_input/session_id/cwd/profile at the top level. Accept both
    shapes so synthetic (flat) and production (nested) payloads behave the same."""
    extra = payload.get("extra")
    if isinstance(extra, dict) and key in extra:
        return extra[key]
    return payload.get(key)


FIELDS = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens", "reasoning_tokens")


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0

    try:
        cli = _load(CLI)
    except Exception:
        return 0

    sid = str(payload.get("session_id") or "")
    usage = _field(payload, "usage")
    usage = usage if isinstance(usage, dict) else {}

    try:
        mode, _source = cli.resolve_mode(sid)
    except Exception:
        mode = "unknown"

    row = {
        "ts": time.time(),
        "session": sid,
        "turn": _field(payload, "turn_id"),
        "api_call": _field(payload, "api_call_count"),
        "api_request_id": _field(payload, "api_request_id"),
        "mode": mode,
        "model": _field(payload, "model"),
        "provider": _field(payload, "provider"),
        "platform": _field(payload, "platform"),
        "finish_reason": _field(payload, "finish_reason"),
        "chars": _field(payload, "assistant_content_chars"),
        "tool_calls": _field(payload, "assistant_tool_call_count"),
    }
    for field in FIELDS:
        try:
            row[field] = int(usage.get(field) or 0)
        except (TypeError, ValueError):
            row[field] = 0

    try:
        path = cli.LEDGER_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
