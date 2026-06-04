# Codex Tomogatchi Plugin

Repo-scoped Codex plugin for the Codex Tomogatchi pet loop.

## Default Pet Line

Bundled public-safe default assets are original generated pixel pets:

- Baby: Sparkbit
- Teen: Byteclaw
- Adult: Coremaw

Regenerate them with:

```powershell
py -3 scripts/generate_original_assets.py
```

## Install

From the repository root:

```powershell
codex plugin marketplace add .
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings --init
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py reset --confirm --from-now
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py install
npm start
```

Use `python3` instead of `py -3` on macOS/Linux.

## Commands

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
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py care-call
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py reset --confirm --from-now
```

## Rules

- Baby starts at 0 XP.
- Teen evolves at 90 XP.
- Adult evolves at 260 XP.
- Evolution never skips stages.
- User prompts/completed turns add XP based on the configured XP pace.
- Tool calls update counters/stats/focus but do not spam XP.
- Care calls appear when fullness, energy, mood, or stress crosses a need threshold.
- Matching care answers the call and gives extra care weight.
- Missed care calls count toward care mistakes.
- Without interaction for 72 hours, the pet dies unless death is disabled.
- After 12 dead hours, it automatically returns to baby with fresh stats and 0 XP.

## Evolution Paths

Current logical paths are `partner`, `builder`, `explorer`, `debugger`, `reviewer`, `wild`, and `balanced`.

- `wild`: high mistakes, missed calls, stress mistakes, or overwork mistakes.
- focus paths: dominant generation focus without too many mistakes.
- `partner`: broad care with low mistakes.
- `balanced`: fallback.

## Settings

Settings live at:

```text
${CODEX_HOME:-~/.codex}/codex-tomogatchi/settings.json
```

Supported settings:

- `xp.pace`: `slow`, `normal`, or `fast`
- `care.callStrictness`: `relaxed`, `normal`, or `strict`
- `lifecycle.deathEnabled`: `true` or `false`
- `overlay.alwaysOnTop`: `true` or `false`
- `overlay.startMode`: `compact` or `full`
- `overlay.startMinimized`: `true` or `false`

## Privacy

The tracker stores aggregate counters, lifecycle timestamps, evolution profile metadata, settings, and reaction metadata only. It must not store prompt text, command text, tool output, screenshots, raw hook payloads, or raw session-log records.
