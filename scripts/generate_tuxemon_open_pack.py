#!/usr/bin/env python3
"""Generate a DW1-sized open-source branching pet pack from Tuxemon data.

The evolution graph and monster metadata are read from a local Tuxemon source
checkout. The generated sprites are simple local concept atlases; this script
does not copy Tuxemon image assets.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml
from PIL import Image

from generate_dw1_agumon_pack import COLUMNS, FRAME_H, FRAME_W, ROWS, draw_pixel_form


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = Path(os.environ.get("TUXEMON_SOURCE", ROOT / ".tmp" / "tuxemon-source"))
MONSTER_ROOT = SOURCE_ROOT / "mods" / "tuxemon" / "db" / "monster"
PACK_ROOT = ROOT / "examples" / "pet-packs" / "tuxemon-open-61"
SOURCE_URL = "https://github.com/Tuxemon/Tuxemon"
MONSTER_SOURCE_URL = "https://github.com/Tuxemon/Tuxemon/tree/development/mods/tuxemon/db/monster"
TARGET_FORMS = 61
SOURCE_NOTICE = """# Tuxemon Open 61 Source Notice

This pet pack uses evolution relationships and monster metadata derived from
the open-source Tuxemon monster YAML data:

https://github.com/Tuxemon/Tuxemon/tree/development/mods/tuxemon/db/monster

Tuxemon source data is licensed GPL-3.0-or-later. See the upstream Tuxemon
LICENSE and CONTRIBUTING.md files for the full terms.

This pack does not copy Tuxemon sprite artwork. The included spritesheet.webp
files are locally generated Codex Tomogatchi concept atlases.

