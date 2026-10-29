---
name: caveman-stats
description: >
  Show recorded output and cache-read token usage and mode attribution for the
  current Hermes session, or for recorded sessions. Trigger: /caveman-stats.
---
<!-- Hermes port (caveman-hermes): modified from upstream v4.0.1 — see NOTICE. -->

In Hermes this skill is a thin wrapper over the native reader. Do **not** compute,
recompute or re-round anything yourself: run the command and relay its output
verbatim in a fenced code block.

```
~/.hermes/bin/caveman stats
```

## What backs the numbers

- `post_api_request` shell hook (`~/.hermes/agent-hooks/caveman-ledger.py`) appends one
  JSON row per API call to `$HERMES_HOME/state/caveman-ledger.jsonl`, tagged with the mode
  active at that call: input, output, cache-read, cache-write and reasoning tokens.
- `pre_llm_call` shell hook (`~/.hermes/agent-hooks/caveman-mode-guard.py`) enforces the
  stored mode on every turn, so a mode survives turns, compression and tool results
  without re-invoking the skill.
- Sessions that ran before the hooks were wired fall back to `$HERMES_HOME/state.db`
  session totals, and the report says so ("no ledger rows for this session"). Those rows
  carry no mode attribution.

Per-mode rows are observed, not estimated. A single call reporting more than 32,768
output tokens is flagged as likely cumulative provider usage; the recorded number is
left untouched.

## Variants

```
~/.hermes/bin/caveman stats --all          # recorded sessions, newest first
~/.hermes/bin/caveman stats --since 7d     # 30m / 24h / 7d
~/.hermes/bin/caveman stats --json         # machine-readable
~/.hermes/bin/caveman stats --share        # same numbers, session id omitted
~/.hermes/bin/caveman status               # mode only
```

## Savings stay unknown

The ledger records what was spent, never what would have been spent without caveman.
No paired non-caveman run of the same session exists, so no reduction percentage,
dollar figure, rule overhead or net result is derived from these counts. Say
"unknown" and stop; do not infer a saving from a smaller output count.

Claude Code and Gemini CLI instructions from the upstream project do not apply here:
this host has no `~/.claude` transcripts and no Gemini session metrics. The Hermes
reader is the only source.
