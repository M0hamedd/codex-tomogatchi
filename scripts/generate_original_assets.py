#!/usr/bin/env python3
"""Generate the original Codex Tomogatchi default pet assets.

The generated spritesheets are intentionally simple, original pixel creatures.
They satisfy the Codex pet atlas contract: 1536x1872, 8 columns, 9 rows,
transparent background, 192x208 frames.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "plugins" / "codex-tomogatchi" / "assets" / "stages"
FRAME_W = 192
FRAME_H = 208
COLUMNS = 8
ROWS = 9
LOW_W = 48
LOW_H = 52
SCALE = 4


STAGES = {
    "baby": {
        "id": "sparkbit",
        "displayName": "Sparkbit",
        "description": "A tiny original ember-coded desktop pet.",
        "body": "#ff7b50",
        "belly": "#ffd07a",
        "accent": "#52d6c4",
        "horn": "#ffe1a6",
        "size": 0,
    },
    "teen": {
        "id": "byteclaw",
        "displayName": "Byteclaw",
        "description": "An original quick-footed code companion with bright claws.",
        "body": "#f05f46",
        "belly": "#ffe08c",
        "accent": "#46d7a8",
        "horn": "#f8f0c8",
        "size": 1,
    },
    "adult": {
        "id": "coremaw",
        "displayName": "Coremaw",
        "description": "An original mature compiler-beast with a warm core.",
        "body": "#d84d42",
        "belly": "#ffc85d",
        "accent": "#37c6d0",
        "horn": "#fff0c2",
        "size": 2,
    },
}


def rect(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], fill: str) -> None:
    draw.rectangle(xy, fill=fill)


def poly(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], fill: str) -> None:
    draw.polygon(points, fill=fill)


def ellipse(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], fill: str) -> None:
    draw.ellipse(xy, fill=fill)


def draw_creature(stage: dict[str, object], row: int, column: int) -> Image.Image:
    frame = Image.new("RGBA", (LOW_W, LOW_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)

    size = int(stage["size"])
    body = str(stage["body"])
    belly = str(stage["belly"])
    accent = str(stage["accent"])
    horn = str(stage["horn"])

    bob = [0, -1, 0, 1, 0, -1, 0, 1][column % COLUMNS]
    blink = row == 1 and column in {2, 3}
    lean = -1 if column % 4 == 1 else 1 if column % 4 == 3 else 0
    y = 6 + bob
    x = 24 + lean

    shadow_alpha = 48 if row != 3 else 32
    ellipse(draw, (10, 42, 39, 48), (0, 0, 0, shadow_alpha))

    if size == 0:
        ellipse(draw, (x - 12, y + 10, x + 12, y + 34), body)
        ellipse(draw, (x - 7, y + 22, x + 7, y + 35), belly)
        poly(draw, [(x - 10, y + 11), (x - 16, y + 5), (x - 8, y + 7)], body)
        poly(draw, [(x + 10, y + 11), (x + 16, y + 5), (x + 8, y + 7)], body)
        poly(draw, [(x - 3, y + 10), (x, y + 4), (x + 3, y + 10)], horn)
        rect(draw, (x - 12, y + 31, x - 7, y + 37), body)
        rect(draw, (x + 7, y + 31, x + 12, y + 37), body)
    elif size == 1:
        ellipse(draw, (x - 11, y + 7, x + 12, y + 28), body)
        ellipse(draw, (x - 12, y + 22, x + 13, y + 43), body)
        ellipse(draw, (x - 6, y + 25, x + 7, y + 40), belly)
        poly(draw, [(x - 10, y + 9), (x - 17, y + 1), (x - 8, y + 4)], body)
        poly(draw, [(x + 10, y + 9), (x + 17, y + 1), (x + 8, y + 4)], body)
        poly(draw, [(x - 4, y + 8), (x - 1, y + 0), (x + 1, y + 8)], horn)
        poly(draw, [(x + 4, y + 8), (x + 8, y + 1), (x + 8, y + 10)], horn)
        rect(draw, (x - 18, y + 24, x - 10, y + 29), body)
        rect(draw, (x + 11, y + 24, x + 19, y + 29), body)
        rect(draw, (x - 11, y + 40, x - 5, y + 47), body)
        rect(draw, (x + 5, y + 40, x + 11, y + 47), body)
    else:
        ellipse(draw, (x - 13, y + 5, x + 14, y + 28), body)
        ellipse(draw, (x - 15, y + 22, x + 16, y + 45), body)
        ellipse(draw, (x - 8, y + 25, x + 9, y + 43), belly)
        poly(draw, [(x - 11, y + 7), (x - 20, y - 1), (x - 8, y + 2)], body)
        poly(draw, [(x + 11, y + 7), (x + 20, y - 1), (x + 8, y + 2)], body)
        poly(draw, [(x - 6, y + 7), (x - 2, y - 3), (x + 1, y + 7)], horn)
        poly(draw, [(x + 4, y + 7), (x + 10, y - 2), (x + 9, y + 10)], horn)
        poly(draw, [(x - 15, y + 24), (x - 25, y + 17), (x - 18, y + 32)], body)
        poly(draw, [(x + 15, y + 24), (x + 25, y + 17), (x + 18, y + 32)], body)
        rect(draw, (x - 12, y + 42, x - 5, y + 50), body)
        rect(draw, (x + 5, y + 42, x + 12, y + 50), body)
        poly(draw, [(x - 14, y + 27), (x - 24, y + 31), (x - 15, y + 34)], accent)
        poly(draw, [(x + 14, y + 27), (x + 24, y + 31), (x + 15, y + 34)], accent)

    if blink:
        rect(draw, (x - 7, y + 17, x - 3, y + 18), "#241818")
        rect(draw, (x + 4, y + 17, x + 8, y + 18), "#241818")
    else:
        rect(draw, (x - 7, y + 15, x - 4, y + 19), "#241818")
        rect(draw, (x + 4, y + 15, x + 7, y + 19), "#241818")
        rect(draw, (x - 6, y + 15, x - 6, y + 15), "#fff4dc")
        rect(draw, (x + 5, y + 15, x + 5, y + 15), "#fff4dc")

    if row in {4, 5}:
        rect(draw, (x - 3, y + 23, x + 4, y + 24), "#241818")
    else:
        rect(draw, (x - 2, y + 23, x + 2, y + 24), "#241818")

    if row in {6, 7, 8}:
        ellipse(draw, (x - 16, y + 35, x - 10, y + 40), accent)
        ellipse(draw, (x + 10, y + 35, x + 16, y + 40), accent)

    return frame.resize((FRAME_W, FRAME_H), Image.Resampling.NEAREST)


def generate_stage(stage_name: str, stage: dict[str, object]) -> None:
    target = ASSET_ROOT / stage_name
    target.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGBA", (FRAME_W * COLUMNS, FRAME_H * ROWS), (0, 0, 0, 0))
    for row in range(ROWS):
        for column in range(COLUMNS):
            frame = draw_creature(stage, row, column)
            sheet.alpha_composite(frame, (column * FRAME_W, row * FRAME_H))

    sheet.save(target / "spritesheet.webp", "WEBP", lossless=True, quality=100, method=6)
    sheet.save(target / "contact-sheet.png", "PNG")
    manifest = {
        "id": stage["id"],
        "displayName": stage["displayName"],
        "description": stage["description"],
        "spritesheetPath": "spritesheet.webp",
    }
    (target / "pet.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    for stage_name, stage in STAGES.items():
        generate_stage(stage_name, stage)
        print(f"Generated {stage_name}: {stage['displayName']}")


if __name__ == "__main__":
    main()
