# Codex Tomogatchi

A local virtual pet for Codex that grows from privacy-safe activity counters.

![Codex Tomogatchi overlay preview](docs/screenshots/overlay-preview.png)

Codex Tomogatchi watches local Codex session activity, turns aggregate counters into XP, care calls, stats, and evolution paths, and renders a live Electron overlay. It is designed as a playful desktop companion, not an analytics collector.

## What This Is

Codex Tomogatchi is primarily a live desktop overlay for Codex, not a replacement for Codex's built-in custom pets. The overlay is the main experience because it can update immediately while you work: XP changes, care calls, reactions, evolution, death/rebirth, and the full Tamagotchi-style screen all happen without restarting Codex or manually refreshing a pet.

Codex custom pet support is treated as an optional compatibility layer. The project can still install the current evolution stage into `${CODEX_HOME:-~/.codex}/pets`, but Codex itself may not refresh that selected pet live. For that reason, the Electron overlay is the recommended way to use Codex Tomogatchi, and native Codex pet sync is a bonus for people who also want the selected custom pet asset to match their current stage.

In short:

- Use the overlay for the actual game loop.
- Use the Codex plugin/skill for local commands, setup, state, and optional pet asset sync.
- Use native Codex custom pets as a visual extra, not the core gameplay surface.

## Current Alpha

- Original default pet line: Sparkbit -> Byteclaw -> Coremaw.
- Hook-free tracking through Codex session-log sync/watch.
- Electron overlay with tray menu, compact mode, full device mode, resizing, and live reactions.
- Tamagotchi-style care calls for `feed`, `rest`, `play`, and `comfort`.
- Classic monster-raising evolution requirements based on care mistakes, missed calls, focus, and care balance.
- Local-only JSON state and settings.

## Quick Start

Windows:

```powershell
.\scripts\setup.ps1
```

macOS/Linux:

```bash
./scripts/setup.sh
```

Manual start:

```powershell
npm install
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings --init
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py reset --confirm --from-now
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py install
npm start
```

Use `python3` instead of `py -3` on macOS/Linux.

## Commands

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py status
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py care feed
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py care rest
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py care play
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py care comfort
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py sync
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py watch
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py profile
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets list
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets forms
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets import C:\path\my-pet-line.zip --select
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets hatch agumon
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets select default
```

## Settings

Settings are stored at:

```text
${CODEX_HOME:-~/.codex}/codex-tomogatchi/settings.json
```

Examples:

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings xp.pace slow
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings care.callStrictness relaxed
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings lifecycle.deathEnabled false
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings overlay.startMode full
```

## Custom Pet Packs

Custom pets are asset-only packs. They can be shared as folders or `.zip` files and are imported into:

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

Each stage folder must include a `pet.json` that references `spritesheet.webp`, plus the `spritesheet.webp` file. Pet packs cannot run scripts or write outside the local pet-pack folder. For Codex custom pet compatibility, spritesheets should follow the Codex pet atlas shape: `1536x1872`, 8 columns, 9 rows, transparent background.

### Branching Packs

Packs can also define `forms` instead of one asset per stage. A form has its own asset path, optional `evolvesFrom`, and requirements. The current branching evaluator supports the normal Tomogatchi requirement keys plus a `dw1` requirement object with Digimon World 1-style groups:

- `stats`
- `careMistakes`
- `weight`
- `bonus`

DW1-style rules require 3 of those 4 groups by default, matching the PS1 requirement model documented by SydMontague's Digimon World evolution guide.

Example form:

```json
{
  "id": "greymon",
  "name": "Greymon",
  "assetPath": "forms/teen/greymon",
  "evolvesFrom": ["agumon"],
  "requirements": {
    "reason": "DW1 Greymon groups matched",
    "dw1": {
      "groupsRequired": 3,
      "stats": {
        "hp": 2000,
        "mp": 1500,
        "offense": 100,
        "defense": 100,
        "speed": 100,
        "brains": 100
      },
      "careMistakes": { "max": 1 },
      "weight": { "min": 25, "max": 35 },
      "bonus": [
        { "disciplineMin": 90 },
        { "techniquesMin": 35 }
      ]
    }
  }
}
```

The repo includes an example branching pack at:

```text
examples/pet-packs/digimon-world-1-agumon
```

It starts at Agumon, branches to Greymon, Meramon, Birdramon, Centarumon, Monochromon, Tyrannomon, or Numemon, then branches to matching DW1 ultimate counterparts such as MetalGreymon, SkullGreymon, Andromon, Phoenixmon, Megadramon, MetalMamemon, Giromon, or Monzaemon. Requirement data is stored in the pack as source-backed DW1 groups; local sprites are concept atlases, not ripped game assets.

Commands:

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets list
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets forms
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets import C:\path\my-pet-line.zip
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets import C:\path\my-pet-line.zip --select
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets import C:\path\my-pet-line.zip --replace --select
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets select my-pet-line
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets hatch agumon
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets select default
```

Use the bundled DW1 example:

```powershell
py -3 scripts/generate_dw1_agumon_pack.py
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets import examples\pet-packs\digimon-world-1-agumon --replace --select
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets forms
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets hatch agumon
```

For branching packs, `pets forms` lists available forms and `pets hatch <baby-form-id>` chooses the starter baby form. Hatching resets to baby and checkpoints existing Codex session logs by default, so older history does not instantly replay and evolve the pet. Use `--include-history` only when you intentionally want old logs to count after hatching.

## Optional Autostart

On Windows, install a no-admin Scheduled Task that starts the overlay at login:

```powershell
.\scripts\install-autostart.ps1
```

Remove it:

```powershell
.\scripts\uninstall-autostart.ps1
```

Autostart is off by default. It launches the overlay minimized to tray, so it is ready when you open Codex.

## Packaging

The overlay can be packaged with Electron Builder on demand:

```powershell
npm run package
npm run dist
```

The packager is invoked with `npx --yes electron-builder`, so normal development installs stay light.

## Privacy

Codex Tomogatchi stores aggregate counters, timestamps, XP, stats, lifecycle state, evolution metadata, DW1-style derived raising stats, reactions, settings, and session-log checkpoints. It does not store prompt text, command text, tool output, screenshots, raw hook payloads, raw session-log records, or project file contents.

See [PRIVACY.md](PRIVACY.md).

## Development

```powershell
npm test
py -3 scripts/validate_assets.py
py -3 scripts/generate_original_assets.py
py -3 scripts/render_overlay_preview.py
```

See [docs/SETUP.md](docs/SETUP.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).
