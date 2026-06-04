#!/usr/bin/env python3
"""Validate bundled Codex pet stage assets."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "plugins" / "codex-tomogatchi" / "assets" / "stages"
STAGES = ("baby", "teen", "adult")
EXPECTED_SIZE = (1536, 1872)


def validate_stage(stage: str) -> None:
    stage_dir = ASSET_ROOT / stage
    manifest_path = stage_dir / "pet.json"
    sprite_path = stage_dir / "spritesheet.webp"
    if not manifest_path.exists():
        raise SystemExit(f"Missing manifest: {manifest_path}")
    if not sprite_path.exists():
        raise SystemExit(f"Missing spritesheet: {sprite_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("spritesheetPath") != "spritesheet.webp":
        raise SystemExit(f"{manifest_path} must reference spritesheet.webp")
    for key in ("id", "displayName", "description"):
        if not isinstance(manifest.get(key), str) or not manifest[key].strip():
            raise SystemExit(f"{manifest_path} is missing {key}")

    with Image.open(sprite_path) as image:
        if image.size != EXPECTED_SIZE:
            raise SystemExit(f"{sprite_path} has size {image.size}, expected {EXPECTED_SIZE}")
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        alpha = image.getchannel("A")
        if alpha.getbbox() is None:
            raise SystemExit(f"{sprite_path} has no visible pixels")
        for point in ((0, 0), (EXPECTED_SIZE[0] - 1, 0), (0, EXPECTED_SIZE[1] - 1), (EXPECTED_SIZE[0] - 1, EXPECTED_SIZE[1] - 1)):
            if alpha.getpixel(point) != 0:
                raise SystemExit(f"{sprite_path} corner {point} is not transparent")


def main() -> None:
    for stage in STAGES:
        validate_stage(stage)
        print(f"Validated {stage}")


if __name__ == "__main__":
    main()
