# Codex Tomogatchi

A local virtual pet for Codex that grows from privacy-safe activity counters.

![Codex Tomogatchi overlay preview](docs/screenshots/overlay-preview.png)

Codex Tomogatchi watches local Codex session activity, turns aggregate counters into XP, care calls, stats, and evolution paths, and renders a live Electron overlay. It is designed as a playful desktop companion, not an analytics collector.

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

Codex Tomogatchi stores aggregate counters, timestamps, XP, stats, lifecycle state, evolution metadata, reactions, settings, and session-log checkpoints. It does not store prompt text, command text, tool output, screenshots, raw hook payloads, raw session-log records, or project file contents.

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
