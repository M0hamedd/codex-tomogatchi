#!/usr/bin/env python3
"""Generate the Windows app icon from the bundled adult pet sprite."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SPRITE = ROOT / "plugins" / "codex-tomogatchi" / "assets" / "stages" / "adult" / "spritesheet.webp"
OUT = ROOT / "build" / "icon.ico"
FRAME = (0, 0, 192, 208)
SIZES = (16, 24, 32, 48, 64, 128, 256)


def make_icon(size: int) -> Image.Image:
    sheet = Image.open(SPRITE).convert("RGBA")
    pet = sheet.crop(FRAME)
    canvas = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((18, 18, 238, 238), radius=48, fill="#1c2027", outline="#ffd166", width=8)
    pet = pet.resize((174, 188), Image.Resampling.NEAREST)
    canvas.alpha_composite(pet, (41, 38))
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    images = [make_icon(size) for size in SIZES]
    images[-1].save(OUT, sizes=[(size, size) for size in SIZES], append_images=images[:-1])
    print(f"Generated {OUT}")


if __name__ == "__main__":
    main()
