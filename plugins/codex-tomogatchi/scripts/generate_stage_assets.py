#!/usr/bin/env python3
"""Generate deterministic placeholder Codex pet stage atlases.

The repo's default concept assets are imported pet packages. This helper is
kept only for quick placeholder regeneration and writes to assets/placeholders
by default so it does not overwrite the imported concept defaults.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = PLUGIN_ROOT / "assets" / "placeholders"
CELL_W = 192
CELL_H = 208
COLS = 8
ROWS = 9
ATLAS_W = CELL_W * COLS
ATLAS_H = CELL_H * ROWS

ROW_FRAMES = {
    0: 6,
    1: 8,
    2: 8,
    3: 4,
    4: 5,
    5: 8,
    6: 6,
    7: 6,
    8: 6,
}

STAGES = {
    "baby": {
        "displayName": "Codex Tomogatchi (Baby)",
        "description": "A tiny Codex companion just starting to learn your rhythm.",
        "body": "#7BC8A4",
        "belly": "#D7F4DD",
        "accent": "#2E6F64",
        "scale": 0.78,
    },
    "teen": {
        "displayName": "Codex Tomogatchi (Teen)",
        "description": "A curious Codex companion growing from your steady work.",
        "body": "#5BA8D7",
        "belly": "#D8F0FF",
        "accent": "#275B7A",
        "scale": 0.9,
    },
    "adult": {
        "displayName": "Codex Tomogatchi (Adult)",
        "description": "A confident Codex companion shaped by your coding sessions.",
        "body": "#E2A455",
        "belly": "#FFF0C9",
        "accent": "#8B4A2C",
        "scale": 1.0,
    },
}


def hex_to_rgba(value: str) -> tuple[int, int, int, int]:
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), 255)


def draw_frame(stage: dict[str, str | float], row: int, col: int) -> Image.Image:
    frame = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)
    scale = float(stage["scale"])
    body = hex_to_rgba(str(stage["body"]))
    belly = hex_to_rgba(str(stage["belly"]))
    accent = hex_to_rgba(str(stage["accent"]))
    outline = (28, 42, 48, 255)

    phase = col / max(1, ROW_FRAMES[row] - 1)
    bob = int(math.sin(phase * math.tau) * 4)
    dx = 0
    dy = bob

    if row == 1:
        dx = int(math.sin(phase * math.tau) * 8)
    elif row == 2:
        dx = -int(math.sin(phase * math.tau) * 8)
    elif row == 3:
        dy -= int(math.sin(phase * math.pi) * 3)
    elif row == 4:
        dy -= int(math.sin(phase * math.pi) * 34)
    elif row == 5:
        dy += int(math.sin(phase * math.pi) * 5)
    elif row == 6:
        dx = int(math.sin(phase * math.tau) * 2)
    elif row == 7:
        dy -= int(math.sin(phase * math.tau) * 5)
    elif row == 8:
        dx = int(math.sin(phase * math.tau) * 3)

    cx = CELL_W // 2 + dx
    cy = 117 + dy
    body_w = int(86 * scale)
    body_h = int(98 * scale)
    head_r = int(42 * scale)

    # Ears / antenna nubs.
    left_ear = (cx - int(46 * scale), cy - int(80 * scale), cx - int(20 * scale), cy - int(48 * scale))
    right_ear = (cx + int(20 * scale), cy - int(80 * scale), cx + int(46 * scale), cy - int(48 * scale))
    draw.ellipse(left_ear, fill=body, outline=outline, width=3)
    draw.ellipse(right_ear, fill=body, outline=outline, width=3)

    # Body and head.
    body_box = (cx - body_w // 2, cy - body_h // 2, cx + body_w // 2, cy + body_h // 2)
    head_box = (cx - head_r, cy - int(70 * scale), cx + head_r, cy - int(70 * scale) + head_r * 2)
    draw.ellipse(body_box, fill=body, outline=outline, width=4)
    draw.ellipse(head_box, fill=body, outline=outline, width=4)
    belly_box = (cx - int(28 * scale), cy - int(9 * scale), cx + int(28 * scale), cy + int(42 * scale))
    draw.ellipse(belly_box, fill=belly, outline=accent, width=2)

    # Feet.
    foot_y = cy + int(48 * scale)
    step = int(math.sin(phase * math.tau) * 7) if row in (1, 2) else 0
    draw.ellipse((cx - int(36 * scale) + step, foot_y, cx - int(10 * scale) + step, foot_y + int(18 * scale)), fill=accent)
    draw.ellipse((cx + int(10 * scale) - step, foot_y, cx + int(36 * scale) - step, foot_y + int(18 * scale)), fill=accent)

    # Arms vary by state.
    arm_y = cy - int(10 * scale)
    if row == 3:
        wave = int(math.sin(phase * math.pi) * 32)
        draw.line((cx - int(42 * scale), arm_y, cx - int(62 * scale), arm_y - wave), fill=outline, width=5)
        draw.line((cx + int(42 * scale), arm_y, cx + int(60 * scale), arm_y + int(8 * scale)), fill=outline, width=5)
    elif row == 5:
        draw.line((cx - int(42 * scale), arm_y + 8, cx - int(62 * scale), arm_y + 18), fill=outline, width=5)
        draw.line((cx + int(42 * scale), arm_y + 8, cx + int(62 * scale), arm_y + 18), fill=outline, width=5)
    else:
        swing = int(math.sin(phase * math.tau) * 10)
        draw.line((cx - int(42 * scale), arm_y, cx - int(61 * scale), arm_y + swing), fill=outline, width=5)
        draw.line((cx + int(42 * scale), arm_y, cx + int(61 * scale), arm_y - swing), fill=outline, width=5)

    # Face.
    eye_y = cy - int(45 * scale)
    if row == 5:
        draw.line((cx - 20, eye_y - 5, cx - 8, eye_y + 5), fill=outline, width=4)
        draw.line((cx - 8, eye_y - 5, cx - 20, eye_y + 5), fill=outline, width=4)
        draw.line((cx + 8, eye_y - 5, cx + 20, eye_y + 5), fill=outline, width=4)
        draw.line((cx + 20, eye_y - 5, cx + 8, eye_y + 5), fill=outline, width=4)
        draw.arc((cx - 14, eye_y + 22, cx + 14, eye_y + 42), 200, 340, fill=outline, width=3)
    elif row == 6:
        draw.ellipse((cx - 23, eye_y - 4, cx - 11, eye_y + 8), fill=outline)
        draw.ellipse((cx + 11, eye_y - 4, cx + 23, eye_y + 8), fill=outline)
        draw.arc((cx - 12, eye_y + 12, cx + 12, eye_y + 30), 20, 160, fill=outline, width=3)
    else:
        blink = row == 0 and col == 2
        if blink:
            draw.line((cx - 23, eye_y + 2, cx - 11, eye_y + 2), fill=outline, width=3)
            draw.line((cx + 11, eye_y + 2, cx + 23, eye_y + 2), fill=outline, width=3)
        else:
            draw.ellipse((cx - 23, eye_y - 4, cx - 11, eye_y + 8), fill=outline)
            draw.ellipse((cx + 11, eye_y - 4, cx + 23, eye_y + 8), fill=outline)
        draw.arc((cx - 14, eye_y + 8, cx + 14, eye_y + 28), 20, 160, fill=outline, width=3)

    # Tiny stage badge, geometric only; no text.
    badge_r = 5 if scale < 0.8 else 7 if scale < 1 else 9
    draw.ellipse((cx + 24, cy + 12, cx + 24 + badge_r * 2, cy + 12 + badge_r * 2), fill=accent)
    return frame


def make_stage(output_root: Path, stage_name: str, stage: dict[str, str | float]) -> None:
    output = output_root / stage_name
    output.mkdir(parents=True, exist_ok=True)
    atlas = Image.new("RGBA", (ATLAS_W, ATLAS_H), (0, 0, 0, 0))
    for row, frame_count in ROW_FRAMES.items():
        for col in range(frame_count):
            frame = draw_frame(stage, row, col)
            atlas.alpha_composite(frame, (col * CELL_W, row * CELL_H))
    atlas.save(output / "spritesheet.webp", "WEBP", lossless=True, quality=100, method=6)
    manifest = {
        "id": f"codex-tomogatchi-{stage_name}",
        "displayName": stage["displayName"],
        "description": stage["description"],
        "spritesheetPath": "spritesheet.webp",
    }
    (output / "pet.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate placeholder Codex pet atlases.")
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Directory for generated stage folders. Defaults to assets/placeholders.",
    )
    args = parser.parse_args()
    output_root = Path(args.output_root).expanduser().resolve()
    for name, stage in STAGES.items():
        make_stage(output_root, name, stage)
    print(f"Generated placeholder stage assets in {output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
