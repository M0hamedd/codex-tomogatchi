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

The packaging scripts use `npx --yes electron-builder`, so the packager is downloaded only when needed.
