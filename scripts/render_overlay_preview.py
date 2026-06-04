#!/usr/bin/env python3
"""Render a static README preview of the full Tomogatchi overlay."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SPRITE = ROOT / "plugins" / "codex-tomogatchi" / "assets" / "stages" / "teen" / "spritesheet.webp"
OUT = ROOT / "docs" / "screenshots" / "overlay-preview.png"
FRAME = (0, 0, 192, 208)


def font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("segoeui.ttf", size)
    except OSError:
        return ImageFont.load_default()


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str, outline: str | None = None) -> None:
    draw.rounded_rectangle(box, radius=8, fill=fill, outline=outline, width=1)


def meter(draw: ImageDraw.ImageDraw, x: int, y: int, label: str, value: int, color: str) -> None:
    draw.text((x, y), label, fill="#d9d1c6", font=font(13))
    draw.rounded_rectangle((x + 72, y + 4, x + 300, y + 14), radius=5, fill="#34373d")
    draw.rounded_rectangle((x + 72, y + 4, x + 72 + int(228 * value / 100), y + 14), radius=5, fill=color)
    draw.text((x + 312, y - 1), str(value), fill="#fff5e8", font=font(13))


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (980, 620), "#14171c")
    draw = ImageDraw.Draw(image)

    rounded(draw, (260, 32, 720, 588), "#1c2027", "#4a515a")
    draw.text((300, 58), "Codex Tomogatchi", fill="#fff5e8", font=font(28))
    draw.text((300, 92), "Full device view", fill="#f4ba71", font=font(15))

    sprite_sheet = Image.open(SPRITE).convert("RGBA")
    sprite = sprite_sheet.crop(FRAME).resize((250, 270), Image.Resampling.NEAREST)
    image.paste(sprite, (365, 120), sprite)

    rounded(draw, (300, 410, 680, 548), "#242832", "#4a515a")
    meter(draw, 324, 430, "Full", 72, "#ffd166")
    meter(draw, 324, 460, "Energy", 80, "#68d391")
    meter(draw, 324, 490, "Mood", 70, "#68d391")
    meter(draw, 324, 520, "Stress", 15, "#ff6952")

    rounded(draw, (300, 560, 680, 576), "#34373d")
    draw.rounded_rectangle((300, 560, 500, 576), radius=8, fill="#ffd166")
    draw.text((520, 556), "Byteclaw | Builder path", fill="#fff5e8", font=font(13))

    image.save(OUT)
    print(f"Rendered {OUT}")


if __name__ == "__main__":
    main()
