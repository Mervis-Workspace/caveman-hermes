# Caveman for Hermes

Terse output mode for [Hermes Agent](https://github.com/NousResearch/hermes-agent):
answer first, fluff gone, every technical fact kept. This repository is the
Hermes-native port of [Caveman](https://github.com/JuliusBrussee/caveman) by
**Julius Brussee** — the skill voice, the rules and the honest-numbers policy are
his work; only the plumbing is new.

One command installs eight skills, two lifecycle hooks and a small CLI:

```bash
git clone https://github.com/Mervis-Workspace/caveman-hermes.git
cd caveman-hermes && bash install.sh
```

Then, in any Hermes session:

```
/caveman          # terse voice, this session
/ultracave        # maximum compression
/megacave         # Classical Chinese, fewer characters
/caveman status   # report the tracked mode
/caveman-stats    # recorded output + cache-read tokens, per mode
```

## Thanks

- **Caveman** — [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman),
  Copyright 2026 Julius Brussee, Apache-2.0. The skill texts in `skills/` are his,
  taken from tag `v4.0.1` (`d262ab3`). Without his writing there is nothing to port.
- **Hermes Agent** — [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent),
  whose skill commands and lifecycle hooks this port is built on.

Modifications are listed in [NOTICE](./NOTICE) and marked inside the files.

## Why this version differs from the original

Upstream is built for Claude Code. Hermes has different primitives, so the
Claude-specific parts could not be copied, only reimplemented.

| Concern | Upstream (Claude Code) | This port (Hermes) |
|---|---|---|
| Mode state | flag files read by `caveman-mode-tracker.js` | JSON state at `$HERMES_HOME/state/caveman.json` |
| Mode enforcement | `SessionStart` handler + statusline | `pre_llm_call` shell hook injects the mode every turn |
| Activation | upstream hook intercepts `/caveman` | the hook parses Hermes's skill-invocation scaffold, so `/ultracave` persists the mode without the model cooperating |
| Token accounting | reads Claude's JSONL transcript | `post_api_request` hook records Hermes's own per-call buckets: input, output, cache-read, cache-write, reasoning |
| Mode attribution | mode-transition log beside the transcript | every ledger row is stamped with the mode active at that call |
| Statusline | Claude statusline badge | `caveman status`, plus the hook's `Caveman mode: <mode>` line |
| Savings | already unknown upstream | still unknown — no paired non-caveman run exists |

Three consequences worth knowing:

1. **Per-call truth instead of transcript inference.** Hermes reports usage per API
   call, so `caveman stats` sums observed numbers rather than parsing a log. On a
   fresh session the ledger reconciles exactly with Hermes's own `state.db` totals.
2. **Enforcement is not model-dependent.** A `/caveman`, `/caveman ultra`,
   `/ultracave` or `/megacave` turn writes the mode inside the hook. Later turns,
   context compression and tool results cannot drop it; `stop caveman` and
   `normal mode` clear it deterministically.
3. **No statusline, no savings badge.** Hermes has no per-token status bar, so this
   port reports on demand and claims no reduction percentage.

What did **not** change: the skill rules themselves (answer-first, payload verbatim,
never drop a negation, plain prose for safety warnings and confirmations), plus
`caveman-commit`, `caveman-review` and `caveman-compress`, which need no host
plumbing and are shipped verbatim.

## Install

Requirements: Hermes Agent with shell hooks, `python3` (3.9+), and a writable
`$HERMES_HOME` (default `~/.hermes`).

```bash
bash install.sh                      # into $HERMES_HOME
HERMES_HOME=/opt/hermes bash install.sh   # custom home / profile
bash tests/verify.sh                 # 14 behaviour checks
```

The installer copies files, adds one `pre_llm_call` and one `post_api_request`
entry to `config.yaml`, adds the matching consent entries to
`shell-hooks-allowlist.json`, and backs the config up first. It is idempotent: run
it twice and nothing is added twice. It touches nothing outside the Hermes home.

Manual install, if you prefer no script: copy `bin/caveman` to `$HERMES_HOME/bin/`,
`agent-hooks/*.py` to `$HERMES_HOME/agent-hooks/` (chmod +x), and each
`skills/<name>/` to `$HERMES_HOME/skills/productivity/`, then add the two hook
entries yourself (see `scripts/configure-hooks.py` for the exact shape).

After installing:

```bash
hermes gateway restart    # hooks load at session start
/reload-skills            # inside a live session
```

Uninstall: `bash uninstall.sh` (keeps skills and recorded usage),
`--with-skills`, `--purge` for a full removal.

## How it works

```
bin/caveman                      mode CLI + stats reader (python3 stdlib)
agent-hooks/caveman-mode-guard.py    pre_llm_call  -> activate + enforce
agent-hooks/caveman-ledger.py        post_api_request -> one row per API call
skills/…                          the eight skills (upstream text + Hermes notes)

$HERMES_HOME/state/caveman.json           {"default": …, "sessions": {…}}
$HERMES_HOME/state/caveman-ledger.jsonl   one JSON row per API call
```

Mode resolution: session entry → `CAVEMAN_DEFAULT_MODE` → global default →
upstream `~/.config/caveman/config.json` → `off`.

```bash
~/.hermes/bin/caveman set caveman          # this session
~/.hermes/bin/caveman set --global caveman # every new session
~/.hermes/bin/caveman off                  # or say "stop caveman"
~/.hermes/bin/caveman status --json
~/.hermes/bin/caveman stats --all --since 7d --json --share
```

Cost when active: about 45 input tokens per turn for the injected directive; zero
when the mode is off.

## Honest numbers

`caveman stats` reports what was spent, never what would have been spent.

- Output, cache-read, uncached input, cache-write and reasoning tokens come from
  Hermes per API call, summed across the session and split by mode.
- Sessions recorded before the hooks were installed fall back to `state.db` totals
  and are labelled as having no mode attribution.
- A single call reporting more than 32,768 output tokens is flagged as likely
  cumulative provider usage. The number is left as recorded, not "corrected".
- No reduction percentage, dollar figure, rule overhead or net result is ever
  derived, because there is no paired run of the same session without caveman.
  See [docs/HONEST-NUMBERS.md](./docs/HONEST-NUMBERS.md).

## Layout

```
bin/caveman                  CLI: set, status, off, stats, help
agent-hooks/                 pre_llm_call guard, post_api_request ledger
scripts/configure-hooks.py   config.yaml + allowlist wiring (add/remove)
skills/                      caveman, caveman-help, caveman-stats,
                             caveman-commit, caveman-review, caveman-compress,
                             ultracave, megacave
tests/verify.sh              14 behaviour checks against an installed home
docs/HONEST-NUMBERS.md       what these numbers can and cannot say
NOTICE                       attribution and change list
LICENSE                      Apache-2.0 (upstream license)
```

## Compatibility

Exercised on macOS 26 with Hermes Agent's `pre_llm_call` and `post_api_request`
shell-hook events and the skill-slash command path. The hook payload nests event
kwargs under `extra`; the scripts accept both nested and flat shapes, so they keep
working if that envelope changes for synthetic payloads. Debian/Ubuntu are expected
to behave the same (python3 stdlib only) but were not exercised.

## License

Apache License 2.0 — see [LICENSE](./LICENSE) and [NOTICE](./NOTICE).
The skills are upstream work by Julius Brussee; the Hermes plumbing is new.
