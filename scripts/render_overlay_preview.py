#!/usr/bin/env python3
"""Render static README previews of the Codex Tomogatchi overlay."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "plugins" / "codex-tomogatchi" / "assets" / "stages"
OUT_DIR = ROOT / "docs" / "screenshots"
FRAME = (0, 0, 192, 208)


def font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    family = "segoeuib.ttf" if bold else "segoeui.ttf"
    try:
        return ImageFont.truetype(family, size)
    except OSError:
        return ImageFont.load_default()


def rounded(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill: str,
    outline: str | None = None,
    *,
    radius: int = 8,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def sprite(stage: str, size: tuple[int, int]) -> Image.Image:
    sheet = Image.open(ASSET_ROOT / stage / "spritesheet.webp").convert("RGBA")
    return sheet.crop(FRAME).resize(size, Image.Resampling.NEAREST)


def paste_sprite(image: Image.Image, stage: str, xy: tuple[int, int], size: tuple[int, int]) -> None:
    pet = sprite(stage, size)
    shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    x, y = xy
    shadow_draw.ellipse((x + 24, y + size[1] - 18, x + size[0] - 24, y + size[1] + 8), fill=(0, 0, 0, 80))
    image.alpha_composite(shadow)
    image.alpha_composite(pet, xy)


def meter(draw: ImageDraw.ImageDraw, x: int, y: int, label: str, value: int, color: str) -> None:
    draw.text((x, y), label, fill="#d9d1c6", font=font(13))
    draw.rounded_rectangle((x + 72, y + 4, x + 300, y + 14), radius=5, fill="#34373d")
    draw.rounded_rectangle((x + 72, y + 4, x + 72 + int(228 * value / 100), y + 14), radius=5, fill=color)
    draw.text((x + 312, y - 1), str(value), fill="#fff5e8", font=font(13))


def draw_full_device(
    image: Image.Image,
    *,
    stage: str,
    title: str,
    subtitle: str,
    toast: str | None = None,
    highlight: str | None = None,
    evolution: str | None = None,
) -> None:
    draw = ImageDraw.Draw(image)
    rounded(draw, (260, 32, 720, 588), "#1c2027", "#4a515a")
    draw.text((300, 58), title, fill="#fff5e8", font=font(28, bold=True))
    draw.text((300, 92), subtitle, fill="#f4ba71", font=font(15))

    if evolution:
        for radius, color in ((158, "#5ad7a1"), (120, "#ffd166"), (84, "#ff6952")):
            draw.ellipse((490 - radius, 250 - radius, 490 + radius, 250 + radius), outline=color, width=3)

    paste_sprite(image, stage, (365, 126), (250, 270))

    if toast:
        rounded(draw, (292, 130, 688, 168), "#322b22", "#ffd166")
        draw.text((314, 140), toast, fill="#fff5e8", font=font(15, bold=True))

    rounded(draw, (300, 410, 680, 548), "#242832", "#4a515a")
    meter(draw, 324, 430, "Full", 72, "#ffd166")
    meter(draw, 324, 460, "Energy", 80, "#68d391")
    meter(draw, 324, 490, "Mood", 70, "#68d391")
    meter(draw, 324, 520, "Stress", 15, "#ff6952")

    buttons = [("Feed", 302), ("Rest", 398), ("Play", 494), ("Care", 590)]
    for label, x in buttons:
        active = highlight == label.lower()
        rounded(draw, (x, 356, x + 80, 388), "#ffd166" if active else "#2b3038", "#fff1bc" if active else "#4a515a")
        draw.text((x + 22, 364), label, fill="#1a1d23" if active else "#fff5e8", font=font(12, bold=True))

    rounded(draw, (300, 560, 680, 576), "#34373d")
    draw.rounded_rectangle((300, 560, 500, 576), radius=8, fill="#ffd166")
    draw.text((520, 556), "Byteclaw | Builder path", fill="#fff5e8", font=font(13))


def render_full() -> None:
    image = Image.new("RGBA", (980, 620), "#14171cff")
    draw_full_device(image, stage="teen", title="Codex Tomogatchi", subtitle="Full device view")
    image.convert("RGB").save(OUT_DIR / "overlay-preview.png")


def render_compact() -> None:
    image = Image.new("RGBA", (760, 440), "#14171cff")
    draw = ImageDraw.Draw(image)
    paste_sprite(image, "baby", (276, 74), (210, 228))
    rounded(draw, (224, 304, 536, 392), "#1d222acc", "#4a515a")
    draw.text((246, 322), "Sparkbit", fill="#fff5e8", font=font(21, bold=True))
    draw.text((420, 328), "Baby", fill="#f4ba71", font=font(12, bold=True))
    draw.rounded_rectangle((246, 354, 514, 363), radius=5, fill="#34373d")
    draw.rounded_rectangle((246, 354, 362, 363), radius=5, fill="#ffd166")
    draw.text((246, 370), "42 XP | 48 to next", fill="#d9d1c6", font=font(12))
    draw.text((404, 370), "Mood 72", fill="#d9d1c6", font=font(12))
    image.convert("RGB").save(OUT_DIR / "compact-preview.png")


def render_care_call() -> None:
    image = Image.new("RGBA", (980, 620), "#14171cff")
    draw_full_device(
        image,
        stage="teen",
        title="Care Call",
        subtitle="Answer small needs while you work",
        toast="Byteclaw wants rest",
        highlight="rest",
    )
    image.convert("RGB").save(OUT_DIR / "care-call-preview.png")


def render_evolution() -> None:
    image = Image.new("RGBA", (980, 620), "#14171cff")
    draw_full_device(
        image,
        stage="adult",
        title="Evolution",
        subtitle="Raising choices shape the path",
        toast="Evolution! Teen -> Adult",
        evolution="Stage Up",
    )
    image.convert("RGB").save(OUT_DIR / "evolution-preview.png")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    render_full()
    render_compact()
    render_care_call()
    render_evolution()
    for path in (
        OUT_DIR / "overlay-preview.png",
        OUT_DIR / "compact-preview.png",
        OUT_DIR / "care-call-preview.png",
        OUT_DIR / "evolution-preview.png",
    ):
        print(f"Rendered {path}")


if __name__ == "__main__":
    main()
