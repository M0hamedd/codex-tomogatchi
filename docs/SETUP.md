# Setup

Codex Tomogatchi can run as a repo overlay during development or as a packaged Electron app.

## Requirements

- Python 3
- Node.js LTS and npm
- Codex Desktop or Codex CLI session logs under `${CODEX_HOME:-~/.codex}/sessions`

## Quick Start

Windows:

```powershell
.\scripts\setup.ps1
```

macOS/Linux:

```bash
./scripts/setup.sh
```

The setup script installs npm dependencies, initializes settings, installs the current pet stage into `$CODEX_HOME/pets`, resets from the current session-log position, tries to register the local plugin marketplace, and launches the overlay.

Autostart is optional and off by default. To opt in during setup on Windows:

```powershell
.\scripts\setup.ps1 -InstallAutostart
```

## Live Surface And Limitations

The Electron overlay is the main live surface. It updates immediately for XP, care calls, reactions, evolution, death/rebirth, and compact or full device mode.

Native Codex custom pet sync is optional compatibility. Codex may not refresh the selected custom pet live after this project installs a new stage into `$CODEX_HOME/pets`, so restart or refresh Codex if you rely on the native pet view.

Hook-free tracking depends on Codex Desktop or Codex CLI JSONL session logs under `${CODEX_HOME:-~/.codex}/sessions`. If those logs are missing or Codex changes their location or schema, run `doctor` and expect tracking to be incomplete until the parser is updated.

## Manual Commands

```powershell
npm install
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings --init
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py reset --confirm --from-now
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py install
npm start
```

Use `python3` instead of `py -3` on macOS/Linux.

## Diagnostics And Backups

Check common setup issues:

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py doctor
```

Create and restore a state/settings backup:

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py backup create
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py backup list
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py backup restore C:\path\backup.zip --confirm
```

Backups do not include raw Codex session logs.

## Settings

Show settings:

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings
```

Change XP pace:

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings xp.pace slow
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings xp.pace normal
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings xp.pace fast
```

Change care-call strictness:

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings care.callStrictness relaxed
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings care.callStrictness normal
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings care.callStrictness strict
```

Disable death:

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings lifecycle.deathEnabled false
```

Start overlay in full mode:

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py settings overlay.startMode full
```

## Custom Pet Packs

List packs:

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets list
```

List forms in the active pack:

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets forms
```

Import and select a pack:

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets import C:\path\my-pet-line.zip --select
```

Validate or export a pack for sharing:

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets validate C:\path\my-pet-line.zip
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets export my-pet-line --output C:\path\my-pet-line.zip
```

Choose a baby starter from a branching pack:

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets hatch agumon
```

Return to bundled pets:

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets select default
```

Custom packs are asset-only folders or zip files with `pack.json` and `baby`, `teen`, and `adult` stage folders. Each stage must include `pet.json` and `spritesheet.webp`.

Use the bundled branching Digimon World 1 Agumon example:

```powershell
py -3 scripts/generate_dw1_agumon_pack.py
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets import examples\pet-packs\digimon-world-1-agumon --replace --select
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets forms
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets hatch agumon
```

Branching packs can define multiple `forms` per stage. The DW1 example stores the original-style stats, care mistake, weight, and bonus groups in `pack.json`, then uses the local Codex Tomogatchi raising stats to choose the matching form.
`pets hatch <baby-form-id>` resets to baby from the current session-log position by default, so old Codex logs do not immediately evolve a new starter.

Use the larger open-source Tuxemon example:

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets import examples\pet-packs\tuxemon-open-61 --replace --select
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets forms
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py pets hatch waysprite
```

`Tuxemon Open 61` is a DW1-sized pack with 61 forms and 24 real three-stage paths from Tuxemon YAML evolution data. Tuxemon source data is GPL-3.0-or-later. The included sprites are generated concept atlases, not copied Tuxemon art.

Licensing note: repository code is MIT, but example packs can include separate source-data or asset terms. Keep source data and asset provenance documented when adding or sharing packs.

## Optional Windows Autostart

Install a no-admin Scheduled Task that starts Codex Tomogatchi when you log in:

```powershell
.\scripts\install-autostart.ps1
```

Start it immediately after installing:

```powershell
.\scripts\install-autostart.ps1 -RunNow
```

Remove the task:

```powershell
.\scripts\uninstall-autostart.ps1
```

The task is named `CodexTomogatchiOverlay` by default and runs:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File .\scripts\start-overlay.ps1 -StartMinimized
```

It starts the overlay minimized to tray and uses the repo it was installed from.

## Packaging

Create an unpacked app directory:

```powershell
npm run package
```

Create distributables:

```powershell
npm run dist
```

The packaging scripts use the locked `electron-builder` dev dependency. GitHub release builds run `npm run dist:win` and upload the Windows installer/zip artifacts.

## Release Screenshots And GIFs

Use `python scripts/render_overlay_preview.py` to refresh the static preview set in `docs/screenshots/`.

For GitHub release notes or UI-facing PRs, capture the real overlay and add concise references for:

- Compact mode: `docs/screenshots/compact-preview.png`
- Full device mode: `docs/screenshots/overlay-preview.png`
- Care calls: `docs/screenshots/care-call-preview.png` or a real overlay GIF
- Evolution: `docs/screenshots/evolution-preview.png` or a real overlay GIF

Do not include prompt text, command text, tool output, raw logs, screenshots of project files, or private workspace details in release media.
