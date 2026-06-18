# Setup

This page is the practical install and operations guide. The README is the fast overview.

## Requirements

- Python 3
- Node.js 22 or newer with npm 10 or newer
- Codex Desktop or Codex CLI session logs under `${CODEX_HOME:-~/.codex}/sessions`

Codex Tomogatchi is a public alpha. Windows users can install with [Codex-Tomogatchi-Windows-Setup.exe](https://github.com/M0hamedd/codex-tomogatchi/releases/latest/download/Codex-Tomogatchi-Windows-Setup.exe), or use the [latest GitHub release](https://github.com/M0hamedd/codex-tomogatchi/releases/latest) for all release assets. npm publishing is intentionally disabled. Windows builds are unsigned and may trigger OS trust prompts.

## Quick Start

Windows:

```powershell
git clone https://github.com/M0hamedd/codex-tomogatchi.git
cd codex-tomogatchi
npm ci
python -m pip install -r requirements-dev.txt
.\scripts\setup.ps1
```

macOS/Linux:

```bash
git clone https://github.com/M0hamedd/codex-tomogatchi.git
cd codex-tomogatchi
npm ci
python3 -m pip install -r requirements-dev.txt
./scripts/setup.sh
```

The setup script installs npm dependencies when needed, initializes settings, installs the current pet stage, checkpoints current session logs, tries to register the local plugin marketplace, starts the overlay, runs `doctor`, and prints one next action.

The npm commands automatically look for Python 3 in this order: `PYTHON`, `python`, `python3`, then Windows `py -3`.
Most command examples use PowerShell paths; on macOS/Linux, use `python3` and `/` paths.

Use Windows autostart:

```powershell
.\scripts\setup.ps1 -InstallAutostart
```

Skip marketplace registration during development:

```powershell
.\scripts\setup.ps1 -SkipMarketplace
```

## Manual Start

```powershell
npm install
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings --init
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py reset --confirm --from-now
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py install
npm start
```

Use `python3` instead of `py -3` on macOS/Linux.

## Overlay And Codex Pet Sync

The Electron overlay is the real live surface. It updates immediately for XP, care calls, reactions, evolution, death/rebirth, compact mode, and full device mode.

If first-run setup is incomplete, the overlay shows a setup panel with the detected issue and safe actions such as Install pet, Sync, and Doctor. It does not reset local pet state from the panel.

Native Codex custom pet sync is optional. Codex may not refresh the selected custom pet immediately after Tomogatchi installs a new stage into `$CODEX_HOME/pets`; restart or refresh Codex if you rely on that view.

## Health Checks

```powershell
npm run doctor
```

`doctor` checks state, settings, pet install paths, Codex avatar config, Electron dependencies, logs, and backups. Warnings are normal on a fresh install before the pet has been installed or backed up.

## Backups

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py backup create
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py backup list
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py backup restore C:\path\backup.zip --confirm
```

Backups include Tomogatchi state and settings only. They do not include raw Codex session logs.

## Settings

Show settings:

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings
```

Common changes:

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings xp.pace slow
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings care.callStrictness relaxed
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings lifecycle.deathEnabled false
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings overlay.startMode full
```

Settings are stored at:

```text
${CODEX_HOME:-~/.codex}/codex-tomogatchi/settings.json
```

## Custom Pet Packs

Pet packs are asset-only folders or zip files. They cannot run scripts.

Useful commands:

```powershell
npm run care -- feed
npm run care -- rest
npm run care -- play
npm run care -- comfort
npm run status
npm run doctor
```

Direct pack commands:

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets list
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets forms
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets import C:\path\my-pet-line.zip --select
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets validate C:\path\my-pet-line.zip
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets export my-pet-line --output C:\path\my-pet-line.zip
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets select default
```

Choose a baby starter in a branching pack:

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets hatch agumon
```

Hatching resets to baby and checkpoints current session logs by default. Add `--include-history` only when replaying old Codex logs is intentional.

## Bundled Example Packs

Digimon World 1-style example:

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets import examples\pet-packs\digimon-world-1-agumon --replace --select
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets forms
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets hatch agumon
```

This pack uses source-backed evolution requirement data and generated concept sprites. It is not affiliated with or endorsed by the owners of Digimon or Digimon World. Keep `examples/pet-packs/digimon-world-1-agumon/SOURCE.md` with the pack when sharing it.

Tuxemon example:

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets import examples\pet-packs\tuxemon-open-61 --replace --select
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets forms
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets hatch waysprite
```

`Tuxemon Open 61` uses GPL-3.0-or-later Tuxemon YAML source data for evolution relationships and monster metadata. Its sprites are generated concept atlases, not copied Tuxemon art.

## Windows Autostart

Install:

```powershell
.\scripts\install-autostart.ps1
```

Install and start immediately:

```powershell
.\scripts\install-autostart.ps1 -RunNow
```

Remove:

```powershell
.\scripts\uninstall-autostart.ps1
```

The scheduled task is named `CodexTomogatchiOverlay`. It starts the overlay minimized to tray and uses the repo path it was installed from.

## Packaging

Use `npm ci` for release checks from a clean checkout. The setup scripts use `npm install` for everyday local installs.

Windows release check:

```powershell
npm ci
python -m pip install -r requirements-dev.txt
npm test
npm run package
npm run dist:win
```

macOS/Linux local check:

```bash
npm ci
python3 -m pip install -r requirements-dev.txt
npm test
npm run package
```

Create an unpacked app:

```powershell
npm run package
```

Create distributables:

```powershell
npm run dist
```

Create Windows distributables:

```powershell
npm run dist:win
```

GitHub release builds install `requirements-dev.txt`, run `npm test`, build Windows artifacts with `npm run dist:win -- --publish never`, then upload the installer, zip, update metadata, and stable installer alias. Current Windows artifacts are unsigned alpha builds.

## Release Screenshots

Refresh static previews:

```powershell
python scripts/render_overlay_preview.py
```

Use `python3 scripts/render_overlay_preview.py` on systems where the Python executable is named `python3`.

Preview files:

- `docs/screenshots/compact-preview.png`
- `docs/screenshots/overlay-preview.png`
- `docs/screenshots/care-call-preview.png`
- `docs/screenshots/evolution-preview.png`

Use real overlay GIFs in release notes when animation timing matters. Do not include prompt text, command text, tool output, raw logs, project files, or private workspace details.
