#!/usr/bin/env python3
"""Run the release-quality local validation suite."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> None:
    print(f"+ {' '.join(command)}")
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    run(["node", "--check", "overlay/main.js"])
    run(["node", "--check", "overlay/preload.js"])
    run(["node", "--check", "overlay/renderer.js"])
    run([sys.executable, "scripts/validate_assets.py"])
    run([sys.executable, "plugins/codex-tomogatchi/scripts/tomogatchi.py", "pets", "validate", "examples/pet-packs/digimon-world-1-agumon"])
    run([sys.executable, "plugins/codex-tomogatchi/scripts/tomogatchi.py", "pets", "validate", "examples/pet-packs/tuxemon-open-61"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
