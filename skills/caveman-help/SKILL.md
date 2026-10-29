---
name: caveman-help
description: >
  Quick-reference card for the three caveman skills and their commands.
  Trigger: /caveman-help or "caveman help".
---
<!-- Hermes port (caveman-hermes): modified from upstream v4.0.1 — see NOTICE. -->

# Caveman Help

Display this reference card when invoked. One-shot — do NOT change mode, write flag files, or persist anything. Output in caveman style.

## Modes

| Mode | Trigger | What change |
|------|---------|-------------|
| **caveman** | `/caveman` | The voice. Answer first, no fluff, every fact kept. Default. |
| **ultracave** | `/ultracave` (alias `/caveman ultra`) | Grammar stripped. Fragments, one word when enough, each fact once. |
| **megacave** | `/megacave` (alias `/caveman wenyan`) | Classical Chinese 文言文. Far fewer characters, technical terms verbatim. |

Mode stick until changed or session end.
`/caveman status` reports current mode without changing it. Hermes reads stored state natively — `~/.hermes/bin/caveman status` (the `pre_llm_call` hook injects `Caveman mode: <mode>` every turn); other hosts answer from the conversation and mark it `(not tracked by this host)`.

## Skills

| Skill | Trigger | What it do |
|-------|---------|-----------|
| **caveman-commit** | `/caveman-commit` | Terse commit messages. Conventional Commits. ≤50 char subject. |
| **caveman-review** | `/caveman-review` | One-line PR comments: `L42: bug: user null. Add guard.` |
| **caveman-compress** | `/caveman-compress <file>` | Compress .md files to caveman prose. 33.2% fewer tokens on the repo's five test files. |
| **caveman-help** | `/caveman-help` | This card. |

## Deactivate

Say "stop caveman" or "normal mode". Resume anytime with `/caveman`.

## Language

Keep user's language by default — reply in the language user writes, never switch regardless of example text or multilingual context elsewhere. Compress the style, not the language. Technical terms, code, commands, commit types, and exact error strings stay verbatim unless user ask for translation.

## Hermes Commands

```bash
~/.hermes/bin/caveman set caveman        # this session
~/.hermes/bin/caveman set megacave
~/.hermes/bin/caveman off                # also: "stop caveman", "normal mode"
~/.hermes/bin/caveman set --global ultracave   # every new session
~/.hermes/bin/caveman status             # mode only
~/.hermes/bin/caveman stats              # recorded usage, per-mode
```

State lives in `$HERMES_HOME/state/caveman.json`; per-call usage in
`$HERMES_HOME/state/caveman-ledger.jsonl`.

## Configure Default Mode

Resolution order: session entry > `CAVEMAN_DEFAULT_MODE` > `--global` default
(`state/caveman.json`) > upstream `~/.config/caveman/config.json` `defaultMode` > `off`.

```bash
export CAVEMAN_DEFAULT_MODE=ultracave        # scoped to a shell / one host
~/.hermes/bin/caveman set --global ultracave # persistent default
~/.hermes/bin/caveman set --global off       # opt-in only: no automatic mode
```

`manual` and `off` are startup policies, not modes. Legacy values `lite`, `full`, `ultra`,
`wenyan*`, `normal`, `stop` still resolve.

## More

Full docs: https://github.com/JuliusBrussee/caveman
