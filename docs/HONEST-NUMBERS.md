# Honest numbers

`caveman stats` measures spend. It does not measure saving.

## What is measured

One ledger row per API call, written by the `post_api_request` shell hook from the
numbers the model provider returned to Hermes:

| Field | Source |
|---|---|
| `input_tokens` | uncached prompt tokens reported for that call |
| `output_tokens` | completion tokens reported for that call |
| `cache_read_tokens` | prompt tokens served from the provider cache |
| `cache_write_tokens` | tokens written to the provider cache |
| `reasoning_tokens` | hidden reasoning tokens, where the provider reports them |
| `mode` | the caveman mode active when that call returned |

The report sums those rows for a session and groups them by mode. Every number can
be traced back to a line in `$HERMES_HOME/state/caveman-ledger.jsonl`.

## What is not measured

There is no control arm. The same session is never run twice — once with caveman
and once without — so nothing in this repository can say "caveman saved N tokens"
or "N percent". Output-token counts are not a saving: a terse session is one
observation, not a comparison. Accordingly the tool never prints a percentage, a
dollar saving, rule overhead or a net result, and it refuses to estimate one when
asked.

## Known limits

1. **No attribution for old sessions.** Calls made before the hooks were installed
   have no mode stamp. The report falls back to `state.db` session totals and says
   so. Those totals cover the whole session and cannot be split by mode.
2. **Provider usage shapes vary.** Some OpenAI-compatible gateways report cumulative
   counters instead of per-call usage. A single call above 32,768 output tokens is
   flagged; the recorded value is displayed unchanged.
3. **Auxiliary work is excluded.** Title generation, compression and memory calls
   fire `post_auxiliary_call`, not `post_api_request`, so they do not inflate a
   session's caveman numbers.
4. **The directive costs input tokens.** While a mode is active, roughly 45 input
   tokens per turn carry the style instruction. That cost is real and is counted in
   the ledger like everything else.
5. **Delegated subagents** run their own sessions; they inherit the model but not
   the mode unless the mode is set globally.

## Correct use

- "How much did this session spend in caveman mode?" — answerable, from the ledger.
- "How much did caveman save?" — not answerable. Say unknown.

## Relationship to upstream

The upstream project reached the same conclusion and removed its earlier fixed-ratio
savings estimates. This port keeps that policy and extends it to per-call
attribution: the number of calls in each mode is observed, the tokens each call
spent are observed, and no counterfactual is invented.
