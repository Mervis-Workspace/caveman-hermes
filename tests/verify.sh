#!/usr/bin/env bash
# Post-install verification. Proves behaviour, not just file presence.
#
#   bash tests/verify.sh                  # verify $HERMES_HOME
#   HERMES_HOME=/tmp/probe bash tests/verify.sh
#   bash tests/verify.sh --live           # also run one real Hermes turn
#
# Eleven checks; the script exits non-zero on the first failure.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$HERE/.." && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
CLI="$HERMES_HOME/bin/caveman"
GUARD="$HERMES_HOME/agent-hooks/caveman-mode-guard.py"
LEDGER="$HERMES_HOME/agent-hooks/caveman-ledger.py"
LEDGER_FILE="$HERMES_HOME/state/caveman-ledger.jsonl"
SID="verify-$$"
PASS=0
FAIL=0

ok()   { printf '  PASS  %s\n' "$1"; PASS=$((PASS+1)); }
bad()  { printf '  FAIL  %s\n' "$1"; FAIL=$((FAIL+1)); }
check(){ # check <label> <expected-substring> <actual>
  case "$3" in *"$2"*) ok "$1" ;; *) bad "$1 — wanted '$2', got '$3'" ;; esac
}

echo "caveman for Hermes — verification ($HERMES_HOME)"

# 1-2. files and modes
[ -x "$CLI" ] && ok "CLI installed and executable" || bad "CLI missing at $CLI"
check "valid mode accepted" "Caveman mode: ultracave" "$("$CLI" set ultracave --session "$SID" 2>&1)"
check "status reads stored mode" "Caveman mode: ultracave" "$("$CLI" status --session "$SID" 2>&1)"
check "off clears the mode" "Caveman mode: off" "$("$CLI" off --session "$SID" 2>&1 | tail -1)"

# 3. hook consent
check "mode-guard allowlisted" "caveman-mode-guard.py" "$(cat "$HERMES_HOME/shell-hooks-allowlist.json")"

# 4. guard injects through the production parser
"$CLI" set caveman --session "$SID" >/dev/null
OUT="$(printf '{"hook_event_name":"pre_llm_call","session_id":"%s","extra":{"user_message":"hi"}}' "$SID" \
      | "$GUARD")"
check "guard injects mode directive" "Caveman mode: caveman" "$OUT"

# 5. skill invocation activates the mode without model cooperation
BODY="$(cat "$HERMES_HOME/skills/productivity/ultracave/SKILL.md")"
MSG="[IMPORTANT: The user has invoked the \"ultracave\" skill, indicating they want you to follow its instructions. The full skill content is loaded below.]\\n\\n$BODY"
python3 - "$GUARD" "$SID" "$MSG" <<'PY'
import json, subprocess, sys
guard, sid, msg = sys.argv[1], sys.argv[2], sys.argv[3]
payload = {"hook_event_name": "pre_llm_call", "session_id": sid, "extra": {"user_message": msg}}
out = subprocess.run([guard], input=json.dumps(payload), capture_output=True, text=True)
sys.exit(0 if "ultracave" in out.stdout else 1)
PY
[ $? -eq 0 ] && ok "/ultracave activates the mode from the skill scaffold" || bad "/ultracave did not activate the mode"

# 6. switch-off phrase
printf '{"hook_event_name":"pre_llm_call","session_id":"%s","extra":{"user_message":"stop caveman"}}' "$SID" \
  | "$GUARD" >/dev/null
check "off phrase clears the mode" "Caveman mode: off" "$("$CLI" status --session "$SID" 2>&1 | head -1)"

# 7-8. ledger row from a synthetic API call
"$CLI" set caveman --session "$SID" >/dev/null
BEFORE=$( [ -f "$LEDGER_FILE" ] && wc -l < "$LEDGER_FILE" || echo 0 )
printf '{"hook_event_name":"post_api_request","session_id":"%s","extra":{"turn_id":"t","api_call_count":1,"model":"m","provider":"p","platform":"cli","finish_reason":"stop","assistant_content_chars":10,"assistant_tool_call_count":0,"usage":{"input_tokens":100,"output_tokens":40,"cache_read_tokens":900,"cache_write_tokens":0,"reasoning_tokens":3}}}' "$SID" \
  | "$LEDGER"
AFTER=$( [ -f "$LEDGER_FILE" ] && wc -l < "$LEDGER_FILE" || echo 0 )
[ "$AFTER" -gt "$BEFORE" ] && ok "ledger recorded an API call" || bad "ledger did not grow ($BEFORE -> $AFTER)"
check "stats reads ledger tokens" "Output tokens:         40" "$("$CLI" stats --session "$SID" 2>&1)"
check "stats attributes the mode" "caveman" "$("$CLI" stats --session "$SID" 2>&1)"
check "savings reported unknown" "Savings: unknown" "$("$CLI" stats --session "$SID" 2>&1)"

# 9. stats honesty on an empty session: no numbers invented
EMPTY="$(printf 'verify-empty-%s' "$SID")"
check "empty session says nothing was recorded" "nothing recorded" "$("$CLI" stats --session "$EMPTY" 2>&1)"

# 10. hooks doctor, when the CLI is available
if command -v hermes >/dev/null 2>&1; then
  # Scope to our two hooks: unrelated hooks in this home are not our verdict.
  DOCTOR="$(HERMES_HOME="$HERMES_HOME" hermes hooks doctor 2>&1)"
  OUR_LINES="$(printf '%s\n' "$DOCTOR" | grep -A3 -E "caveman-(mode-guard|ledger)\.py")"
  case "$OUR_LINES" in
    *"✗"*) bad "hermes hooks doctor reported a problem for a caveman hook" ;;
    "") bad "hermes hooks doctor listed no caveman hooks (not registered?)" ;;
    *)
      case "$OUR_LINES" in
        *"allowlisted (approved"*) ok "both hooks registered, allowlisted and running clean" ;;
        *) bad "hooks registered but not allowlisted" ;;
      esac ;;
  esac
else
  echo "  SKIP  hermes hooks doctor (hermes not on PATH)"
fi

# 11. optional live turn
if [ "${1:-}" = "--live" ]; then
  if command -v hermes >/dev/null 2>&1; then
    OUT="$(HERMES_HOME="$HERMES_HOME" CAVEMAN_DEFAULT_MODE=ultracave \
           hermes chat -q 'In one line: what does git stash do?' 2>&1)"
    check "live turn produced a reply" "Shelves" "$OUT"
  else
    echo "  SKIP  live turn (hermes not on PATH)"
  fi
fi

# cleanup probe artefacts
"$CLI" off --session "$SID" >/dev/null 2>&1 || true
python3 - "$HERMES_HOME" "$SID" <<'PY'
import json, pathlib, sys
home, sid = pathlib.Path(sys.argv[1]), sys.argv[2]
sp = home / "state" / "caveman.json"
if sp.exists():
    st = json.loads(sp.read_text())
    st.get("sessions", {}).pop(sid, None)
    sp.write_text(json.dumps(st, indent=2, sort_keys=True) + "\n")
lp = home / "state" / "caveman-ledger.jsonl"
if lp.exists():
    kept = [l for l in lp.read_text().splitlines()
            if l.strip() and json.loads(l).get("session") != sid]
    lp.write_text("\n".join(kept) + ("\n" if kept else ""))
PY

echo ""
printf 'RESULT: %d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
