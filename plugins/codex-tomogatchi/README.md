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
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py doctor
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
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets list
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets forms
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets import C:\path\my-pet-line.zip --select
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets hatch agumon
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py backup create
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets select default
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
- `pets.activePack`: `default` or an installed custom pet pack id
- `pets.starterForm`: empty for the pack default, or a baby form id from `pets forms`

## Custom Pet Packs

Custom pet packs are asset-only folders or zip files. They are imported into:

```text
${CODEX_HOME:-~/.codex}/codex-tomogatchi/pet-packs/<pack-id>/
```

Pack layout:

```text
my-pet-line.zip
  pack.json
  stages/
    baby/
      pet.json
      spritesheet.webp
    teen/
      pet.json
      spritesheet.webp
    adult/
      pet.json
      spritesheet.webp
```

`pack.json`:

```json
{
  "schemaVersion": 1,
  "id": "my-pet-line",
  "name": "My Pet Line",
  "author": "Someone",
  "description": "A custom three-stage evolution line.",
  "stages": {
    "baby": "stages/baby",
    "teen": "stages/teen",
    "adult": "stages/adult"
  }
}
```

Commands:

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets list
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets forms
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets import C:\path\my-pet-line.zip --select
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets import C:\path\my-pet-line.zip --replace --select
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets validate C:\path\my-pet-line.zip
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets export my-pet-line --output C:\path\my-pet-line.zip
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets select my-pet-line
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets hatch agumon
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets select default
```

Branching packs can use `forms` instead of `stages`. Each form has an `assetPath`, optional `evolvesFrom`, and `requirements`. The requirement evaluator supports Digimon World 1-style `dw1` groups: stats, care mistakes, weight, and bonus. DW1-style forms require 3 of the 4 groups by default.

The repo includes an example pack:

```powershell
py -3 scripts/generate_dw1_agumon_pack.py
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets import examples\pet-packs\digimon-world-1-agumon --replace --select
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets forms
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets hatch agumon
```

That pack starts at Agumon, branches to Greymon, Meramon, Birdramon, Centarumon, Monochromon, Tyrannomon, or Numemon, then branches to matching DW1 ultimate counterparts. The requirement data is source-backed; the local sprites are concept atlases, not ripped game assets.

`pets hatch <baby-form-id>` resets to baby and checkpoints existing Codex session logs by default. That keeps old local history from instantly evolving a newly chosen starter. Add `--include-history` only when replaying older logs is intentional.

Packs cannot run scripts. Each stage must include `pet.json` and `spritesheet.webp`; for Codex custom pet sync, use the Codex atlas shape: `1536x1872`, 8 columns, 9 rows, transparent background.

## Diagnostics And Backups

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py doctor
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py backup create
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py backup list
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py backup restore C:\path\backup.zip --confirm
```

`doctor` checks common local setup issues. Backups store Tomogatchi state and settings only; they do not include raw Codex session logs.

## Privacy

The tracker stores aggregate counters, lifecycle timestamps, evolution profile metadata, DW1-style derived raising stats, settings, and reaction metadata only. It must not store prompt text, command text, tool output, screenshots, raw hook payloads, or raw session-log records.
