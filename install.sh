#!/usr/bin/env bash
# caveman for Hermes — installer.
#
# Copies the CLI, the two shell hooks and the eight skills into a Hermes home,
# then wires the hooks into config.yaml and the consent allowlist.
#
#   bash install.sh              # into $HERMES_HOME (default ~/.hermes)
#   HERMES_HOME=/tmp/probe bash install.sh
#
# Idempotent: re-running adds nothing twice. Every config write is backed up to
# <home>/backups/ and guarded by an anchor count. Nothing outside the Hermes home
# is touched.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"

say() { printf '%s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || die "python3 is required"

say "caveman for Hermes -> $HERMES_HOME"

mkdir -p "$HERMES_HOME"/{bin,agent-hooks,skills/productivity}

# --- files ---------------------------------------------------------------
install -m 0755 "$REPO_DIR/bin/caveman"                        "$HERMES_HOME/bin/caveman"
install -m 0755 "$REPO_DIR/agent-hooks/caveman-mode-guard.py"  "$HERMES_HOME/agent-hooks/"
install -m 0755 "$REPO_DIR/agent-hooks/caveman-ledger.py"      "$HERMES_HOME/agent-hooks/"
say "files: bin/caveman, agent-hooks/{caveman-mode-guard,caveman-ledger}.py"

for skill in caveman caveman-help caveman-stats caveman-commit caveman-review caveman-compress ultracave megacave; do
  if [ -d "$HERMES_HOME/skills/productivity/$skill" ]; then
    rm -rf "$HERMES_HOME/skills/productivity/$skill"
  fi
  cp -R "$REPO_DIR/skills/$skill" "$HERMES_HOME/skills/productivity/"
done
say "skills: 8 installed under skills/productivity/"

# --- config + consent ----------------------------------------------------
python3 "$REPO_DIR/scripts/configure-hooks.py" --home "$HERMES_HOME" --add

# --- verification --------------------------------------------------------
say ""
say "verifying:"
"$HERMES_HOME/bin/caveman" status || die "caveman status failed"

if command -v hermes >/dev/null 2>&1; then
  HERMES_HOME="$HERMES_HOME" hermes hooks doctor 2>&1 | tail -n 3 || true
else
  say "note: 'hermes' not on PATH — run 'hermes hooks doctor' yourself"
fi

cat <<'EOF'

Done. Next:
  1. Shell hooks are read at session start: open a new session before relying on
     them. An already-running process keeps the previous hook set until it exits.
  2. Reload skills in a live session:  /reload-skills
  3. Use it:
       /caveman            # terse voice, this session
       /ultracave          # maximum compression
       /caveman status     # report the tracked mode
       /caveman-stats      # recorded output + cache-read tokens, per mode
       ~/.hermes/bin/caveman off
EOF
