---
name: codex-tomogatchi
description: Use when the user wants to inspect, care for, reset, install, configure, or evolve the local Codex Tomogatchi pet that grows from privacy-safe Codex activity counters.
---

# Codex Tomogatchi

Use the bundled CLI for every operation. Do not manually edit the state file unless the user explicitly asks for recovery.

Run commands from the repository root when working in a clone:

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py status
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py status --json
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py care feed
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py care rest
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py care play
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py care comfort
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py sync
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py watch
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py install
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py evolve --check
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py profile
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py profile --json
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py care-call
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py care-call --force feed
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py care-call --json
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings --json
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings xp.pace slow
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py reset --confirm
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py reset --confirm --from-now
npm start
```

Use `python3` instead of `py -3` on macOS/Linux.

## Behavior

- `status` reports the current stage, XP, stats, activity counters, branch signals, care call, and installed pet path.
- `care feed|rest|play|comfort` adjusts fullness, energy, mood, and stress.
- `sync` does a one-shot privacy-safe ingest from Codex session JSONL logs.
- `watch` continuously syncs session logs in the foreground for hook-free tracking.
- `install` copies all stage packages into `${CODEX_HOME:-~/.codex}/pets/codex-tomogatchi-{stage}` and updates `[desktop].selected-avatar-id`.
- `profile` reports the current generation's logical evolution path, care mistakes, care points, focus points, training points, care calls, and lineage.
- `care-call` checks the current active care call. `care-call --force <kind>` creates a test call.
- `settings` shows or updates settings under `${CODEX_HOME:-~/.codex}/codex-tomogatchi/settings.json`.
- `npm start` launches the Electron overlay with tray, compact/full modes, resizing, and live reactions.

## Default Pets

Bundled default assets are original generated pixel pets:

- Sparkbit: baby
- Byteclaw: teen
- Coremaw: adult

## XP Rules

- User prompts/completed turns add XP according to `xp.pace`.
- Normal tool calls add 0 XP.
- A successful tool gives one small work bonus per turn.
- Failed tools raise stress but add 0 XP.
- `care play` adds tiny capped care XP.

## Lifecycle Rules

- `SessionStart`, `UserPromptSubmit`, and care actions count as interactions.
- Without interaction for 72 hours, the pet dies if `lifecycle.deathEnabled` is true.
- While dead, counters continue to update but XP, care stat changes, and evolution are paused.
- After 12 dead hours, the pet automatically returns to baby with 0 XP and fresh stats.

## Evolution Rules

- Evolution is generation-based and table-driven.
- Logical paths are `partner`, `builder`, `explorer`, `debugger`, `reviewer`, `wild`, and `balanced`.
- Care actions add care points for `feed`, `rest`, `play`, and `comfort`.
- Care calls appear when fullness, energy, mood, or stress crosses the configured need threshold.
- Matching care answers an active call and gives extra care weight.
- Missing a care call records aggregate missed-call counters and adds the matching mistake type.
- `wild` comes from high mistakes or missed calls.
- Focus paths come from dominant work focus without too many mistakes.
- `partner` comes from broad care with low mistakes.
- `balanced` is the fallback path.

## Privacy

The hook and session-log paths store aggregate counters, lifecycle timestamps, settings, evolution profile metadata, and reaction metadata only. They must not store prompt text, command text, tool output, screenshots, raw hook payloads, or raw session-log records. If a user asks what is stored, run `status --json` and summarize the JSON keys.