Because this pack uses GPL-3.0-or-later source data, do not treat it as covered
only by the repository's MIT license. Keep this notice with the pack when
redistributing it.
"""


SELECTED_PATHS: tuple[tuple[str, str, str], ...] = (
    ("agnite", "agnidon", "agnigon"),
    ("anoleaf", "gectile", "velocitile"),
    ("banling", "bansaken", "banvengeance"),
    ("cackleen", "brumi", "bewhich"),
    ("cardiling", "cardiwing", "cardinale"),
    ("cataspike", "puparmor", "weavifly"),
    ("chloragon", "sapragon", "dragarbor"),
    ("devidin", "devidra", "deviraptor"),
    ("drashimi", "tsushimi", "tobishimi"),
    ("elofly", "elowind", "elostorm"),
    ("flacono", "corvix", "gryfix"),
    ("fruitera", "megafruitera", "spectera"),
    ("gupphish", "gupphire", "golnagi"),
    ("hoarse", "equill", "hoarseshoo"),
    ("rockitten", "rockat", "jemuar"),
    ("waysprite", "angesnow", "seraphice"),
    ("waysprite", "demosnow", "lucifice"),
    ("katapill", "katacoon", "bugnin"),
    ("katapill", "katacoon", "sumchon"),
    ("katapill", "katacoon", "gladiatorbug"),
    ("mk01_proto", "mk01_alpha", "mk01_delta"),
    ("mk01_proto", "mk01_alpha", "mk01_gamma"),
    ("mk01_proto", "mk01_beta", "mk01_delta"),
    ("mk01_proto", "mk01_beta", "mk01_omega"),
)

TYPE_COLORS: dict[str, tuple[str, str, str, str]] = {
    "cosmic": ("#5b4da0", "#b9b1ff", "#2f255f", "#e6dcff"),
    "earth": ("#9a7043", "#dbc08a", "#56412c", "#efe0b5"),
    "fire": ("#e25735", "#ffd06c", "#8b2820", "#ffe6a7"),
    "frost": ("#86cce3", "#e4f7ff", "#3d7f99", "#ffffff"),
    "heroic": ("#d9b33f", "#fff0a6", "#806729", "#ffffff"),
    "lightning": ("#e0c93f", "#fff3a1", "#756b22", "#ffffff"),
    "metal": ("#89929a", "#d9e0e4", "#4d5962", "#f5f7f8"),
    "normal": ("#b9825d", "#edcf9d", "#65432f", "#f5deb6"),
    "shadow": ("#635179", "#d0bfe5", "#31273f", "#efe1ff"),
    "sky": ("#65a6ce", "#d5eef9", "#31556e", "#f7fdff"),
    "venom": ("#8172a8", "#d8caef", "#4d3c70", "#f4ecff"),
    "water": ("#4e8fc7", "#d3ebff", "#244b74", "#f0fbff"),
    "wood": ("#5e9b63", "#c8e5a9", "#2f5a39", "#edf7d5"),
}

SHAPE_KINDS: dict[str, str] = {
    "blob": "slime",
    "brute": "armored",
    "dragon": "dino",
    "flier": "bird",
    "grub": "slime",
    "humanoid": "android",
    "hunter": "dino",
    "landrace": "bear",
    "leviathan": "cyborg-dragon",
    "piscine": "cyborg-dragon",
    "polliwog": "slime",
    "serpent": "cyborg-dragon",
    "sprite": "flame",
    "varmint": "bear",
}

BRANCH_REQUIREMENTS: tuple[dict[str, Any], ...] = (
    {
        "reason": "steady care branch",
        "maxCareMistakes": 1,
        "minCareTotal": 2,
    },
    {
        "reason": "explorer focus branch",
        "dominantFocus": "explorer",
        "minDominantFocus": 2,
    },
    {
        "reason": "stress mistake branch",
        "minMistakesByKind": {"stress": 1},
    },
    {
        "reason": "debugger focus branch",
        "dominantFocus": "debugger",
        "minDominantFocus": 2,
    },
)


def slug_to_name(slug: str) -> str:
    return " ".join(part.upper() if part.startswith("mk") else part.capitalize() for part in slug.replace("-", "_").split("_"))


def load_monsters() -> dict[str, dict[str, Any]]:
    if not MONSTER_ROOT.exists():
        raise SystemExit(
            f"Missing Tuxemon monster data at {MONSTER_ROOT}. "
            "Clone Tuxemon to .tmp/tuxemon-source or set TUXEMON_SOURCE."
        )

    monsters: dict[str, dict[str, Any]] = {}
    for path in sorted(MONSTER_ROOT.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            continue
        slug = str(data.get("slug") or path.stem)
        data["_sourceFile"] = str(path.relative_to(SOURCE_ROOT)).replace("\\", "/")
        monsters[slug] = data
    return monsters


def evolution_between(monsters: dict[str, dict[str, Any]], parent: str, child: str) -> dict[str, Any]:
    for evolution in monsters[parent].get("evolutions") or []:
        if isinstance(evolution, dict) and evolution.get("monster_slug") == child:
            return dict(evolution)
    raise SystemExit(f"Selected path is not in Tuxemon data: {parent} -> {child}")


def ordered_unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    values: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            values.append(item)
    return values


def selected_stage_slugs() -> dict[str, list[str]]:
    return {
        "baby": ordered_unique([path[0] for path in SELECTED_PATHS]),
        "teen": ordered_unique([path[1] for path in SELECTED_PATHS]),
        "adult": ordered_unique([path[2] for path in SELECTED_PATHS]),
    }


def selected_parent_map(stage: str) -> dict[str, list[str]]:
    parents: dict[str, list[str]] = defaultdict(list)
    for baby, teen, adult in SELECTED_PATHS:
        if stage == "teen":
            parents[teen].append(baby)
        elif stage == "adult":
            parents[adult].append(teen)
    return {child: ordered_unique(values) for child, values in parents.items()}


def child_order(stage: str) -> dict[str, list[str]]:
    children: dict[str, list[str]] = defaultdict(list)
    for baby, teen, adult in SELECTED_PATHS:
        if stage == "teen":
            children[baby].append(teen)
        elif stage == "adult":
            children[teen].append(adult)
    return {parent: ordered_unique(values) for parent, values in children.items()}


def branch_requirement(stage: str, form_id: str, parents: list[str]) -> dict[str, Any] | None:
    children_by_parent = child_order(stage)
    options: list[dict[str, Any]] = []
    reasons: list[str] = []
    for parent in parents:
        siblings = children_by_parent.get(parent, [])
        if len(siblings) < 2 or form_id not in siblings:
            continue
        index = siblings.index(form_id) % len(BRANCH_REQUIREMENTS)
        requirement = dict(BRANCH_REQUIREMENTS[index])
        options.append(requirement)
        reasons.append(f"{parent} option {index + 1}")

    if not options:
        return None
    if len(options) == 1:
        result = dict(options[0])
    else:
        result = {"any": options, "reason": " or ".join(reason["reason"] for reason in options)}
    result["sourceBranch"] = ", ".join(reasons)
    return result


def source_requirements(monsters: dict[str, dict[str, Any]], stage: str, slug: str, parents: list[str]) -> dict[str, Any]:
    monster = monsters[slug]
    source_edges: list[dict[str, Any]] = []
    for parent in parents:
        evolution = evolution_between(monsters, parent, slug)
        source_edges.append(
            {
                "from": parent,
                "to": slug,
                "atLevel": evolution.get("at_level"),
                "conditions": {key: value for key, value in evolution.items() if key != "monster_slug"},
                "sourceFile": monsters[parent]["_sourceFile"],
            }
        )
    return {
        "game": "Tuxemon",
        "source": MONSTER_SOURCE_URL,
        "sourceLicense": "GPL-3.0-or-later for Tuxemon source data; see Tuxemon LICENSE",
        "sourceSlug": slug,
        "sourceStage": monster.get("stage"),
        "stage": stage,
        "shape": monster.get("shape"),
        "types": monster.get("types") or [],
        "txmnId": monster.get("txmn_id"),
        "height": monster.get("height"),
        "weight": monster.get("weight"),
        "evolutions": source_edges,
    }


def look_for(monster: dict[str, Any], stage: str) -> dict[str, Any]:
    primary_type = str((monster.get("types") or ["normal"])[0])
    colors = TYPE_COLORS.get(primary_type, TYPE_COLORS["normal"])
    shape = str(monster.get("shape") or "blob")
    kind = SHAPE_KINDS.get(shape, "dino")
    if primary_type == "fire" and shape in {"sprite", "blob"}:
        kind = "flame"
    if primary_type == "metal" and shape in {"humanoid", "sprite"}:
        kind = "android"
    size = {"baby": 0, "teen": 1, "adult": 2}[stage]
    return {
        "body": colors[0],
        "belly": colors[1],
        "accent": colors[2],
        "horn": colors[3],
        "kind": kind,
        "size": size,
    }


def write_form_asset(stage: str, form: dict[str, Any], look: dict[str, Any]) -> None:
    target = PACK_ROOT / form["assetPath"]
    target.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGBA", (FRAME_W * COLUMNS, FRAME_H * ROWS), (0, 0, 0, 0))
    for row in range(ROWS):
        for column in range(COLUMNS):
            frame = draw_pixel_form(look, row, column)
            sheet.alpha_composite(frame, (column * FRAME_W, row * FRAME_H))
    sheet.save(target / "spritesheet.webp", "WEBP", lossless=True, quality=100, method=6)
    manifest = {
        "id": f"tuxemon-open-61-{form['id']}",
        "displayName": form["name"],
        "description": f"{form['name']} concept atlas for the Tuxemon Open 61 pack.",
        "spritesheetPath": "spritesheet.webp",
    }
    (target / "pet.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_forms(monsters: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    stage_slugs = selected_stage_slugs()
    parents_by_stage = {
        "baby": {},
        "teen": selected_parent_map("teen"),
        "adult": selected_parent_map("adult"),
    }
    forms: dict[str, list[dict[str, Any]]] = {}
    for stage, slugs in stage_slugs.items():
        stage_forms: list[dict[str, Any]] = []
        first_child_by_parent = {
            parent: children[0]
            for parent, children in child_order(stage).items()
            if children
        }
        for index, slug in enumerate(slugs):
            monster = monsters.get(slug)
            if monster is None:
                raise SystemExit(f"Selected Tuxemon slug is missing: {slug}")
            parents = parents_by_stage.get(stage, {}).get(slug, [])
            form = {
                "id": slug,
                "name": slug_to_name(slug),
                "assetPath": f"forms/{stage}/{slug}",
                "path": f"tuxemon-{slug}",
                "reason": f"Tuxemon {monster.get('stage', stage)} source form",
                "sourceRequirements": source_requirements(monsters, stage, slug, parents),
            }
            if stage == "baby":
                if index == 0:
                    form["default"] = True
            else:
                form["evolvesFrom"] = parents
                if any(first_child_by_parent.get(parent) == slug for parent in parents):
                    form["default"] = True
                requirement = branch_requirement(stage, slug, parents)
                if requirement is not None:
                    form["requirements"] = requirement
            write_form_asset(stage, form, look_for(monster, stage))
            stage_forms.append(form)
        forms[stage] = stage_forms
    return forms


def validate_selected_shape(forms: dict[str, list[dict[str, Any]]]) -> None:
    form_count = sum(len(stage_forms) for stage_forms in forms.values())
    if form_count != TARGET_FORMS:
        raise SystemExit(f"Generated {form_count} forms, expected {TARGET_FORMS}.")


def main() -> int:
    monsters = load_monsters()
    PACK_ROOT.mkdir(parents=True, exist_ok=True)
    forms = build_forms(monsters)
    validate_selected_shape(forms)
    pack = {
        "schemaVersion": 1,
        "id": "tuxemon-open-61",
        "name": "Tuxemon Open 61",
        "author": "Codex Tomogatchi Contributors",
        "description": (
            "A DW1-sized, source-backed branching pack with 61 forms and 24 "
            "real three-stage paths from the open-source Tuxemon evolution graph. "
            "Sprites are local concept atlases, not copied Tuxemon art."
        ),
        "source": {
            "name": "Tuxemon",
            "url": SOURCE_URL,
            "monsterData": MONSTER_SOURCE_URL,
            "license": "GPL-3.0-or-later for source data in the Tuxemon repository",
            "notes": (
                "Tuxemon currently provides 47 real three-stage paths across 128 unique "
                "basic/stage1/stage2 monsters in the checked source. This pack chooses "
                "61 unique forms to match the commonly cited Digimon World 1 playable count."
            ),
            "fullThreeStagePathsAvailable": 47,
            "fullThreeStageFormsAvailable": 128,
            "selectedThreeStagePaths": len(SELECTED_PATHS),
            "selectedForms": TARGET_FORMS,
        },
        "forms": forms,
    }
    (PACK_ROOT / "pack.json").write_text(json.dumps(pack, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (PACK_ROOT / "SOURCE.md").write_text(SOURCE_NOTICE, encoding="utf-8")
    print(f"Generated {PACK_ROOT} ({TARGET_FORMS} forms, {len(SELECTED_PATHS)} paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
