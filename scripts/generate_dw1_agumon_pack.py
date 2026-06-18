#!/usr/bin/env python3
"""Generate a Digimon World 1 Agumon-line example pet pack.

The requirement data is transcribed from SydMontague's Digimon World evolution
guide. The sprites are simple local concept atlases for testing the branching
pack format; they are not ripped game assets.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
PACK_ROOT = ROOT / "examples" / "pet-packs" / "digimon-world-1-agumon"
SOURCE_URL = "https://gamefaqs.gamespot.com/ps/913684-digimon-world/faqs/73845?single=1"
SOURCE_NOTICE = """# Digimon World 1 Agumon Example Source Notice

This pet pack is a branching-rule example for Codex Tomogatchi. It uses Digimon World 1-style evolution requirement groups transcribed from:

https://gamefaqs.gamespot.com/ps/913684-digimon-world/faqs/73845?single=1

The included `spritesheet.webp` files are locally generated Codex Tomogatchi concept atlases. They are not ripped game sprites and not copied game artwork.

Digimon, Digimon World, Agumon, and related character names are trademarks or protected works of their respective owners. Codex Tomogatchi is not affiliated with, endorsed by, sponsored by, or approved by those owners. This pack is included as a local example for compatibility testing and branching-rule demonstration.
"""
FRAME_W = 192
FRAME_H = 208
COLUMNS = 8
ROWS = 9
LOW_W = 48
LOW_H = 52
SCALE = 4


def dw1(stats: dict[str, int], care: dict[str, int], weight: tuple[int, int], bonus: list[dict[str, int]]) -> dict[str, Any]:
    return {
        "groupsRequired": 3,
        "stats": stats,
        "careMistakes": care,
        "weight": {"min": weight[0], "max": weight[1]},
        "bonus": bonus,
    }


def source_requirements(lines: str, text: str) -> dict[str, str]:
    return {
        "game": "Digimon World (PlayStation)",
        "source": SOURCE_URL,
        "sourceLines": lines,
        "text": text,
    }


FORMS: dict[str, list[dict[str, Any]]] = {
    "baby": [
        {
            "id": "agumon",
            "name": "Agumon",
            "assetPath": "forms/baby/agumon",
            "path": "rookie",
            "default": True,
            "reason": "Koromon-to-Agumon starter for this DW1 pack",
            "sourceRequirements": source_requirements(
                "638-654",
                "Agumon evolves from Koromon and can evolve to Greymon, Meramon, Birdramon, Centarumon, Monochromon, and Tyrannomon.",
            ),
            "look": {"body": "#f47a2f", "belly": "#ffd184", "accent": "#2d2a25", "horn": "#f5e0b0", "kind": "dino", "size": 0},
        }
    ],
    "teen": [
        {
            "id": "greymon",
            "name": "Greymon",
            "assetPath": "forms/teen/greymon",
            "path": "dw1-greymon",
            "evolvesFrom": ["agumon"],
            "requirements": {"reason": "DW1 Greymon groups matched", "dw1": dw1(
                {"hp": 2000, "mp": 1500, "offense": 100, "defense": 100, "speed": 100, "brains": 100},
                {"max": 1},
                (25, 35),
                [{"disciplineMin": 90}, {"techniquesMin": 35}],
            )},
            "sourceRequirements": source_requirements("782-794", "Care <= 1, weight 25-35, discipline >= 90 or techniques >= 35, and listed stats."),
            "look": {"body": "#d9792d", "belly": "#f6d087", "accent": "#2b2a24", "horn": "#f5e0b0", "kind": "dino", "size": 1},
        },
        {
            "id": "meramon",
            "name": "Meramon",
            "assetPath": "forms/teen/meramon",
            "path": "dw1-meramon",
            "evolvesFrom": ["agumon"],
            "requirements": {"reason": "DW1 Meramon groups matched", "dw1": dw1(
                {"hp": 1000, "mp": 1500, "offense": 100, "defense": 150, "speed": 150, "brains": 150},
                {"min": 5},
                (15, 25),
                [{"battlesMin": 10}, {"techniquesMin": 28}],
            )},
            "sourceRequirements": source_requirements("795-807", "Care >= 5, weight 15-25, battles >= 10 or techniques >= 28, and listed stats."),
            "look": {"body": "#f04b28", "belly": "#ffd45b", "accent": "#8a1f18", "horn": "#ffe08a", "kind": "flame", "size": 1},
        },
        {
            "id": "birdramon",
            "name": "Birdramon",
            "assetPath": "forms/teen/birdramon",
            "path": "dw1-birdramon",
            "evolvesFrom": ["agumon"],
            "requirements": {"reason": "DW1 Birdramon groups matched", "dw1": dw1(
                {"hp": 1500, "mp": 1500, "offense": 150, "defense": 100, "speed": 100, "brains": 150},
                {"min": 3},
                (15, 25),
                [{"techniquesMin": 35}],
            )},
            "sourceRequirements": source_requirements("808-820", "Care >= 3, weight 15-25, techniques >= 35, and listed stats."),
            "look": {"body": "#df4f2f", "belly": "#ffc45a", "accent": "#f4a43d", "horn": "#ffe3a2", "kind": "bird", "size": 1},
        },
        {
            "id": "centarumon",
            "name": "Centarumon",
            "assetPath": "forms/teen/centarumon",
            "path": "dw1-centarumon",
            "evolvesFrom": ["agumon"],
            "requirements": {"reason": "DW1 Centarumon groups matched", "dw1": dw1(
                {"hp": 1500, "mp": 1500, "offense": 150, "defense": 150, "speed": 150, "brains": 100},
                {"max": 3},
                (25, 35),
                [{"disciplineMin": 60}, {"techniquesMin": 28}],
            )},
            "sourceRequirements": source_requirements("821-834", "Care <= 3, weight 25-35, discipline >= 60 or techniques >= 28, and listed stats."),
            "look": {"body": "#b77a48", "belly": "#edd09a", "accent": "#6e4c32", "horn": "#e8e2cc", "kind": "centaur", "size": 1},
        },
        {
            "id": "monochromon",
            "name": "Monochromon",
            "assetPath": "forms/teen/monochromon",
            "path": "dw1-monochromon",
            "evolvesFrom": ["agumon"],
            "requirements": {"reason": "DW1 Monochromon groups matched", "dw1": dw1(
                {"hp": 1000, "mp": 1500, "offense": 150, "defense": 100, "speed": 150, "brains": 100},
                {"max": 3},
                (35, 45),
                [{"battlesMax": 5}, {"techniquesMin": 35}],
            )},
            "sourceRequirements": source_requirements("835-848", "Care <= 3, weight 35-45, battles <= 5 or techniques >= 35, and listed stats."),
            "look": {"body": "#6f7469", "belly": "#c5c5a7", "accent": "#343834", "horn": "#ece3c0", "kind": "armored", "size": 1},
        },
        {
            "id": "tyrannomon",
            "name": "Tyrannomon",
            "assetPath": "forms/teen/tyrannomon",
            "path": "dw1-tyrannomon",
            "evolvesFrom": ["agumon"],
            "requirements": {"reason": "DW1 Tyrannomon groups matched", "dw1": dw1(
                {"hp": 1000, "mp": 1500, "offense": 150, "defense": 100, "speed": 150, "brains": 150},
                {"max": 5},
                (25, 35),
                [{"battlesMax": 5}, {"techniquesMin": 28}],
            )},
            "sourceRequirements": source_requirements("862-875", "Care <= 5, weight 25-35, battles <= 5 or techniques >= 28, and listed stats."),
            "look": {"body": "#bb5432", "belly": "#f3c47d", "accent": "#55281f", "horn": "#f3e0b5", "kind": "dino", "size": 1},
        },
        {
            "id": "numemon",
            "name": "Numemon",
            "assetPath": "forms/teen/numemon",
            "path": "dw1-numemon",
            "evolvesFrom": ["agumon"],
            "default": True,
            "reason": "DW1 special fallback when Rookie requirements are missed",
            "sourceRequirements": source_requirements("2380-2384", "Any Rookie can become Numemon after 96h on Rookie level; stats are reduced by 20%."),
            "look": {"body": "#88a45f", "belly": "#c8db98", "accent": "#4e693c", "horn": "#d7e5a8", "kind": "slime", "size": 1},
        },
    ],
    "adult": [
        {
            "id": "metalgreymon",
            "name": "MetalGreymon",
            "assetPath": "forms/adult/metalgreymon",
            "path": "dw1-metalgreymon",
            "evolvesFrom": ["greymon", "meramon", "monochromon", "tyrannomon"],
            "requirements": {"reason": "DW1 MetalGreymon groups matched", "dw1": dw1(
                {"hp": 4000, "mp": 3000, "offense": 500, "defense": 500, "speed": 300, "brains": 300},
                {"max": 10},
                (60, 70),
                [{"disciplineMin": 95}, {"battlesMin": 30}, {"techniquesMin": 30}],
            )},
            "sourceRequirements": source_requirements("1172-1187", "Care <= 10, weight 60-70, discipline >= 95 or battles >= 30 or techniques >= 30, and listed stats."),
            "look": {"body": "#b85f33", "belly": "#e6c079", "accent": "#6c7074", "horn": "#ead9aa", "kind": "cyborg-dino", "size": 2},
        },
        {
            "id": "skullgreymon",
            "name": "SkullGreymon",
            "assetPath": "forms/adult/skullgreymon",
            "path": "dw1-skullgreymon",
            "evolvesFrom": ["greymon"],
            "requirements": {"reason": "DW1 SkullGreymon groups matched", "dw1": dw1(
                {"hp": 4000, "mp": 6000, "offense": 400, "defense": 400, "speed": 200, "brains": 500},
                {"min": 10},
                (25, 35),
                [{"battlesMin": 40}, {"techniquesMin": 45}],
            )},
            "sourceRequirements": source_requirements("1204-1219", "Care >= 10, weight 25-35, battles >= 40 or techniques >= 45, and listed stats."),
            "look": {"body": "#c9c3b2", "belly": "#f0ead7", "accent": "#5e5b54", "horn": "#fff3d0", "kind": "skull", "size": 2},
        },
        {
            "id": "andromon",
            "name": "Andromon",
            "assetPath": "forms/adult/andromon",
            "path": "dw1-andromon",
            "evolvesFrom": ["meramon", "centarumon"],
            "requirements": {"reason": "DW1 Andromon groups matched", "dw1": dw1(
                {"hp": 2000, "mp": 4000, "offense": 200, "defense": 400, "speed": 200, "brains": 400},
                {"max": 5},
                (35, 45),
                [{"disciplineMin": 95}, {"battlesMin": 30}, {"techniquesMin": 30}],
            )},
            "sourceRequirements": source_requirements("1188-1203", "Care <= 5, weight 35-45, discipline >= 95 or battles >= 30 or techniques >= 30, and listed stats."),
            "look": {"body": "#8f9499", "belly": "#d6dde0", "accent": "#d94545", "horn": "#e7e7e7", "kind": "android", "size": 2},
        },
        {
            "id": "phoenixmon",
            "name": "Phoenixmon",
            "assetPath": "forms/adult/phoenixmon",
            "path": "dw1-phoenixmon",
            "evolvesFrom": ["birdramon"],
            "requirements": {"reason": "DW1 Phoenixmon groups matched", "dw1": dw1(
                {"hp": 4000, "mp": 4000, "offense": 400, "defense": 400, "speed": 400, "brains": 600},
                {"max": 3},
                (25, 35),
                [{"disciplineMin": 100}, {"battlesMax": 0}, {"techniquesMin": 40}],
            )},
            "sourceRequirements": source_requirements("1250-1265", "Care <= 3, weight 25-35, discipline >= 100 or battles <= 0 or techniques >= 40, and listed stats."),
            "look": {"body": "#d94e2f", "belly": "#ffcd58", "accent": "#f0a33d", "horn": "#ffe3a4", "kind": "phoenix", "size": 2},
        },
        {
            "id": "megadramon",
            "name": "Megadramon",
            "assetPath": "forms/adult/megadramon",
            "path": "dw1-megadramon",
            "evolvesFrom": ["tyrannomon"],
            "requirements": {"reason": "DW1 Megadramon groups matched", "dw1": dw1(
                {"hp": 3000, "mp": 5000, "offense": 500, "defense": 300, "speed": 400, "brains": 400},
                {"max": 10},
                (50, 60),
                [{"battlesMin": 30}, {"techniquesMin": 30}],
            )},
            "sourceRequirements": source_requirements("1220-1235", "Care <= 10, weight 50-60, battles >= 30 or techniques >= 30, and listed stats."),
            "look": {"body": "#813e45", "belly": "#bfc5c7", "accent": "#5a626b", "horn": "#e6d6aa", "kind": "cyborg-dragon", "size": 2},
        },
        {
            "id": "metalmamemon",
            "name": "MetalMamemon",
            "assetPath": "forms/adult/metalmamemon",
            "path": "dw1-metalmamemon",
            "evolvesFrom": ["monochromon"],
            "requirements": {"reason": "DW1 MetalMamemon groups matched", "dw1": dw1(
                {"hp": 3000, "mp": 3000, "offense": 500, "defense": 400, "speed": 400, "brains": 400},
                {"max": 15},
                (5, 15),
                [{"happinessMin": 95}, {"techniquesMin": 30}],
            )},
            "sourceRequirements": source_requirements("1295-1309", "Care <= 15, weight 5-15, happiness >= 95 or techniques >= 30, and listed stats."),
            "look": {"body": "#c6c9ca", "belly": "#f0f3f4", "accent": "#4c6b83", "horn": "#ededed", "kind": "metal-ball", "size": 2},
        },
        {
            "id": "giromon",
            "name": "Giromon",
            "assetPath": "forms/adult/giromon",
            "path": "dw1-giromon",
            "evolvesFrom": ["centarumon"],
            "requirements": {"reason": "DW1 Giromon groups matched", "dw1": dw1(
                {"hp": 3000, "mp": 3000, "offense": 400, "defense": 600, "speed": 300, "brains": 400},
                {"min": 15},
                (0, 10),
                [{"happinessMin": 95}, {"battlesMin": 100}, {"techniquesMin": 35}],
            )},
            "sourceRequirements": source_requirements("1235-1249", "Care >= 15, weight 0-10, happiness >= 95 or battles >= 100 or techniques >= 35, and listed stats."),
            "look": {"body": "#c44848", "belly": "#f4e9cf", "accent": "#33373c", "horn": "#f2f2f2", "kind": "gear", "size": 2},
        },
        {
            "id": "monzaemon",
            "name": "Monzaemon",
            "assetPath": "forms/adult/monzaemon",
            "path": "dw1-monzaemon",
            "evolvesFrom": ["numemon"],
            "default": True,
            "reason": "DW1 Numemon special evolution counterpart",
            "sourceRequirements": source_requirements("2447-2451", "Numemon can become Monzaemon by talking to the Monzaemon suit in Toy Town."),
            "look": {"body": "#d49358", "belly": "#f3d7a3", "accent": "#684432", "horn": "#f8e0ba", "kind": "bear", "size": 2},
        },
    ],
}


def hex_rgba(value: str) -> tuple[int, int, int, int]:
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), 255)


def draw_pixel_form(look: dict[str, Any], row: int, column: int) -> Image.Image:
    frame = Image.new("RGBA", (48, 52), (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)
    body = hex_rgba(str(look["body"]))
    belly = hex_rgba(str(look["belly"]))
    accent = hex_rgba(str(look["accent"]))
    horn = hex_rgba(str(look["horn"]))
    outline = (33, 28, 25, 255)
    kind = str(look["kind"])
    size = int(look["size"])
    bob = [0, -1, 0, 1, 0, -1, 0, 1][column % 8]
    x = 24 + (-1 if column % 4 == 1 else 1 if column % 4 == 3 else 0)
    y = 8 + bob - min(size, 1)
    tall = size >= 2

    draw.ellipse((9, 43, 39, 48), fill=(0, 0, 0, 48))

    if kind in {"bird", "phoenix"}:
        draw.polygon([(x - 10, y + 22), (x - 23, y + 11), (x - 17, y + 31)], fill=accent)
        draw.polygon([(x + 10, y + 22), (x + 23, y + 11), (x + 17, y + 31)], fill=accent)
        draw.polygon([(x - 3, y + 9), (x + 3, y + 9), (x, y + 3)], fill=horn)
    elif "cyborg" in kind:
        draw.rectangle((x + 8, y + 20, x + 22, y + 30), fill=accent)
        draw.rectangle((x + 18, y + 24, x + 27, y + 27), fill=outline)
    elif kind in {"centaur", "armored"}:
        draw.rectangle((x - 19, y + 29, x + 17, y + 40), fill=body)
        draw.rectangle((x - 18, y + 39, x - 13, y + 47), fill=body)
        draw.rectangle((x + 11, y + 39, x + 16, y + 47), fill=body)
    elif kind == "gear":
        for dx, dy in [(-14, -8), (14, -8), (-14, 10), (14, 10)]:
            draw.rectangle((x + dx - 2, y + 22 + dy - 2, x + dx + 2, y + 22 + dy + 2), fill=accent)

    head_box = (x - 12 - size, y + 5, x + 12 + size, y + 28 + size)
    body_box = (x - 13 - size, y + 22, x + 13 + size, y + 43 + size)
    if kind in {"slime", "metal-ball"}:
        body_box = (x - 15, y + 16, x + 15, y + 42)
        draw.ellipse(body_box, fill=body, outline=outline)
    else:
        draw.ellipse(body_box, fill=body, outline=outline)
        draw.ellipse(head_box, fill=body, outline=outline)

    draw.ellipse((x - 7, y + 27, x + 7, y + 42), fill=belly)

    if kind in {"dino", "cyborg-dino", "skull", "cyborg-dragon"}:
        draw.polygon([(x - 8, y + 8), (x - 16, y + 1), (x - 7, y + 3)], fill=horn)
        draw.polygon([(x + 8, y + 8), (x + 16, y + 1), (x + 7, y + 3)], fill=horn)
        draw.polygon([(x + 13, y + 33), (x + 26, y + 28), (x + 16, y + 38)], fill=body)
    elif kind == "flame":
        draw.polygon([(x - 9, y + 7), (x - 4, y - 2), (x, y + 7)], fill=horn)
        draw.polygon([(x, y + 7), (x + 5, y - 4), (x + 10, y + 8)], fill=accent)
    elif kind == "android":
        draw.rectangle((x - 10, y + 7, x + 10, y + 25), fill=body, outline=outline)
        draw.rectangle((x - 15, y + 28, x - 10, y + 39), fill=accent)
        draw.rectangle((x + 10, y + 28, x + 15, y + 39), fill=accent)
    elif kind == "bear":
        draw.ellipse((x - 15, y + 5, x - 7, y + 13), fill=body, outline=outline)
        draw.ellipse((x + 7, y + 5, x + 15, y + 13), fill=body, outline=outline)

    if tall:
        draw.rectangle((x - 12, y + 42, x - 6, y + 50), fill=body, outline=outline)
        draw.rectangle((x + 6, y + 42, x + 12, y + 50), fill=body, outline=outline)
    else:
        draw.rectangle((x - 10, y + 39, x - 5, y + 47), fill=body)
        draw.rectangle((x + 5, y + 39, x + 10, y + 47), fill=body)

    blink = row == 1 and column in {2, 3}
    eye_y = y + 16
    if blink:
        draw.rectangle((x - 7, eye_y, x - 3, eye_y + 1), fill=outline)
        draw.rectangle((x + 3, eye_y, x + 7, eye_y + 1), fill=outline)
    else:
        draw.rectangle((x - 7, eye_y - 2, x - 4, eye_y + 2), fill=outline)
        draw.rectangle((x + 4, eye_y - 2, x + 7, eye_y + 2), fill=outline)
    if row in {4, 5}:
        draw.rectangle((x - 4, y + 24, x + 4, y + 25), fill=outline)
    else:
        draw.rectangle((x - 2, y + 24, x + 2, y + 25), fill=outline)

    if row in {6, 7, 8}:
        draw.ellipse((x - 16, y + 36, x - 10, y + 41), fill=accent)
        draw.ellipse((x + 10, y + 36, x + 16, y + 41), fill=accent)
    return frame.resize((FRAME_W, FRAME_H), Image.Resampling.NEAREST)


def write_form(stage: str, form: dict[str, Any]) -> None:
    target = PACK_ROOT / form["assetPath"]
    target.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGBA", (FRAME_W * COLUMNS, FRAME_H * ROWS), (0, 0, 0, 0))
    for row in range(ROWS):
        for column in range(COLUMNS):
            frame = draw_pixel_form(form["look"], row, column)
            sheet.alpha_composite(frame, (column * FRAME_W, row * FRAME_H))
    sheet.save(target / "spritesheet.webp", "WEBP", lossless=True, quality=100, method=6)
    manifest = {
        "id": form["id"],
        "displayName": form["name"],
        "description": f"Digimon World 1 counterpart form for the Agumon example pack.",
        "spritesheetPath": "spritesheet.webp",
    }
    (target / "pet.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def stripped_form(form: dict[str, Any]) -> dict[str, Any]:
    cleaned = {key: value for key, value in form.items() if key != "look"}
    return cleaned


def main() -> int:
    PACK_ROOT.mkdir(parents=True, exist_ok=True)
    for stage, forms in FORMS.items():
        for form in forms:
            write_form(stage, form)
    pack = {
        "schemaVersion": 1,
        "id": "digimon-world-1-agumon",
        "name": "Digimon World 1 Agumon Line",
        "author": "Codex Tomogatchi Contributors",
        "description": "A branching example pack based on Digimon World 1 Agumon evolution requirements.",
        "source": {
            "name": "Digimon World - Evolution Guide by SydMontague",
            "url": SOURCE_URL,
            "license": "Guide/source terms belong to the linked author/site; game names and characters belong to their respective owners.",
            "assetNotice": "Sprites are locally generated Codex Tomogatchi concept atlases, not copied game assets.",
            "trademarkNotice": "Not affiliated with, endorsed by, sponsored by, or approved by the owners of Digimon or Digimon World.",
            "notes": "Natural evolutions use the original 3-of-4 DW1 requirement groups: stats, care mistakes, weight, and bonus.",
        },
        "forms": {
            stage: [stripped_form(form) for form in forms]
            for stage, forms in FORMS.items()
        },
    }
    (PACK_ROOT / "pack.json").write_text(json.dumps(pack, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (PACK_ROOT / "SOURCE.md").write_text(SOURCE_NOTICE, encoding="utf-8")
    print(f"Generated {PACK_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
