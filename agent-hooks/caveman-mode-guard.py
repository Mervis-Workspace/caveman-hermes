#!/usr/bin/env python3
"""pre_llm_call hook — enforce the caveman mode for every turn of a session.

Reads the mode that `caveman set` stored for this session and injects a short
style directive into the current user message (the documented pre_llm_call
channel). That is what makes caveman native in Hermes: the mode survives turns,
context compression and new tool results without re-invoking the skill.

Fail-open: any error means no injection, never a broken turn. Silence when the
mode is off.
"""
import json
import os
import re
import sys
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

# Style-only directive: the payload rules (code/paths/errors verbatim, keep each
# negation) are restated because they are the expensive failure mode.
DIRECTIVES = {
    "caveman": ("Caveman mode: caveman. Answer first, no greeting/recap/hedging, short words, "
                "one idea per sentence. Code, paths, numbers and error strings verbatim; keep "
                "every not/never/only. Safety warnings and confirmations in plain prose. "
                "Full rules: skill_view('caveman')."),
    "ultracave": ("Caveman mode: ultracave. Fragments, one word when one is enough, each fact "
                  "once, no ceremony. Code, paths, numbers and error strings verbatim; keep every "
                  "not/never/only. Safety warnings and confirmations in plain prose. "
                  "Full rules: skill_view('ultracave')."),
    "megacave": ("Caveman mode: megacave. Classical Chinese 文言文 register, far fewer characters. "
                 "Technical terms, code, paths, numbers and error strings verbatim; keep every "
                 "not/never/only. Safety warnings and confirmations in plain prose. "
                 "Full rules: skill_view('megacave')."),
}

def _field(payload, key):
    """Read a hook field: Hermes puts event kwargs under ``extra`` and keeps only
    tool_name/tool_input/session_id/cwd/profile at the top level. Accept both
    shapes so synthetic (flat) and production (nested) payloads behave the same."""
    extra = payload.get("extra")
    if isinstance(extra, dict) and key in extra:
        return extra[key]
    return payload.get(key)


OFF_REQUEST = re.compile(r"^(?:please\s+)?(?:stop\s+caveman|normal\s+mode|caveman\s+off|exit\s+caveman)\b", re.I)

# Hermes expands "/<skill>" into "[IMPORTANT: The user has invoked the \"<name>\" skill, ...]"
# with the whole skill body embedded, then the typed instruction after this marker.
_INVOKE_RE = re.compile(r'^\[IMPORTANT: The user has invoked the "([^"]+)" skill')
_INSTR_MARKER = "The user has provided the following instruction alongside the skill invocation: "
ACTIVATING_SKILLS = {"caveman", "ultracave", "megacave"}


def _invoked_skill(message):
    """(skill_name, typed_instruction) for a /skill turn, else (None, "").

    Only the typed instruction is inspected for aliases: the embedded skill body
    itself names ultracave/megacave, so scanning the whole payload would flip modes.
    """
    m = _INVOKE_RE.match(message)
    if not m:
        return None, ""
    name = m.group(1).strip().lower()
    idx = message.rfind(_INSTR_MARKER)
    instr = message[idx + len(_INSTR_MARKER):][:200] if idx >= 0 else ""
    return name, instr


def _target_mode(name, instr):
    """Mode a /skill invocation activates, or None when it must not change state."""
    low = instr.lower()
    if name == "caveman":
        if re.search(r"\bstatus\b", low):
            return None  # /caveman status: report only, change nothing
        if "ultra" in low:
            return "ultracave"
        if "wenyan" in low or "mega" in low:
            return "megacave"
        return "caveman"
    return name


def load_cli():
    return _load(CLI)


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0

    try:
        cli = load_cli()
    except Exception:
        return 0

    sid = str(_field(payload, "session_id") or "")
    message = _field(payload, "user_message")
    message = message if isinstance(message, str) else ""

    # Explicit switch-off by the human, short message only, so a question that
    # merely mentions the phrase never flips the mode.
    if message and len(message.strip()) <= 40 and OFF_REQUEST.match(message.strip()):
        try:
            state = cli.load_state()
            if sid and sid in (state.get("sessions") or {}):
                state["sessions"][sid] = {"mode": "off", "set_at": __import__("time").time()}
                cli.save_state(state)
        except Exception:
            pass
        return 0

    # A /caveman, /caveman ultra, /ultracave or /megacave turn persists the mode
    # itself, so activation never depends on the model remembering to run the CLI.
    try:
        skill, instr = _invoked_skill(message)
        if skill in ACTIVATING_SKILLS:
            target = _target_mode(skill, instr)
            if target and sid:
                state = cli.load_state()
                state.setdefault("sessions", {})[sid] = {"mode": target, "set_at": __import__("time").time()}
                cli.save_state(state)
    except Exception:
        pass

    try:
        mode, _source = cli.resolve_mode(sid)
        directive = DIRECTIVES.get(mode)
    except Exception:
        return 0
    if not directive:
        return 0

    sys.stdout.write(json.dumps({"context": directive}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
