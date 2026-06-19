#!/usr/bin/env python3
"""Validate shared default settings across Python and Electron loaders."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "default-settings.json"
TOMOGATCHI_PATH = ROOT / "plugins" / "codex-tomogatchi" / "scripts" / "tomogatchi.py"


def load_tomogatchi_defaults() -> dict:
    spec = importlib.util.spec_from_file_location("tomogatchi", TOMOGATCHI_PATH)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Could not load {TOMOGATCHI_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {
        "DEFAULT_SETTINGS": module.DEFAULT_SETTINGS,
        "FALLBACK_DEFAULT_SETTINGS": module.FALLBACK_DEFAULT_SETTINGS,
    }


def load_overlay_defaults() -> dict:
    script = (
        "const { FALLBACK_DEFAULT_SETTINGS, loadDefaultSettings } = require('./overlay/default_settings');"
        "process.stdout.write(JSON.stringify({"
        "DEFAULT_SETTINGS: loadDefaultSettings(process.cwd()),"
        "FALLBACK_DEFAULT_SETTINGS"
        "}));"
    )
    result = subprocess.run(["node", "-e", script], cwd=ROOT, check=True, text=True, capture_output=True)
    return json.loads(result.stdout)


def main() -> int:
    config_defaults = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    tomogatchi_defaults = load_tomogatchi_defaults()
    overlay_defaults = load_overlay_defaults()
    runtime_defaults = {
        "tomogatchi.py DEFAULT_SETTINGS": tomogatchi_defaults["DEFAULT_SETTINGS"],
        "tomogatchi.py FALLBACK_DEFAULT_SETTINGS": tomogatchi_defaults["FALLBACK_DEFAULT_SETTINGS"],
        "overlay/default_settings.js DEFAULT_SETTINGS": overlay_defaults["DEFAULT_SETTINGS"],
        "overlay/default_settings.js FALLBACK_DEFAULT_SETTINGS": overlay_defaults["FALLBACK_DEFAULT_SETTINGS"],
    }
    for label, defaults in runtime_defaults.items():
        if defaults != config_defaults:
            print(f"{label} defaults do not match {CONFIG_PATH}", file=sys.stderr)
            print(json.dumps(defaults, indent=2, sort_keys=True), file=sys.stderr)
            return 1
    print("Validated shared default settings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
