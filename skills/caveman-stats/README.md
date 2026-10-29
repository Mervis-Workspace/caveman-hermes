<!-- Hermes port (caveman-hermes): modified from upstream v4.0.1 — see NOTICE. -->

# caveman-stats (Hermes native)

Recorded session usage and mode attribution. Savings stay unknown without a measured
comparison.

## What it does

`~/.hermes/bin/caveman stats` reads two local sources:

- `$HERMES_HOME/state/caveman-ledger.jsonl` — one JSON row per API call, written by the
  `post_api_request` hook `~/.hermes/agent-hooks/caveman-ledger.py`. Each row carries the
  mode active for that call plus Hermes's own token buckets: input, output, cache-read,
  cache-write, reasoning.
- `$HERMES_HOME/state.db` — session and message store, used for turn and tool-call counts
  and as the fallback total for sessions that ran before the hooks existed.

That replaces the upstream Claude Code path (a mode-tracker hook reading a JSONL
transcript), which cannot run here: this host has no `~/.claude`.

## How to invoke

```
/caveman-stats
~/.hermes/bin/caveman stats --all
~/.hermes/bin/caveman stats --since 7d
~/.hermes/bin/caveman stats --json
~/.hermes/bin/caveman stats --share
```

The model relays the command output verbatim. It does not estimate the numbers.

## Example output

```
Caveman Stats — Hermes native
──────────────────────────────────
Session:   local-ba8bf307a2085d38
Model:     deepseek/deepseek-v4.1-flash-1017
Turns:     2 assistant message(s), 1 tool call(s)
──────────────────────────────────
Output tokens:         179
Cache-read tokens:     44,928
Input (uncached):      1,680
Reasoning tokens:      104
Recorded API calls:    2
Source: caveman ledger (post_api_request hook)
──────────────────────────────────
Mode: caveman (current; source: default)
By mode (recorded API calls):
  caveman       2 call(s)         179 output        44,928 cache-read
──────────────────────────────────
Savings: unknown — no measured comparison for this session.
```

## Measurement limits

- Spending is observed; a saving is not. There is no paired non-caveman run of the same
  session, so no percentage, dollar value or net result is produced.
- Mode attribution exists only for calls made after the hooks were wired. Older sessions
  report session totals with no mode attribution.
- A single call above 32,768 output tokens is flagged as likely cumulative provider usage
  rather than silently summed or corrected.

## See also

- [`SKILL.md`](./SKILL.md) — wrapper contract
- `~/.hermes/bin/caveman help` — full command surface
