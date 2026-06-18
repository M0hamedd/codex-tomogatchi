# Contributing

Thanks for helping with Codex Tomogatchi. Keep changes local-first, privacy-safe, and easy to verify.

## Setup

Install Python 3, Node.js 22 or newer, and npm 10 or newer.

Install Python test dependencies:

```powershell
python -m pip install -r requirements-dev.txt
```

Use `python3 -m pip install -r requirements-dev.txt` on systems where the Python executable is named `python3`.

Windows:

```powershell
.\scripts\setup.ps1 -SkipMarketplace
```

macOS/Linux:

```bash
./scripts/setup.sh --skip-marketplace
```

## Checks

Run the same local gate used by CI:

```powershell
npm test
```

The npm test command automatically uses `PYTHON`, `python`, `python3`, or Windows `py -3`, whichever available command provides Python 3. It runs Python unit tests, Electron JavaScript syntax checks, pet asset validation, and pet-pack validation.

## Privacy Rules

Do not store:

- Prompt text
- Command text
- Tool output
- Raw hook payloads
- Raw session-log records
- Project file contents

Add or update tests when touching session-log ingestion, reactions, settings, lifecycle, care calls, evolution rules, pet packs, or privacy-sensitive state.

## Assets And Example Packs

Bundled default assets must be original or explicitly licensed for redistribution. Regenerate the current default sprites with:

```powershell
py -3 scripts/generate_original_assets.py
```

Do not commit proprietary or fandom-inspired art as bundled defaults.

Example packs may have separate source-data, asset, or trademark terms. When adding or changing one, update:

- `THIRD_PARTY_NOTICES.md`
- The pack's `SOURCE.md`
- The pack's `pack.json` source block
- README/setup docs when users need to know about it
- Tests that protect release notices

The Digimon World 1 Agumon example must remain clearly marked as unaffiliated generated concept art plus source-backed requirement data, not copied game assets. `Tuxemon Open 61` must remain clearly marked as using GPL-3.0-or-later Tuxemon source data, with generated concept sprites.

## Release Media

Refresh static previews after UI-facing changes:

```powershell
python scripts/render_overlay_preview.py
```

Use `python3 scripts/render_overlay_preview.py` on systems where the Python executable is named `python3`.

Static previews live in `docs/screenshots/`. Use real overlay GIFs for release notes when animation timing matters.

Never include prompt text, command text, tool output, raw logs, project file contents, or private workspace details in screenshots or GIFs.
