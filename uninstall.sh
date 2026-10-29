#!/usr/bin/env bash
# caveman for Hermes — uninstaller.
#
# Removes the CLI, both hooks, the hook config entries and their consent entries.
# Leaves the skills in place by default (they are the actual product); pass
# --with-skills to remove those too, and --purge to delete recorded usage.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
WITH_SKILLS=0
PURGE=0
for arg in "$@"; do
  case "$arg" in
    --with-skills) WITH_SKILLS=1 ;;
    --purge) PURGE=1 ;;
    *) printf 'unknown flag: %s\n' "$arg" >&2; exit 2 ;;
  esac
done

python3 "$REPO_DIR/scripts/configure-hooks.py" --home "$HERMES_HOME" --remove

rm -f "$HERMES_HOME/bin/caveman" \
      "$HERMES_HOME/agent-hooks/caveman-mode-guard.py" \
      "$HERMES_HOME/agent-hooks/caveman-ledger.py"
echo "files: CLI and hooks removed"

if [ "$WITH_SKILLS" -eq 1 ]; then
  for skill in caveman caveman-help caveman-stats caveman-commit caveman-review caveman-compress ultracave megacave; do
    rm -rf "$HERMES_HOME/skills/productivity/$skill"
  done
  echo "skills: removed"
else
  echo "skills: kept (pass --with-skills to remove)"
fi

if [ "$PURGE" -eq 1 ]; then
  rm -f "$HERMES_HOME/state/caveman.json" "$HERMES_HOME/state/caveman-ledger.jsonl"
  echo "state: mode + recorded usage deleted"
else
  echo "state: kept at $HERMES_HOME/state/caveman* (pass --purge to delete)"
fi

echo "hooks are read at session start: an already-running process keeps them until it exits"
