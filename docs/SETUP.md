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
