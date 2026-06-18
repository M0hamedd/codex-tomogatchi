#!/usr/bin/env python3
"""Codex Tomogatchi state, hook, and install CLI.

The CLI deliberately stores aggregate counters only. Hook payloads are consumed
only to infer event class and success/failure, then discarded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
import zipfile
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
PLUGIN_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = PLUGIN_ROOT / "assets" / "stages"
PET_ID = "codex-tomogatchi"
STAGES = ("baby", "teen", "adult")
BUILTIN_PACK_ID = "default"
PET_PACK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
THRESHOLDS = {"baby": 0, "teen": 90, "adult": 260}
DAILY_XP_CAP = 90
TURN_XP = 7
TURN_TOOL_BONUS_XP = 1
CARE_XP_DAILY_CAP = 6
CARE_MISTAKE_DAILY_CAP = 4
CARE_CALL_RESPONSE_SECONDS = 35 * 60
CARE_CALL_COOLDOWN_SECONDS = 45 * 60
CARE_CALL_STAT_THRESHOLD = 45
CARE_CALL_URGENT_THRESHOLD = 35
NEGLECT_DEATH_SECONDS = 72 * 60 * 60
REBIRTH_SECONDS = 12 * 60 * 60
HOOK_INPUT_LIMIT = 64 * 1024
FOCUS_KEYS = ("builder", "explorer", "debugger", "reviewer")
CARE_KINDS = ("feed", "rest", "play", "comfort")
MISTAKE_KINDS = ("neglect", "overwork", "stress", "death")
TRAINING_KEYS = ("focus", "testing", "care", "recovery")
DW1_STAT_KEYS = ("hp", "mp", "offense", "defense", "speed", "brains")
DW1_METRIC_KEYS = DW1_STAT_KEYS + ("weight", "happiness", "discipline", "battles", "techniques")

DEFAULT_STATS = {
    "fullness": 72,
    "energy": 80,
    "mood": 70,
    "stress": 15,
}

DEFAULT_COUNTERS = {
    "prompts": 0,
    "sessions": 0,
    "turns": 0,
    "toolUses": 0,
    "successfulTools": 0,
    "failedTools": 0,
}

DEFAULT_BRANCH_SIGNALS = {
    "builder": 0,
    "explorer": 0,
    "debugger": 0,
    "reviewer": 0,
}

DEFAULT_INGEST = {
    "sessionLogs": {},
    "pendingTools": {},
}

DEFAULT_TURN_STATE = {
    "currentTurn": 0,
    "toolBonusAwardedForTurn": 0,
}

DEFAULT_LIFECYCLE = {
    "status": "alive",
    "lastInteractionAt": "",
    "deathDueAt": "",
    "diedAt": None,
    "rebirthDueAt": None,
    "rebornAt": None,
    "deaths": 0,
    "rebirths": 0,
}

DEFAULT_REACTION = {
    "sequence": 0,
    "id": "",
    "kind": "",
    "message": "",
    "at": "",
    "expiresAt": "",
}

DEFAULT_SETTINGS = {
    "xp": {
        "pace": "normal",
    },
    "lifecycle": {
        "deathEnabled": True,
    },
    "care": {
        "callStrictness": "normal",
    },
    "overlay": {
        "alwaysOnTop": True,
        "startMode": "compact",
        "startMinimized": False,
    },
    "pets": {
        "activePack": BUILTIN_PACK_ID,
        "starterForm": "",
    },
}

DEFAULT_CARE_CALL = {
    "sequence": 0,
    "active": False,
    "id": "",
    "kind": "",
    "reason": "",
    "createdAt": None,
    "dueAt": None,
    "lastClosedAt": None,
    "lastStatus": "none",
    "answeredAt": None,
    "missedAt": None,
}

FORM_CATALOG = {
    "baby": {
        "default": {
            "formId": "sparkbit",
            "formName": "Sparkbit",
            "path": "starter",
            "assetStage": "baby",
            "reason": "starter form",
        }
    },
    "teen": {
        "partner": {
            "formId": "byteclaw-partner",
            "formName": "Byteclaw",
            "path": "partner",
            "assetStage": "teen",
            "reason": "high care with few mistakes",
        },
        "builder": {
            "formId": "byteclaw-builder",
            "formName": "Byteclaw",
            "path": "builder",
            "assetStage": "teen",
            "reason": "builder focus led the generation",
        },
        "explorer": {
            "formId": "byteclaw-explorer",
            "formName": "Byteclaw",
            "path": "explorer",
            "assetStage": "teen",
            "reason": "explorer focus led the generation",
        },
        "debugger": {
            "formId": "byteclaw-debugger",
            "formName": "Byteclaw",
            "path": "debugger",
            "assetStage": "teen",
            "reason": "debugger focus led the generation",
        },
        "reviewer": {
            "formId": "byteclaw-reviewer",
            "formName": "Byteclaw",
            "path": "reviewer",
            "assetStage": "teen",
            "reason": "reviewer focus led the generation",
        },
        "wild": {
            "formId": "byteclaw-wild",
            "formName": "Byteclaw",
            "path": "wild",
            "assetStage": "teen",
            "reason": "care mistakes shaped a wild path",
        },
        "balanced": {
            "formId": "byteclaw-balanced",
            "formName": "Byteclaw",
            "path": "balanced",
            "assetStage": "teen",
            "reason": "balanced growth",
        },
    },
    "adult": {
        "partner": {
            "formId": "coremaw-partner",
            "formName": "Coremaw",
            "path": "partner",
            "assetStage": "adult",
            "reason": "high care with few mistakes",
        },
        "builder": {
            "formId": "coremaw-builder",
            "formName": "Coremaw",
            "path": "builder",
            "assetStage": "adult",
            "reason": "builder focus led the generation",
        },
        "explorer": {
            "formId": "coremaw-explorer",
            "formName": "Coremaw",
            "path": "explorer",
            "assetStage": "adult",
            "reason": "explorer focus led the generation",
        },
        "debugger": {
            "formId": "coremaw-debugger",
            "formName": "Coremaw",
            "path": "debugger",
            "assetStage": "adult",
            "reason": "debugger focus led the generation",
        },
        "reviewer": {
            "formId": "coremaw-reviewer",
            "formName": "Coremaw",
            "path": "reviewer",
            "assetStage": "adult",
            "reason": "reviewer focus led the generation",
        },
        "wild": {
            "formId": "coremaw-wild",
            "formName": "Coremaw",
            "path": "wild",
            "assetStage": "adult",
            "reason": "care mistakes shaped a wild path",
        },
        "balanced": {
            "formId": "coremaw-balanced",
            "formName": "Coremaw",
            "path": "balanced",
            "assetStage": "adult",
            "reason": "balanced growth",
        },
    },
}

DEFAULT_EVOLUTION = {
    "generation": 1,
    "formId": "sparkbit",
    "formName": "Sparkbit",
    "path": "starter",
    "assetStage": "baby",
    "reason": "starter form",
    "careMistakes": 0,
    "mistakesByKind": {key: 0 for key in MISTAKE_KINDS},
    "carePoints": {key: 0 for key in CARE_KINDS},
    "careCalls": {
        "answered": 0,
        "missed": 0,
        "byKind": {key: 0 for key in CARE_KINDS},
        "missedByKind": {key: 0 for key in CARE_KINDS},
    },
    "focusPoints": {key: 0 for key in FOCUS_KEYS},
    "trainingPoints": {key: 0 for key in TRAINING_KEYS},
    "dw1Stats": {},
    "lineage": [
        {
            "stage": "baby",
            "formId": "sparkbit",
            "formName": "Sparkbit",
            "path": "starter",
            "reason": "starter form",
        }
    ],
    "lastCareAt": None,
    "lastMistakeAt": None,
    "lastEvaluation": {
        "stage": "baby",
        "path": "starter",
        "formId": "sparkbit",
        "reason": "starter form",
    },
}

EVOLUTION_REQUIREMENTS = {
    "teen": [
        {
            "path": "wild",
            "reason": "care mistakes shaped a wild path",
            "any": [
                {"minCareMistakes": 5},
                {"minMissedCalls": 3},
                {"minMistakesByKind": {"stress": 3}},
                {"minMistakesByKind": {"overwork": 3}},
            ],
        },
        {
            "path": "builder",
            "reason": "builder focus led the generation",
            "dominantFocus": "builder",
            "minDominantFocus": 3,
            "maxCareMistakes": 4,
        },
        {
            "path": "explorer",
            "reason": "explorer focus led the generation",
            "dominantFocus": "explorer",
            "minDominantFocus": 3,
            "maxCareMistakes": 4,
        },
        {
            "path": "debugger",
            "reason": "debugger focus led the generation",
            "dominantFocus": "debugger",
            "minDominantFocus": 3,
            "maxCareMistakes": 4,
        },
        {
            "path": "reviewer",
            "reason": "reviewer focus led the generation",
            "dominantFocus": "reviewer",
            "minDominantFocus": 3,
            "maxCareMistakes": 4,
        },
        {
            "path": "partner",
            "reason": "high care with few mistakes",
            "minCareTotal": 6,
            "maxCareMistakes": 1,
            "minCareKinds": {"feed": 1, "rest": 1, "play": 1, "comfort": 1},
        },
        {"path": "balanced", "reason": "balanced growth"},
    ],
    "adult": [
        {
            "path": "wild",
            "reason": "care mistakes shaped a wild path",
            "any": [
                {"minCareMistakes": 5},
                {"minMissedCalls": 3},
                {"minMistakesByKind": {"stress": 3}},
                {"minMistakesByKind": {"overwork": 3}},
            ],
        },
        {
            "path": "builder",
            "reason": "builder focus led the generation",
            "dominantFocus": "builder",
            "minDominantFocus": 5,
            "maxCareMistakes": 4,
        },
        {
            "path": "explorer",
            "reason": "explorer focus led the generation",
            "dominantFocus": "explorer",
            "minDominantFocus": 5,
            "maxCareMistakes": 4,
        },
        {
            "path": "debugger",
            "reason": "debugger focus led the generation",
            "dominantFocus": "debugger",
            "minDominantFocus": 5,
            "maxCareMistakes": 4,
        },
        {
            "path": "reviewer",
            "reason": "reviewer focus led the generation",
            "dominantFocus": "reviewer",
            "minDominantFocus": 5,
            "maxCareMistakes": 4,
        },
        {
            "path": "partner",
            "reason": "high care with few mistakes",
            "minCareTotal": 10,
            "minAnsweredCalls": 2,
            "maxCareMistakes": 1,
            "minCareKinds": {"feed": 2, "rest": 2, "play": 2, "comfort": 1},
        },
        {"path": "balanced", "reason": "balanced growth"},
    ],
}

REACTION_MESSAGES = {
    "wake": "Back at it.",
    "prompt": "Listening.",
    "tool_success": "That worked.",
    "tool_failure": "Needs a hand.",
    "test_pass": "Tests passed.",
    "test_fail": "Tests need attention.",
    "care": "Feeling better.",
    "care_call": "Needs care.",
    "care_answered": "Care answered.",
    "care_miss": "Care mistake.",
    "death": "Tomogatchi died.",
    "rebirth": "Reborn as baby.",
}

REACTION_DURATIONS = {
    "wake": 3,
    "prompt": 3,
    "tool_success": 3,
    "tool_failure": 4,
    "test_pass": 5,
    "test_fail": 5,
    "care": 3,
    "care_call": 8,
    "care_answered": 4,
    "care_miss": 5,
    "death": 8,
    "rebirth": 6,
}


def now_iso() -> str:
    return to_iso(datetime.now(timezone.utc))


def to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def add_seconds_iso(value: str, seconds: int) -> str:
    parsed = parse_iso(value) or datetime.now(timezone.utc)
    return to_iso(parsed + timedelta(seconds=int(seconds)))


def seconds_until(value: Any, at: datetime | None = None) -> int:
    target = parse_iso(value)
    if target is None:
        return 0
    current = (at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return max(0, int((target - current).total_seconds()))


def format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours >= 24:
        days, hours = divmod(hours, 24)
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def form_for_stage_path(stage: str, path_name: str) -> dict[str, Any]:
    stage_forms = FORM_CATALOG.get(stage, FORM_CATALOG["baby"])
    form = stage_forms.get(path_name) or stage_forms.get("balanced") or stage_forms.get("default") or FORM_CATALOG["baby"]["default"]
    return deepcopy(form)


def known_form_ids() -> set[str]:
    ids = {
        str(form["formId"])
        for stage_forms in FORM_CATALOG.values()
        for form in stage_forms.values()
    }
    ids.update(pet_pack_form_ids(active_pet_pack_id()))
    return {form_id for form_id in ids if form_id}


def dominant_key(points: dict[str, Any], keys: tuple[str, ...]) -> tuple[str, int]:
    normalized = {key: max(0, safe_int(points.get(key))) for key in keys}
    winner = max(keys, key=lambda key: (normalized[key], -keys.index(key)))
    return winner, normalized[winner]


def evolution_profile(state: dict[str, Any]) -> dict[str, Any]:
    return state.setdefault("evolution", deepcopy(DEFAULT_EVOLUTION))


def derived_dw1_metrics(state: dict[str, Any]) -> dict[str, int]:
    """Project Codex Tomogatchi activity into DW1-like raising stats.

    Pet packs keep the original DW1 requirements in their own units. This
    projection gives the local Codex game a way to satisfy those units without
    pretending Codex has the exact PS1 stat system.
    """

    evolution = evolution_profile(state)
    counters = state.get("counters", {})
    stats = state.get("stats", {})
    focus = evolution.get("focusPoints", {})
    training = evolution.get("trainingPoints", {})
    care = evolution.get("carePoints", {})
    care_calls = evolution.get("careCalls", {})
    care_total = sum(safe_int(value) for value in care.values())
    turns = safe_int(counters.get("turns"))
    successful_tools = safe_int(counters.get("successfulTools"))
    xp = safe_int(state.get("xp"))
    builder = safe_int(focus.get("builder"))
    explorer = safe_int(focus.get("explorer"))
    debugger = safe_int(focus.get("debugger"))
    reviewer = safe_int(focus.get("reviewer"))
    feed = safe_int(care.get("feed"))
    rest = safe_int(care.get("rest"))
    play = safe_int(care.get("play"))
    comfort = safe_int(care.get("comfort"))
    mistakes = safe_int(evolution.get("careMistakes"))
    missed_calls = safe_int(care_calls.get("missed"))

    projected = {
        "hp": 500 + xp * 12 + turns * 120 + rest * 180 + feed * 80,
        "mp": 500 + xp * 10 + explorer * 260 + comfort * 160 + play * 60,
        "offense": 50 + builder * 28 + successful_tools * 3 + safe_int(training.get("focus")) * 10,
        "defense": 50 + reviewer * 24 + rest * 20 + safe_int(training.get("testing")) * 15,
        "speed": 50 + explorer * 22 + successful_tools * 2 + play * 12,
        "brains": 50 + debugger * 24 + reviewer * 14 + turns * 4 + safe_int(training.get("testing")) * 20,
        "weight": clamp(10 + feed * 6 + safe_int(stats.get("fullness")) // 8 - play * 2 - safe_int(stats.get("stress")) // 15, 0, 99),
        "happiness": clamp(safe_int(stats.get("mood")) + play * 4 + comfort * 3 - mistakes * 4, -100, 100),
        "discipline": clamp(40 + turns * 4 + reviewer * 4 + debugger * 2 - missed_calls * 8, 0, 100),
        "battles": turns + successful_tools // 3,
        "techniques": clamp(
            safe_int(training.get("focus"))
            + safe_int(training.get("testing"))
            + care_total
            + (builder + explorer + debugger + reviewer) // 2,
            0,
            99,
        ),
    }

    overrides = evolution.get("dw1Stats")
    if isinstance(overrides, dict):
        for key, value in overrides.items():
            if key in DW1_METRIC_KEYS:
                projected[key] = safe_int(value)
    return projected


def evolution_metrics(state: dict[str, Any]) -> dict[str, Any]:
    evolution = evolution_profile(state)
    care_points = evolution.get("carePoints", {})
    focus_points = evolution.get("focusPoints", {})
    care_calls = evolution.get("careCalls", {})
    focus_key, focus_value = dominant_key(focus_points, FOCUS_KEYS)
    return {
        "careMistakes": safe_int(evolution.get("careMistakes")),
        "careTotal": sum(safe_int(value) for value in care_points.values()),
        "carePoints": {key: safe_int(care_points.get(key)) for key in CARE_KINDS},
        "mistakesByKind": {
            key: safe_int(evolution.get("mistakesByKind", {}).get(key))
            for key in MISTAKE_KINDS
        },
        "answeredCalls": safe_int(care_calls.get("answered")),
        "missedCalls": safe_int(care_calls.get("missed")),
        "dominantFocus": focus_key,
        "dominantFocusValue": focus_value,
        "focusPoints": {key: safe_int(focus_points.get(key)) for key in FOCUS_KEYS},
        "trainingPoints": {
            key: safe_int(evolution.get("trainingPoints", {}).get(key))
            for key in TRAINING_KEYS
        },
        "dw1": derived_dw1_metrics(state),
    }


def dw1_bonus_matches(bonus: dict[str, Any], metrics: dict[str, Any]) -> bool:
    dw1 = metrics["dw1"]
    if "happinessMin" in bonus and dw1["happiness"] < safe_int(bonus["happinessMin"]):
        return False
    if "disciplineMin" in bonus and dw1["discipline"] < safe_int(bonus["disciplineMin"]):
        return False
    if "battlesMin" in bonus and dw1["battles"] < safe_int(bonus["battlesMin"]):
        return False
    if "battlesMax" in bonus and dw1["battles"] > safe_int(bonus["battlesMax"]):
        return False
    if "techniquesMin" in bonus and dw1["techniques"] < safe_int(bonus["techniquesMin"]):
        return False
    return True


def dw1_requirement_results(requirement: dict[str, Any], metrics: dict[str, Any]) -> dict[str, bool]:
    dw1 = metrics["dw1"]
    stat_requirements = requirement.get("stats", {})
    stats_match = isinstance(stat_requirements, dict) and bool(stat_requirements)
    if stats_match:
        for key, value in stat_requirements.items():
            normalized_key = str(key).lower()
            if normalized_key in DW1_STAT_KEYS and dw1[normalized_key] < safe_int(value):
                stats_match = False
                break

    weight = requirement.get("weight")
    weight_match = False
    if isinstance(weight, dict):
        minimum = safe_int(weight.get("min"), -10**9)
        maximum = safe_int(weight.get("max"), 10**9)
        weight_match = minimum <= dw1["weight"] <= maximum

    care = requirement.get("careMistakes")
    care_match = False
    if isinstance(care, dict):
        care_match = True
        if "min" in care and metrics["careMistakes"] < safe_int(care["min"]):
            care_match = False
        if "max" in care and metrics["careMistakes"] > safe_int(care["max"]):
            care_match = False

    bonus = requirement.get("bonus")
    bonus_match = False
    if isinstance(bonus, list):
        bonus_match = any(dw1_bonus_matches(item, metrics) for item in bonus if isinstance(item, dict))

    return {
        "stats": stats_match,
        "weight": weight_match,
        "careMistakes": care_match,
        "bonus": bonus_match,
    }


def dw1_requirement_matches(requirement: dict[str, Any], metrics: dict[str, Any]) -> bool:
    groups_required = max(1, safe_int(requirement.get("groupsRequired"), 3))
    results = dw1_requirement_results(requirement, metrics)
    return sum(1 for matched in results.values() if matched) >= groups_required


def requirement_matches(requirement: dict[str, Any], metrics: dict[str, Any]) -> bool:
    dw1_requirement = requirement.get("dw1")
    if isinstance(dw1_requirement, dict) and not dw1_requirement_matches(dw1_requirement, metrics):
        return False

    any_requirements = requirement.get("any")
    if isinstance(any_requirements, list) and any_requirements:
        if not any(requirement_matches(item, metrics) for item in any_requirements if isinstance(item, dict)):
            return False

    if "minCareMistakes" in requirement and metrics["careMistakes"] < safe_int(requirement["minCareMistakes"]):
        return False
    if "maxCareMistakes" in requirement and metrics["careMistakes"] > safe_int(requirement["maxCareMistakes"]):
        return False
    if "minCareTotal" in requirement and metrics["careTotal"] < safe_int(requirement["minCareTotal"]):
        return False
    if "minAnsweredCalls" in requirement and metrics["answeredCalls"] < safe_int(requirement["minAnsweredCalls"]):
        return False
    if "minMissedCalls" in requirement and metrics["missedCalls"] < safe_int(requirement["minMissedCalls"]):
        return False
    if "dominantFocus" in requirement and metrics["dominantFocus"] != str(requirement["dominantFocus"]):
        return False
    if "minDominantFocus" in requirement and metrics["dominantFocusValue"] < safe_int(requirement["minDominantFocus"]):
        return False

    min_care_kinds = requirement.get("minCareKinds")
    if isinstance(min_care_kinds, dict):
        for key, value in min_care_kinds.items():
            if key in CARE_KINDS and metrics["carePoints"].get(key, 0) < safe_int(value):
                return False

    min_mistakes = requirement.get("minMistakesByKind")
    if isinstance(min_mistakes, dict):
        for key, value in min_mistakes.items():
            if key in MISTAKE_KINDS and metrics["mistakesByKind"].get(key, 0) < safe_int(value):
                return False

    min_focus = requirement.get("minFocus")
    if isinstance(min_focus, dict):
        for key, value in min_focus.items():
            if key in FOCUS_KEYS and metrics["focusPoints"].get(key, 0) < safe_int(value):
                return False

    min_training = requirement.get("minTraining")
    if isinstance(min_training, dict):
        for key, value in min_training.items():
            if key in TRAINING_KEYS and metrics["trainingPoints"].get(key, 0) < safe_int(value):
                return False

    return True


def evolution_path_for_state(state: dict[str, Any], stage: str | None = None) -> tuple[str, str]:
    target_stage = stage if stage in {"teen", "adult"} else "teen"
    metrics = evolution_metrics(state)
    for requirement in EVOLUTION_REQUIREMENTS.get(target_stage, EVOLUTION_REQUIREMENTS["teen"]):
        if requirement_matches(requirement, metrics):
            return str(requirement["path"]), str(requirement["reason"])

    return "balanced", "balanced growth"


def legacy_evolution_path_for_state(state: dict[str, Any]) -> tuple[str, str]:
    evolution = evolution_profile(state)
    mistakes = safe_int(evolution.get("careMistakes"))
    care_total = sum(safe_int(value) for value in evolution.get("carePoints", {}).values())
    focus_key, focus_value = dominant_key(evolution.get("focusPoints", {}), FOCUS_KEYS)
    stress_mistakes = safe_int(evolution.get("mistakesByKind", {}).get("stress"))
    overwork_mistakes = safe_int(evolution.get("mistakesByKind", {}).get("overwork"))

    if mistakes >= 5 or stress_mistakes >= 3 or overwork_mistakes >= 3:
        return "wild", "care mistakes shaped a wild path"
    if care_total >= 6 and mistakes <= 1:
        return "partner", "high care with few mistakes"
    if focus_value >= 3:
        return focus_key, f"{focus_key} focus led the generation"
    return "balanced", "balanced growth"


def pack_forms_for_stage(manifest: dict[str, Any], stage: str) -> list[dict[str, Any]]:
    forms = manifest.get("forms", {})
    if not isinstance(forms, dict):
        return []
    stage_forms = forms.get(stage, [])
    if not isinstance(stage_forms, list):
        return []
    return [form for form in stage_forms if isinstance(form, dict)]


def pack_form_by_id(manifest: dict[str, Any], stage: str, form_id: str) -> dict[str, Any] | None:
    for form in pack_forms_for_stage(manifest, stage):
        if str(form.get("id")) == form_id:
            return form
    return None


def selected_pack_baby_form(manifest: dict[str, Any]) -> dict[str, Any] | None:
    starter_id = active_starter_form_id()
    if starter_id:
        starter = pack_form_by_id(manifest, "baby", starter_id)
        if starter is not None:
            return starter
    return pack_default_form(pack_forms_for_stage(manifest, "baby"))


def pack_form_to_catalog_form(stage: str, form: dict[str, Any], reason: str | None = None) -> dict[str, Any]:
    form_id = str(form.get("id") or f"{stage}-form")
    return {
        "formId": form_id,
        "formName": str(form.get("name") or form.get("displayName") or form_id),
        "path": str(form.get("path") or form_id),
        "assetStage": stage,
        "reason": reason or str(form.get("reason") or "pet-pack form"),
    }


def pack_form_matches_from(form: dict[str, Any], previous_form_id: str) -> bool:
    evolves_from = form.get("evolvesFrom")
    if not isinstance(evolves_from, list) or not evolves_from:
        return True
    return previous_form_id in {str(item) for item in evolves_from}


def pack_default_form(forms: list[dict[str, Any]]) -> dict[str, Any] | None:
    for form in forms:
        if form.get("default") is True:
            return form
    return forms[0] if forms else None


def choose_pack_form_for_stage(state: dict[str, Any], stage: str) -> dict[str, Any] | None:
    try:
        _root, manifest = load_installed_pet_pack(active_pet_pack_id())
    except SystemExit:
        return None
    forms = pack_forms_for_stage(manifest, stage)
    if not forms:
        return None
    if stage == "baby":
        default = selected_pack_baby_form(manifest)
        return pack_form_to_catalog_form(stage, default, "starter form") if default else None

    metrics = evolution_metrics(state)
    previous_form_id = str(evolution_profile(state).get("formId", ""))
    fallback = None
    for form in forms:
        if not pack_form_matches_from(form, previous_form_id):
            continue
        if form.get("default") is True:
            fallback = form
        requirement = form.get("requirements")
        if isinstance(requirement, dict) and requirement_matches(requirement, metrics):
            reason = str(form.get("reason") or requirement.get("reason") or "pet-pack requirements matched")
            return pack_form_to_catalog_form(stage, form, reason)

    if fallback is None:
        fallback = pack_default_form([form for form in forms if pack_form_matches_from(form, previous_form_id)])
    if fallback is None:
        fallback = pack_default_form(forms)
    return pack_form_to_catalog_form(stage, fallback, str(fallback.get("reason") or "pet-pack fallback")) if fallback else None


def choose_form_for_stage(state: dict[str, Any], stage: str) -> dict[str, Any]:
    pack_form = choose_pack_form_for_stage(state, stage)
    if pack_form is not None:
        return pack_form
    if stage == "baby":
        return form_for_stage_path("baby", "default")
    path_name, reason = evolution_path_for_state(state, stage)
    form = form_for_stage_path(stage, path_name)
    form["reason"] = reason
    return form


def apply_form(state: dict[str, Any], stage: str, form: dict[str, Any], *, at: str | None = None) -> None:
    evolution = evolution_profile(state)
    evolution.update(
        {
            "formId": form["formId"],
            "formName": form["formName"],
            "path": form["path"],
            "assetStage": form["assetStage"],
            "reason": form["reason"],
            "lastEvaluation": {
                "stage": stage,
                "path": form["path"],
                "formId": form["formId"],
                "reason": form["reason"],
            },
        }
    )
    entry = {
        "stage": stage,
        "formId": form["formId"],
        "formName": form["formName"],
        "path": form["path"],
        "reason": form["reason"],
        "at": at or now_iso(),
    }
    lineage = evolution.setdefault("lineage", [])
    if not lineage or lineage[-1].get("formId") != form["formId"]:
        lineage.append(entry)
        del lineage[:-20]
    state.setdefault("assets", {})["currentFormId"] = form["formId"]
    state["assets"]["currentFormName"] = form["formName"]
    state["assets"]["currentPath"] = form["path"]


def today_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(value)))


def codex_home() -> Path:
    raw = os.environ.get("CODEX_HOME")
    if raw:
        return Path(raw).expanduser().resolve()
    return (Path.home() / ".codex").resolve()


def state_path() -> Path:
    override = os.environ.get("CODEX_TOMOGATCHI_STATE")
    if override:
        return Path(override).expanduser().resolve()
    return codex_home() / "codex-tomogatchi" / "state.json"


def codex_config_path() -> Path:
    override = os.environ.get("CODEX_TOMOGATCHI_CONFIG")
    if override:
        return Path(override).expanduser().resolve()
    return codex_home() / "config.toml"


def legacy_pet_dir() -> Path:
    override = os.environ.get("CODEX_TOMOGATCHI_PET_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return codex_home() / "pets" / PET_ID


def pet_packs_dir() -> Path:
    override = os.environ.get("CODEX_TOMOGATCHI_PET_PACKS_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return codex_home() / "codex-tomogatchi" / "pet-packs"


def backups_dir() -> Path:
    override = os.environ.get("CODEX_TOMOGATCHI_BACKUPS_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return codex_home() / "codex-tomogatchi" / "backups"


def exports_dir() -> Path:
    override = os.environ.get("CODEX_TOMOGATCHI_EXPORTS_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return codex_home() / "codex-tomogatchi" / "exports"


def overlay_log_path() -> Path:
    return codex_home() / "codex-tomogatchi" / "overlay.log"


def validate_pet_pack_id(pack_id: Any) -> str:
    candidate = str(pack_id or "").strip().lower()
    if not PET_PACK_ID_RE.fullmatch(candidate):
        raise SystemExit(
            "Pet pack id must be 1-64 lowercase letters, numbers, dots, underscores, or hyphens, "
            "and must start with a letter or number."
        )
    if candidate in {".", ".."}:
        raise SystemExit("Pet pack id is reserved.")
    return candidate


def builtin_pack_manifest() -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "id": BUILTIN_PACK_ID,
        "name": "Sparkbit Line",
        "author": "Codex Tomogatchi",
        "description": "The bundled original Sparkbit, Byteclaw, and Coremaw evolution line.",
        "stages": {stage: str(ASSET_ROOT / stage) for stage in STAGES},
    }


def active_pet_pack_id() -> str:
    settings = load_settings()
    try:
        return validate_pet_pack_id(settings.get("pets", {}).get("activePack", BUILTIN_PACK_ID))
    except SystemExit:
        return BUILTIN_PACK_ID


def active_starter_form_id() -> str:
    settings = load_settings()
    raw = settings.get("pets", {}).get("starterForm", "")
    if not raw:
        return ""
    try:
        return validate_pet_pack_id(raw)
    except SystemExit:
        return ""


def stage_pet_id(stage: str) -> str:
    if stage not in STAGES:
        raise SystemExit(f"Unknown stage '{stage}'. Expected one of: {', '.join(STAGES)}")
    return f"{PET_ID}-{stage}"


def selected_avatar_id(stage: str) -> str:
    return f"custom:{stage_pet_id(stage)}"


def active_pet_dir(stage: str = "baby") -> Path:
    base = legacy_pet_dir()
    stage_id = stage_pet_id(stage)
    if base.name == stage_id:
        return base
    return base.parent / stage_id


def sessions_dir() -> Path:
    override = os.environ.get("CODEX_TOMOGATCHI_SESSIONS_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return codex_home() / "sessions"


def log_key(path: Path) -> str:
    normalized = str(path.expanduser().resolve()).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]


def default_state() -> dict[str, Any]:
    stamp = now_iso()
    stage = "baby"
    pet_dir = active_pet_dir(stage)
    lifecycle = deepcopy(DEFAULT_LIFECYCLE)
    lifecycle.update(
        {
            "lastInteractionAt": stamp,
            "deathDueAt": add_seconds_iso(stamp, NEGLECT_DEATH_SECONDS),
            "rebornAt": stamp,
        }
    )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "stage": stage,
        "xp": 0,
        "level": 1,
        "createdAt": stamp,
        "updatedAt": stamp,
        "stats": deepcopy(DEFAULT_STATS),
        "counters": deepcopy(DEFAULT_COUNTERS),
        "branchSignals": deepcopy(DEFAULT_BRANCH_SIGNALS),
        "assets": {
            "currentStage": stage,
            "activePetPack": BUILTIN_PACK_ID,
            "activePetPackName": builtin_pack_manifest()["name"],
            "activePetId": stage_pet_id(stage),
            "installedPetPath": str(pet_dir),
            "selectedAvatarId": selected_avatar_id(stage),
        },
        "daily": {
            "date": today_key(),
            "xpAwarded": 0,
            "careXpAwarded": 0,
            "careMistakesAwarded": 0,
            "eventCounts": {},
        },
        "ingest": deepcopy(DEFAULT_INGEST),
        "turnState": deepcopy(DEFAULT_TURN_STATE),
        "lifecycle": lifecycle,
        "reaction": deepcopy(DEFAULT_REACTION),
        "careCall": deepcopy(DEFAULT_CARE_CALL),
        "evolution": deepcopy(DEFAULT_EVOLUTION),
    }


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def settings_path() -> Path:
    override = os.environ.get("CODEX_TOMOGATCHI_SETTINGS")
    if override:
        return Path(override).expanduser().resolve()
    return codex_home() / "codex-tomogatchi" / "settings.json"


def merge_settings(raw: Any) -> dict[str, Any]:
    settings = deepcopy(DEFAULT_SETTINGS)
    if not isinstance(raw, dict):
        return settings
    for section, values in raw.items():
        if section not in settings or not isinstance(values, dict):
            continue
        for key, value in values.items():
            if key in settings[section]:
                settings[section][key] = value

    if settings["xp"].get("pace") not in {"slow", "normal", "fast"}:
        settings["xp"]["pace"] = "normal"
    if settings["care"].get("callStrictness") not in {"relaxed", "normal", "strict"}:
        settings["care"]["callStrictness"] = "normal"
    settings["lifecycle"]["deathEnabled"] = bool(settings["lifecycle"].get("deathEnabled", True))
    settings["overlay"]["alwaysOnTop"] = bool(settings["overlay"].get("alwaysOnTop", True))
    settings["overlay"]["startMode"] = "full" if settings["overlay"].get("startMode") == "full" else "compact"
    settings["overlay"]["startMinimized"] = bool(settings["overlay"].get("startMinimized", False))
    try:
        settings["pets"]["activePack"] = validate_pet_pack_id(settings["pets"].get("activePack", BUILTIN_PACK_ID))
    except SystemExit:
        settings["pets"]["activePack"] = BUILTIN_PACK_ID
    raw_starter = settings["pets"].get("starterForm", "")
    if raw_starter:
        try:
            settings["pets"]["starterForm"] = validate_pet_pack_id(raw_starter)
        except SystemExit:
            settings["pets"]["starterForm"] = ""
    else:
        settings["pets"]["starterForm"] = ""
    return settings


def load_settings() -> dict[str, Any]:
    path = settings_path()
    if not path.exists():
        return deepcopy(DEFAULT_SETTINGS)
    try:
        return merge_settings(json.loads(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Settings file is not valid JSON: {path} ({exc})") from exc


def save_settings(settings: dict[str, Any]) -> None:
    settings = merge_settings(settings)
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps(settings, indent=2, sort_keys=True) + "\n")


def xp_pace() -> str:
    return str(load_settings()["xp"]["pace"])


def effective_xp(amount: int) -> int:
    amount = max(0, int(amount))
    if amount == 0:
        return 0
    multipliers = {"slow": 0.65, "normal": 1.0, "fast": 1.45}
    return max(1, int(round(amount * multipliers.get(xp_pace(), 1.0))))


def daily_xp_cap() -> int:
    return {"slow": 60, "normal": DAILY_XP_CAP, "fast": 140}.get(xp_pace(), DAILY_XP_CAP)


def lifecycle_death_enabled() -> bool:
    return bool(load_settings()["lifecycle"]["deathEnabled"])


def care_call_policy() -> dict[str, int]:
    strictness = str(load_settings()["care"]["callStrictness"])
    if strictness == "relaxed":
        return {
            "responseSeconds": 60 * 60,
            "cooldownSeconds": 75 * 60,
            "statThreshold": 30,
            "urgentThreshold": 50,
        }
    if strictness == "strict":
        return {
            "responseSeconds": 20 * 60,
            "cooldownSeconds": 30 * 60,
            "statThreshold": 55,
            "urgentThreshold": 25,
        }
    return {
        "responseSeconds": CARE_CALL_RESPONSE_SECONDS,
        "cooldownSeconds": CARE_CALL_COOLDOWN_SECONDS,
        "statThreshold": CARE_CALL_STAT_THRESHOLD,
        "urgentThreshold": CARE_CALL_URGENT_THRESHOLD,
    }


def parse_setting_value(raw: str) -> Any:
    lowered = raw.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def set_nested_setting(settings: dict[str, Any], dotted_key: str, value: Any) -> dict[str, Any]:
    parts = dotted_key.split(".")
    if len(parts) != 2:
        raise SystemExit("Settings keys use section.key form, for example xp.pace or overlay.startMode.")
    section, key = parts
    if section not in DEFAULT_SETTINGS or key not in DEFAULT_SETTINGS[section]:
        raise SystemExit(f"Unknown setting '{dotted_key}'.")
    settings.setdefault(section, {})[key] = value
    return merge_settings(settings)


def merge_defaults(state: dict[str, Any]) -> dict[str, Any]:
    merged = default_state()
    nested_keys = {
        "stats",
        "counters",
        "branchSignals",
        "assets",
        "daily",
        "ingest",
        "turnState",
        "lifecycle",
        "reaction",
        "careCall",
        "evolution",
    }
    merged.update({key: value for key, value in state.items() if key not in nested_keys})

    for key, value in state.get("stats", {}).items():
        if key in DEFAULT_STATS:
            merged["stats"][key] = clamp(value)

    for key, value in state.get("counters", {}).items():
        if key in DEFAULT_COUNTERS:
            merged["counters"][key] = max(0, int(value))

    for key, value in state.get("branchSignals", {}).items():
        if key in DEFAULT_BRANCH_SIGNALS:
            merged["branchSignals"][key] = max(0, int(value))

    merged["assets"].update(state.get("assets", {}))
    merged["daily"].update(state.get("daily", {}))
    if merged["daily"].get("date") != today_key():
        merged["daily"] = {
            "date": today_key(),
            "xpAwarded": 0,
            "careXpAwarded": 0,
            "careMistakesAwarded": 0,
            "eventCounts": {},
        }
    else:
        merged["daily"]["xpAwarded"] = min(daily_xp_cap(), max(0, safe_int(merged["daily"].get("xpAwarded"))))
        merged["daily"]["careXpAwarded"] = min(
            CARE_XP_DAILY_CAP,
            max(0, safe_int(merged["daily"].get("careXpAwarded"))),
        )
        merged["daily"]["careMistakesAwarded"] = min(
            CARE_MISTAKE_DAILY_CAP,
            max(0, safe_int(merged["daily"].get("careMistakesAwarded"))),
        )
        if not isinstance(merged["daily"].get("eventCounts"), dict):
            merged["daily"]["eventCounts"] = {}

    turn_state = state.get("turnState", {})
    if isinstance(turn_state, dict):
        for key, value in turn_state.items():
            if key in DEFAULT_TURN_STATE:
                merged["turnState"][key] = max(0, safe_int(value))

    lifecycle = state.get("lifecycle", {})
    if isinstance(lifecycle, dict):
        for key, value in lifecycle.items():
            if key in DEFAULT_LIFECYCLE:
                merged["lifecycle"][key] = value
    if merged["lifecycle"].get("status") not in {"alive", "dead"}:
        merged["lifecycle"]["status"] = "alive"
    for key in ("lastInteractionAt", "deathDueAt", "diedAt", "rebirthDueAt", "rebornAt"):
        if merged["lifecycle"].get(key) is not None and parse_iso(merged["lifecycle"].get(key)) is None:
            merged["lifecycle"][key] = None
    if not merged["lifecycle"].get("lastInteractionAt"):
        merged["lifecycle"]["lastInteractionAt"] = str(merged.get("updatedAt") or merged.get("createdAt") or now_iso())
    if not merged["lifecycle"].get("deathDueAt"):
        merged["lifecycle"]["deathDueAt"] = add_seconds_iso(merged["lifecycle"]["lastInteractionAt"], NEGLECT_DEATH_SECONDS)
    merged["lifecycle"]["deaths"] = max(0, safe_int(merged["lifecycle"].get("deaths")))
    merged["lifecycle"]["rebirths"] = max(0, safe_int(merged["lifecycle"].get("rebirths")))

    reaction = state.get("reaction", {})
    if isinstance(reaction, dict):
        for key, value in reaction.items():
            if key in DEFAULT_REACTION:
                merged["reaction"][key] = value
    merged["reaction"]["sequence"] = max(0, safe_int(merged["reaction"].get("sequence")))
    if str(merged["reaction"].get("kind", "")) not in REACTION_MESSAGES:
        merged["reaction"].update({key: deepcopy(value) for key, value in DEFAULT_REACTION.items() if key != "sequence"})
    for key in ("at", "expiresAt"):
        if merged["reaction"].get(key) and parse_iso(merged["reaction"].get(key)) is None:
            merged["reaction"][key] = ""

    care_call = state.get("careCall", {})
    if isinstance(care_call, dict):
        for key, value in care_call.items():
            if key in DEFAULT_CARE_CALL:
                merged["careCall"][key] = value
    merged["careCall"]["sequence"] = max(0, safe_int(merged["careCall"].get("sequence")))
    merged["careCall"]["active"] = bool(merged["careCall"].get("active"))
    if merged["careCall"].get("kind") not in CARE_KINDS:
        merged["careCall"]["active"] = False
        merged["careCall"]["kind"] = ""
    if str(merged["careCall"].get("lastStatus", "none")) not in {"none", "active", "answered", "missed"}:
        merged["careCall"]["lastStatus"] = "none"
    for key in ("createdAt", "dueAt", "lastClosedAt", "answeredAt", "missedAt"):
        if merged["careCall"].get(key) is not None and parse_iso(merged["careCall"].get(key)) is None:
            merged["careCall"][key] = None
    if not merged["careCall"]["active"]:
        merged["careCall"]["kind"] = ""
        merged["careCall"]["reason"] = ""
        merged["careCall"]["id"] = ""
        merged["careCall"]["createdAt"] = None
        merged["careCall"]["dueAt"] = None

    evolution = state.get("evolution", {})
    if isinstance(evolution, dict):
        for key, value in evolution.items():
            if key in DEFAULT_EVOLUTION and key not in {
                "mistakesByKind",
                "carePoints",
                "careCalls",
                "focusPoints",
                "trainingPoints",
                "lineage",
                "lastEvaluation",
            }:
                merged["evolution"][key] = value
        for key, value in evolution.get("mistakesByKind", {}).items():
            if key in MISTAKE_KINDS:
                merged["evolution"]["mistakesByKind"][key] = max(0, safe_int(value))
        for key, value in evolution.get("carePoints", {}).items():
            if key in CARE_KINDS:
                merged["evolution"]["carePoints"][key] = max(0, safe_int(value))
        care_calls = evolution.get("careCalls", {})
        if isinstance(care_calls, dict):
            merged["evolution"]["careCalls"]["answered"] = max(0, safe_int(care_calls.get("answered")))
            merged["evolution"]["careCalls"]["missed"] = max(0, safe_int(care_calls.get("missed")))
            for key, value in care_calls.get("byKind", {}).items():
                if key in CARE_KINDS:
                    merged["evolution"]["careCalls"]["byKind"][key] = max(0, safe_int(value))
            for key, value in care_calls.get("missedByKind", {}).items():
                if key in CARE_KINDS:
                    merged["evolution"]["careCalls"]["missedByKind"][key] = max(0, safe_int(value))
        for key, value in evolution.get("focusPoints", {}).items():
            if key in FOCUS_KEYS:
                merged["evolution"]["focusPoints"][key] = max(0, safe_int(value))
        for key, value in evolution.get("trainingPoints", {}).items():
            if key in TRAINING_KEYS:
                merged["evolution"]["trainingPoints"][key] = max(0, safe_int(value))
        dw1_stats = evolution.get("dw1Stats")
        if isinstance(dw1_stats, dict):
            merged["evolution"]["dw1Stats"] = {
                key: safe_int(value)
                for key, value in dw1_stats.items()
                if key in DW1_METRIC_KEYS
            }
        lineage = evolution.get("lineage")
        if isinstance(lineage, list):
            merged["evolution"]["lineage"] = [item for item in lineage if isinstance(item, dict)][:20]
        last_evaluation = evolution.get("lastEvaluation")
        if isinstance(last_evaluation, dict):
            merged["evolution"]["lastEvaluation"].update(
                {key: value for key, value in last_evaluation.items() if key in merged["evolution"]["lastEvaluation"]}
            )
    merged["evolution"]["generation"] = max(1, safe_int(merged["evolution"].get("generation"), 1))
    merged["evolution"]["careMistakes"] = max(0, safe_int(merged["evolution"].get("careMistakes")))
    if str(merged["evolution"].get("assetStage")) not in STAGES:
        merged["evolution"]["assetStage"] = merged.get("stage", "baby")
    active_pack_ids = pet_pack_form_ids(active_pet_pack_id())
    current_form_id = str(merged["evolution"].get("formId", ""))
    if current_form_id not in known_form_ids() or (active_pack_ids and current_form_id not in active_pack_ids):
        form = choose_form_for_stage(merged, str(merged.get("stage", "baby")))
        merged["evolution"].update(form)
        merged["evolution"]["lastEvaluation"].update(
            {
                "stage": merged.get("stage", "baby"),
                "path": form["path"],
                "formId": form["formId"],
                "reason": form["reason"],
            }
        )
    if not merged["evolution"].get("formId"):
        form = choose_form_for_stage(merged, str(merged.get("stage", "baby")))
        merged["evolution"].update(form)

    ingest = state.get("ingest", {})
    if isinstance(ingest, dict):
        session_logs = ingest.get("sessionLogs", {})
        if isinstance(session_logs, dict):
            for key, value in session_logs.items():
                if not isinstance(value, dict):
                    continue
                merged["ingest"]["sessionLogs"][str(key)] = {
                    "offset": max(0, safe_int(value.get("offset"))),
                    "size": max(0, safe_int(value.get("size"))),
                    "mtime": max(0, safe_int(value.get("mtime"))),
                    "sessionStarted": bool(value.get("sessionStarted", False)),
                }
        pending_tools = ingest.get("pendingTools", {})
        if isinstance(pending_tools, dict):
            for key, value in pending_tools.items():
                if isinstance(value, str):
                    merged["ingest"]["pendingTools"][str(key)] = value

    if merged.get("stage") not in STAGES:
        merged["stage"] = "baby"
    merged["xp"] = max(0, int(merged.get("xp", 0)))
    merged["level"] = level_for_xp(merged["xp"])
    merged["schemaVersion"] = SCHEMA_VERSION
    stage = merged["stage"]
    if merged["evolution"].get("assetStage") != stage:
        form = choose_form_for_stage(merged, stage)
        merged["evolution"].update(form)
    merged["assets"]["currentFormId"] = merged["evolution"]["formId"]
    merged["assets"]["currentFormName"] = merged["evolution"]["formName"]
    merged["assets"]["currentPath"] = merged["evolution"]["path"]
    lineage = merged["evolution"].setdefault("lineage", [])
    if not lineage or lineage[-1].get("formId") != merged["evolution"]["formId"]:
        lineage.append(
            {
                "stage": stage,
                "formId": merged["evolution"]["formId"],
                "formName": merged["evolution"]["formName"],
                "path": merged["evolution"]["path"],
                "reason": merged["evolution"]["reason"],
                "at": str(merged.get("updatedAt") or merged.get("createdAt") or now_iso()),
            }
        )
        del lineage[:-20]
    merged["assets"]["currentStage"] = stage
    pack_id = active_pet_pack_id()
    merged["assets"]["activePetPack"] = pack_id
    merged["assets"]["activePetPackName"] = pet_pack_display_name(pack_id)
    merged["assets"]["activePetId"] = stage_pet_id(stage)
    merged["assets"]["installedPetPath"] = str(active_pet_dir(stage))
    merged["assets"]["selectedAvatarId"] = selected_avatar_id(stage)
    merged["assets"].pop("legacyInstalledPetPath", None)
    return merged


def load_state() -> dict[str, Any]:
    path = state_path()
    if not path.exists():
        return merge_defaults(default_state())
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"State file is not valid JSON: {path} ({exc})") from exc
    if not isinstance(raw, dict):
        raise SystemExit(f"State file must contain a JSON object: {path}")
    return merge_defaults(raw)


def save_state(state: dict[str, Any]) -> None:
    state = merge_defaults(state)
    state["updatedAt"] = now_iso()
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix="state-", suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            json.dump(state, tmp, indent=2, sort_keys=True)
            tmp.write("\n")
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as tmp:
            tmp.write(text)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def set_toml_string(text: str, section: str, key: str, value: str) -> str:
    lines = text.splitlines()
    section_header = f"[{section}]"
    assignment = f"{key} = {json.dumps(value)}"
    section_start: int | None = None
    section_end = len(lines)

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == section_header:
            section_start = index
            section_end = len(lines)
            continue
        if section_start is not None and index > section_start and stripped.startswith("[") and stripped.endswith("]"):
            section_end = index
            break

    if section_start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend([section_header, assignment])
        return "\n".join(lines) + "\n"

    key_re = re.compile(rf"^(\s*){re.escape(key)}\s*=")
    for index in range(section_start + 1, section_end):
        match = key_re.match(lines[index])
        if match:
            lines[index] = f"{match.group(1)}{assignment}"
            return "\n".join(lines) + "\n"

    lines.insert(section_end, assignment)
    return "\n".join(lines) + "\n"


def select_codex_avatar(stage: str) -> Path | None:
    if os.environ.get("CODEX_TOMOGATCHI_SELECT_AVATAR", "1").lower() in {"0", "false", "no", "off"}:
        return None
    path = codex_config_path()
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    updated = set_toml_string(text, "desktop", "selected-avatar-id", selected_avatar_id(stage))
    if updated != text:
        atomic_write_text(path, updated)
    return path


def level_for_xp(xp: int) -> int:
    return max(1, int(xp) // 50 + 1)


def lifecycle_status(state: dict[str, Any]) -> str:
    lifecycle = state.setdefault("lifecycle", deepcopy(DEFAULT_LIFECYCLE))
    return str(lifecycle.get("status", "alive"))


def is_alive(state: dict[str, Any]) -> bool:
    return lifecycle_status(state) == "alive"


def mark_interaction(state: dict[str, Any], at: datetime | None = None) -> None:
    stamp = to_iso(at or datetime.now(timezone.utc))
    lifecycle = state.setdefault("lifecycle", deepcopy(DEFAULT_LIFECYCLE))
    lifecycle["status"] = "alive"
    lifecycle["lastInteractionAt"] = stamp
    lifecycle["deathDueAt"] = add_seconds_iso(stamp, NEGLECT_DEATH_SECONDS)
    lifecycle["diedAt"] = None
    lifecycle["rebirthDueAt"] = None


def set_reaction(
    state: dict[str, Any],
    kind: str,
    *,
    message: str | None = None,
    at: datetime | None = None,
    duration_seconds: int | None = None,
) -> None:
    if kind not in REACTION_MESSAGES:
        return
    stamp = to_iso(at or datetime.now(timezone.utc))
    reaction = state.setdefault("reaction", deepcopy(DEFAULT_REACTION))
    sequence = safe_int(reaction.get("sequence")) + 1
    duration = duration_seconds if duration_seconds is not None else REACTION_DURATIONS[kind]
    reaction.update(
        {
            "sequence": sequence,
            "id": f"{sequence}:{kind}:{stamp}",
            "kind": kind,
            "message": message or REACTION_MESSAGES[kind],
            "at": stamp,
            "expiresAt": add_seconds_iso(stamp, duration),
        }
    )


def reset_growth_for_rebirth(state: dict[str, Any], at: datetime) -> None:
    stage = "baby"
    stamp = to_iso(at)
    previous_generation = safe_int(state.get("evolution", {}).get("generation"), 1)
    evolution = deepcopy(DEFAULT_EVOLUTION)
    evolution["generation"] = previous_generation + 1
    evolution["lineage"] = []
    state["stage"] = stage
    state["xp"] = 0
    state["level"] = 1
    state["stats"] = deepcopy(DEFAULT_STATS)
    state["turnState"] = deepcopy(DEFAULT_TURN_STATE)
    state["careCall"] = deepcopy(DEFAULT_CARE_CALL)
    state["evolution"] = evolution
    apply_form(state, stage, choose_form_for_stage(state, stage), at=stamp)
    state.setdefault("assets", {})["currentStage"] = stage
    state["assets"]["activePetId"] = stage_pet_id(stage)
    state["assets"]["installedPetPath"] = str(active_pet_dir(stage))
    state["assets"]["selectedAvatarId"] = selected_avatar_id(stage)
    lifecycle = state.setdefault("lifecycle", deepcopy(DEFAULT_LIFECYCLE))
    lifecycle["status"] = "alive"
    lifecycle["lastInteractionAt"] = stamp
    lifecycle["deathDueAt"] = add_seconds_iso(stamp, NEGLECT_DEATH_SECONDS)
    lifecycle["diedAt"] = None
    lifecycle["rebirthDueAt"] = None
    lifecycle["rebornAt"] = stamp
    lifecycle["rebirths"] = max(0, safe_int(lifecycle.get("rebirths"))) + 1
    set_reaction(state, "rebirth", at=at)


def apply_lifecycle(state: dict[str, Any], at: datetime | None = None) -> str | None:
    at = (at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    lifecycle = state.setdefault("lifecycle", deepcopy(DEFAULT_LIFECYCLE))
    if not lifecycle_death_enabled():
        lifecycle["status"] = "alive"
        lifecycle["diedAt"] = None
        lifecycle["rebirthDueAt"] = None
        if not lifecycle.get("lastInteractionAt"):
            lifecycle["lastInteractionAt"] = to_iso(at)
        lifecycle["deathDueAt"] = ""
        return None
    status = lifecycle_status(state)

    if status == "dead":
        rebirth_due = parse_iso(lifecycle.get("rebirthDueAt"))
        if rebirth_due is not None and at >= rebirth_due:
            reset_growth_for_rebirth(state, at)
            return "reborn"
        return None

    last_interaction = parse_iso(lifecycle.get("lastInteractionAt")) or parse_iso(state.get("updatedAt")) or at
    death_due = last_interaction + timedelta(seconds=NEGLECT_DEATH_SECONDS)
    rebirth_due = death_due + timedelta(seconds=REBIRTH_SECONDS)
    lifecycle["deathDueAt"] = to_iso(death_due)

    if at >= rebirth_due:
        lifecycle["deaths"] = max(0, safe_int(lifecycle.get("deaths"))) + 1
        lifecycle["diedAt"] = to_iso(death_due)
        reset_growth_for_rebirth(state, at)
        return "reborn"

    if at >= death_due:
        lifecycle["status"] = "dead"
        lifecycle["diedAt"] = to_iso(death_due)
        lifecycle["rebirthDueAt"] = to_iso(rebirth_due)
        lifecycle["deathDueAt"] = to_iso(death_due)
        lifecycle["deaths"] = max(0, safe_int(lifecycle.get("deaths"))) + 1
        state["stats"] = {"fullness": 0, "energy": 0, "mood": 0, "stress": 100}
        clear_care_call(state, "missed", at)
        add_care_mistake(state, "death")
        set_reaction(state, "death", at=at)
        return "died"

    return None


def ensure_daily(state: dict[str, Any]) -> dict[str, Any]:
    daily = state.setdefault(
        "daily",
        {"date": today_key(), "xpAwarded": 0, "careXpAwarded": 0, "careMistakesAwarded": 0, "eventCounts": {}},
    )
    if daily.get("date") != today_key():
        daily.clear()
        daily.update(
            {"date": today_key(), "xpAwarded": 0, "careXpAwarded": 0, "careMistakesAwarded": 0, "eventCounts": {}}
        )
    else:
        daily.setdefault("xpAwarded", 0)
        daily.setdefault("careXpAwarded", 0)
        daily.setdefault("careMistakesAwarded", 0)
        daily.setdefault("eventCounts", {})
    return daily


def add_xp(state: dict[str, Any], amount: int, *, capped: bool = True) -> int:
    amount = max(0, int(amount))
    if amount == 0:
        return 0
    daily = ensure_daily(state)
    award = amount
    if capped:
        remaining = max(0, daily_xp_cap() - int(daily.get("xpAwarded", 0)))
        award = min(amount, remaining)
    if award:
        state["xp"] = int(state.get("xp", 0)) + award
        daily["xpAwarded"] = int(daily.get("xpAwarded", 0)) + award
        state["level"] = level_for_xp(state["xp"])
    return award


def add_care_xp(state: dict[str, Any], amount: int) -> int:
    daily = ensure_daily(state)
    remaining = max(0, CARE_XP_DAILY_CAP - int(daily.get("careXpAwarded", 0)))
    requested = min(max(0, int(amount)), remaining)
    awarded = add_xp(state, requested, capped=True)
    daily["careXpAwarded"] = int(daily.get("careXpAwarded", 0)) + awarded
    return awarded


def add_focus_point(state: dict[str, Any], focus: str, amount: int = 1) -> None:
    if focus not in FOCUS_KEYS:
        return
    evolution = evolution_profile(state)
    evolution["focusPoints"][focus] = max(0, safe_int(evolution["focusPoints"].get(focus))) + max(0, int(amount))


def add_training_point(state: dict[str, Any], kind: str, amount: int = 1) -> None:
    if kind not in TRAINING_KEYS:
        return
    evolution = evolution_profile(state)
    evolution["trainingPoints"][kind] = max(0, safe_int(evolution["trainingPoints"].get(kind))) + max(0, int(amount))


def add_care_point(state: dict[str, Any], care: str, amount: int = 1) -> None:
    if care not in CARE_KINDS:
        return
    evolution = evolution_profile(state)
    evolution["carePoints"][care] = max(0, safe_int(evolution["carePoints"].get(care))) + max(0, int(amount))
    evolution["lastCareAt"] = now_iso()
    add_training_point(state, "care", amount)


def add_care_mistake(state: dict[str, Any], kind: str, amount: int = 1) -> int:
    if kind not in MISTAKE_KINDS:
        return 0
    daily = ensure_daily(state)
    event_counts = daily.setdefault("eventCounts", {})
    daily_key = f"careMistake:{kind}"
    if int(event_counts.get(daily_key, 0)) > 0:
        return 0
    remaining = max(0, CARE_MISTAKE_DAILY_CAP - safe_int(daily.get("careMistakesAwarded")))
    awarded = min(max(0, int(amount)), remaining)
    if not awarded:
        return 0
    evolution = evolution_profile(state)
    evolution["careMistakes"] = max(0, safe_int(evolution.get("careMistakes"))) + awarded
    evolution["mistakesByKind"][kind] = max(0, safe_int(evolution["mistakesByKind"].get(kind))) + awarded
    evolution["lastMistakeAt"] = now_iso()
    daily["careMistakesAwarded"] = safe_int(daily.get("careMistakesAwarded")) + awarded
    event_counts[daily_key] = int(event_counts.get(daily_key, 0)) + awarded
    return awarded


def care_call_state(state: dict[str, Any]) -> dict[str, Any]:
    return state.setdefault("careCall", deepcopy(DEFAULT_CARE_CALL))


def care_call_reason_for_stats(state: dict[str, Any]) -> tuple[str, str, int] | None:
    stats = state.get("stats", {})
    threshold = care_call_policy()["statThreshold"]
    pressures = [
        (
            max(0, threshold - safe_int(stats.get("fullness", DEFAULT_STATS["fullness"]))),
            "feed",
            "hungry",
        ),
        (
            max(0, threshold - safe_int(stats.get("energy", DEFAULT_STATS["energy"]))),
            "rest",
            "tired",
        ),
        (
            max(0, threshold - safe_int(stats.get("mood", DEFAULT_STATS["mood"]))),
            "play",
            "bored",
        ),
        (
            max(0, safe_int(stats.get("stress", DEFAULT_STATS["stress"])) - (100 - threshold)),
            "comfort",
            "stressed",
        ),
    ]
    score, kind, reason = max(pressures, key=lambda item: (item[0], -CARE_KINDS.index(item[1])))
    if score <= 0:
        return None
    return kind, reason, score


def care_mistake_for_call(kind: str) -> str:
    if kind == "rest":
        return "overwork"
    if kind == "comfort":
        return "stress"
    return "neglect"


def start_care_call(
    state: dict[str, Any],
    kind: str,
    reason: str,
    *,
    at: datetime | None = None,
    force: bool = False,
) -> bool:
    if kind not in CARE_KINDS or not is_alive(state):
        return False
    call = care_call_state(state)
    if call.get("active") and not force:
        return False
    stamp_dt = (at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    stamp = to_iso(stamp_dt)
    sequence = safe_int(call.get("sequence")) + 1
    call.update(
        {
            "sequence": sequence,
            "active": True,
            "id": f"{sequence}:{kind}:{stamp}",
            "kind": kind,
            "reason": reason,
            "createdAt": stamp,
            "dueAt": to_iso(stamp_dt + timedelta(seconds=care_call_policy()["responseSeconds"])),
            "lastStatus": "active",
            "answeredAt": None,
            "missedAt": None,
        }
    )
    set_reaction(state, "care_call", message=f"Wants {kind}.", at=stamp_dt)
    return True


def clear_care_call(state: dict[str, Any], status: str, at: datetime | None = None) -> None:
    call = care_call_state(state)
    stamp = to_iso(at or datetime.now(timezone.utc))
    call.update(
        {
            "active": False,
            "id": "",
            "kind": "",
            "reason": "",
            "createdAt": None,
            "dueAt": None,
            "lastClosedAt": stamp,
            "lastStatus": status,
        }
    )


def miss_active_care_call(state: dict[str, Any], at: datetime | None = None) -> bool:
    call = care_call_state(state)
    if not call.get("active"):
        return False
    kind = str(call.get("kind", ""))
    if kind not in CARE_KINDS:
        clear_care_call(state, "missed", at)
        return False
    stamp_dt = (at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    evolution = evolution_profile(state)
    calls = evolution.setdefault("careCalls", deepcopy(DEFAULT_EVOLUTION["careCalls"]))
    calls["missed"] = max(0, safe_int(calls.get("missed"))) + 1
    calls.setdefault("missedByKind", {key: 0 for key in CARE_KINDS})
    calls["missedByKind"][kind] = max(0, safe_int(calls["missedByKind"].get(kind))) + 1
    add_care_mistake(state, care_mistake_for_call(kind))
    clear_care_call(state, "missed", stamp_dt)
    care_call_state(state)["missedAt"] = to_iso(stamp_dt)
    set_reaction(state, "care_miss", message=f"Missed {kind}.", at=stamp_dt)
    return True


def answer_active_care_call(state: dict[str, Any], kind: str, at: datetime | None = None) -> bool:
    call = care_call_state(state)
    if not call.get("active") or call.get("kind") != kind:
        return False
    stamp_dt = (at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    evolution = evolution_profile(state)
    calls = evolution.setdefault("careCalls", deepcopy(DEFAULT_EVOLUTION["careCalls"]))
    calls["answered"] = max(0, safe_int(calls.get("answered"))) + 1
    calls.setdefault("byKind", {key: 0 for key in CARE_KINDS})
    calls["byKind"][kind] = max(0, safe_int(calls["byKind"].get(kind))) + 1
    clear_care_call(state, "answered", stamp_dt)
    care_call_state(state)["answeredAt"] = to_iso(stamp_dt)
    return True


def maybe_update_care_call(
    state: dict[str, Any],
    *,
    at: datetime | None = None,
    allow_generate: bool = True,
) -> str | None:
    if not is_alive(state):
        return None
    stamp_dt = (at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    call = care_call_state(state)
    if call.get("active"):
        due = parse_iso(call.get("dueAt"))
        if due is not None and stamp_dt >= due:
            return "missed" if miss_active_care_call(state, stamp_dt) else None
        return None
    if not allow_generate:
        return None

    need = care_call_reason_for_stats(state)
    if need is None:
        return None
    kind, reason, score = need
    last_closed = parse_iso(call.get("lastClosedAt"))
    if last_closed is not None:
        elapsed = int((stamp_dt - last_closed).total_seconds())
        policy = care_call_policy()
        if elapsed < policy["cooldownSeconds"] and score < policy["urgentThreshold"]:
            return None
    return "started" if start_care_call(state, kind, reason, at=stamp_dt) else None


def record_stat_care_mistakes(state: dict[str, Any]) -> None:
    if not is_alive(state):
        return
    stats = state.get("stats", {})
    if safe_int(stats.get("fullness", DEFAULT_STATS["fullness"])) <= 8 or safe_int(stats.get("mood", DEFAULT_STATS["mood"])) <= 8:
        add_care_mistake(state, "neglect")
    if safe_int(stats.get("energy", DEFAULT_STATS["energy"])) <= 8:
        add_care_mistake(state, "overwork")
    if safe_int(stats.get("stress", DEFAULT_STATS["stress"])) >= 92:
        add_care_mistake(state, "stress")


def award_tool_success_bonus(state: dict[str, Any]) -> int:
    counters = state.setdefault("counters", deepcopy(DEFAULT_COUNTERS))
    turn_state = state.setdefault("turnState", deepcopy(DEFAULT_TURN_STATE))
    current_turn = max(0, safe_int(counters.get("turns")))
    if current_turn == 0 or safe_int(turn_state.get("toolBonusAwardedForTurn")) == current_turn:
        return 0
    awarded = add_xp(state, effective_xp(TURN_TOOL_BONUS_XP))
    turn_state["currentTurn"] = current_turn
    turn_state["toolBonusAwardedForTurn"] = current_turn
    return awarded


def change_stats(state: dict[str, Any], **changes: int) -> None:
    stats = state.setdefault("stats", deepcopy(DEFAULT_STATS))
    for key, delta in changes.items():
        if key in DEFAULT_STATS:
            stats[key] = clamp(int(stats.get(key, DEFAULT_STATS[key])) + int(delta))


def read_hook_payload() -> Any:
    try:
        if sys.stdin is None or sys.stdin.closed or sys.stdin.isatty():
            return None
        raw = sys.stdin.read(HOOK_INPUT_LIMIT)
    except Exception:
        return None
    if not raw.strip():
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def iter_payload_values(payload: Any) -> list[Any]:
    values: list[Any] = []
    stack = [payload]
    while stack and len(values) < 200:
        item = stack.pop()
        values.append(item)
        if isinstance(item, dict):
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
    return values


def infer_success(payload: Any) -> bool | None:
    if payload is None:
        return None
    success_keys = {"success", "succeeded", "ok"}
    status_keys = {"status", "outcome", "result", "conclusion"}
    stack = [payload]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            for key, value in item.items():
                key_l = str(key).lower()
                if key_l in success_keys and isinstance(value, bool):
                    return value
                if key_l in status_keys and isinstance(value, str):
                    text = value.lower()
                    if text in {"success", "succeeded", "ok", "passed", "complete", "completed"}:
                        return True
                    if text in {"failure", "failed", "error", "errored", "cancelled", "canceled"}:
                        return False
                if isinstance(value, (dict, list)):
                    stack.append(value)
        elif isinstance(item, list):
            stack.extend(item)
    return None


def infer_tool_name(payload: Any) -> str:
    if payload is None:
        return ""
    interesting = {"tool", "tool_name", "toolname", "name", "matcher"}
    stack = [payload]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            for key, value in item.items():
                if str(key).lower() in interesting and isinstance(value, str):
                    return value.lower()
                if isinstance(value, (dict, list)):
                    stack.append(value)
        elif isinstance(item, list):
            stack.extend(item)
    return ""


def is_test_like_tool_output(tool_name: str, output: Any) -> bool:
    if not isinstance(output, str):
        output = ""
    sample = output.lower()[:4000]
    haystack = f"{tool_name.lower()} {sample}"
    markers = (
        "pytest",
        "unittest",
        "npm test",
        "pnpm test",
        "yarn test",
        "vitest",
        "jest",
        "cargo test",
        "go test",
        "dotnet test",
        "mvn test",
        "gradle test",
        " test passed",
        " tests passed",
        " test failed",
        " tests failed",
    )
    return any(marker in haystack for marker in markers) or bool(
        re.search(r"\bran\s+\d+\s+tests?\b", sample)
        or re.search(r"\b\d+\s+(passed|failed|skipped|errors?)\b", sample)
    )


def reaction_from_event(event: str, payload: Any, success: bool | None) -> str | None:
    normalized = event.lower()
    if normalized == "sessionstart":
        return "wake"
    if normalized == "userpromptsubmit":
        return "prompt"
    if normalized != "posttooluse":
        return None

    if isinstance(payload, dict):
        explicit = payload.get("reactionKind")
        if isinstance(explicit, str) and explicit in REACTION_MESSAGES:
            return explicit

    if success is False:
        return "tool_failure"
    return "tool_success"


def branch_from_event(event: str, payload: Any, success: bool | None) -> str:
    event_l = event.lower()
    tool = infer_tool_name(payload)
    values = " ".join(str(v).lower() for v in iter_payload_values(payload) if isinstance(v, str))
    haystack = f"{event_l} {tool} {values}"

    if success is False or "test" in haystack or "pytest" in haystack or "error" in haystack:
        return "debugger"
    if "review" in haystack or "diff" in haystack or "pull" in haystack:
        return "reviewer"
    if "read" in haystack or "search" in haystack or "rg" in haystack or "open" in haystack:
        return "explorer"
    return "builder"


def maybe_evolve(state: dict[str, Any]) -> bool:
    if not is_alive(state):
        return False
    xp = int(state.get("xp", 0))
    current = state.get("stage", "baby")
    target: str | None = None
    if current == "baby" and xp >= THRESHOLDS["teen"]:
        target = "teen"
    elif current == "teen" and xp >= THRESHOLDS["adult"]:
        target = "adult"
    if target is not None:
        form = choose_form_for_stage(state, target)
        state["stage"] = target
        state.setdefault("assets", {})["currentStage"] = target
        apply_form(state, target, form)
        return True
    return False


def apply_event(
    state: dict[str, Any],
    event: str,
    payload: Any | None = None,
    *,
    update_stats: bool = True,
    check_evolution: bool = True,
) -> bool:
    counters = state.setdefault("counters", deepcopy(DEFAULT_COUNTERS))
    event_counts = ensure_daily(state).setdefault("eventCounts", {})
    event_counts[event] = int(event_counts.get(event, 0)) + 1

    if is_alive(state):
        maybe_update_care_call(state, allow_generate=False)

    success = infer_success(payload)
    branch = branch_from_event(event, payload, success)
    state["branchSignals"][branch] = int(state["branchSignals"].get(branch, 0)) + 1
    add_focus_point(state, branch)

    normalized = event.lower()
    alive = is_alive(state)
    if normalized == "sessionstart":
        counters["sessions"] += 1
        if alive:
            mark_interaction(state)
        if alive and update_stats:
            change_stats(state, energy=-1, mood=1)
    elif normalized == "userpromptsubmit":
        counters["prompts"] += 1
        counters["turns"] += 1
        if alive:
            mark_interaction(state)
            turn_state = state.setdefault("turnState", deepcopy(DEFAULT_TURN_STATE))
            turn_state["currentTurn"] = counters["turns"]
            add_xp(state, effective_xp(TURN_XP))
            add_training_point(state, "focus")
        if alive and update_stats:
            change_stats(state, fullness=-1, energy=-1, mood=1)
    elif normalized == "posttooluse":
        counters["toolUses"] += 1
        if alive and isinstance(payload, dict) and payload.get("reactionKind") in {"test_pass", "test_fail"}:
            add_training_point(state, "testing")
        if success is False:
            counters["failedTools"] += 1
            if alive:
                add_training_point(state, "recovery")
            if alive and update_stats:
                change_stats(state, stress=3, mood=-1, energy=-1)
        else:
            counters["successfulTools"] += 1
            if alive:
                award_tool_success_bonus(state)
            if alive and update_stats:
                change_stats(state, stress=-1, mood=1)
    elif normalized == "stop":
        if alive and update_stats:
            change_stats(state, fullness=-1, energy=-1, mood=-1, stress=-1)

    reaction = reaction_from_event(event, payload, success)
    if alive and reaction is not None:
        set_reaction(state, reaction)
    if alive:
        record_stat_care_mistakes(state)
        maybe_update_care_call(state)

    return maybe_evolve(state) if alive and check_evolution else False


def record_event(event: str, payload: Any | None = None) -> dict[str, Any]:
    state = load_state()
    lifecycle_change = apply_lifecycle(state)
    evolved = apply_event(state, event, payload)
    if lifecycle_change == "reborn":
        set_reaction(state, "rebirth")
    save_state(state)
    if lifecycle_change == "reborn":
        install_stage("baby", state=state)
    elif evolved:
        install_stage(state["stage"], state=state)
    return state


def iter_session_logs(root: Path | None = None) -> list[Path]:
    root = (root or sessions_dir()).expanduser().resolve()
    if not root.exists():
        return []
    return sorted((path for path in root.rglob("*.jsonl") if path.is_file()), key=lambda path: str(path).lower())


def infer_tool_output_success(output: Any) -> bool | None:
    if not isinstance(output, str):
        return None
    match = re.search(r"Exit code:\s*(-?\d+)", output)
    if match:
        return int(match.group(1)) == 0
    lowered = output.lower()
    if "tool call failed" in lowered or "tool_error" in lowered:
        return False
    return True


def decode_session_record(raw: bytes) -> dict[str, Any] | None:
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError:
        decoded = raw.decode("utf-8", errors="replace")
    if not decoded.strip():
        return None
    try:
        record = json.loads(decoded)
    except json.JSONDecodeError:
        return None
    return record if isinstance(record, dict) else None


def apply_session_record(
    state: dict[str, Any],
    record: dict[str, Any],
    *,
    key: str,
    checkpoint: dict[str, Any],
    summary: dict[str, int],
    check_evolution: bool = True,
) -> bool:
    payload = record.get("payload")
    if not isinstance(payload, dict):
        return False

    evolved = False
    record_type = record.get("type")
    payload_type = payload.get("type")
    pending_tools = state.setdefault("ingest", deepcopy(DEFAULT_INGEST)).setdefault("pendingTools", {})

    if record_type == "session_meta" and not checkpoint.get("sessionStarted", False):
        checkpoint["sessionStarted"] = True
        evolved = apply_event(state, "SessionStart", {"source": "session_log"}, update_stats=False, check_evolution=check_evolution)
        summary["sessions"] += 1
    elif record_type == "event_msg" and payload_type == "user_message":
        evolved = apply_event(state, "UserPromptSubmit", {"source": "session_log"}, update_stats=False, check_evolution=check_evolution)
        summary["prompts"] += 1
    elif record_type == "response_item" and payload_type == "function_call":
        call_id = payload.get("call_id")
        name = payload.get("name")
        if isinstance(call_id, str) and isinstance(name, str):
            pending_tools[f"{key}:{call_id}"] = name
    elif record_type == "response_item" and payload_type == "function_call_output":
        call_id = payload.get("call_id")
        pending_key = f"{key}:{call_id}" if isinstance(call_id, str) else ""
        tool_name = pending_tools.pop(pending_key, "") if pending_key else ""
        output = payload.get("output")
        success = infer_tool_output_success(output)
        reaction_kind = None
        if is_test_like_tool_output(tool_name, output):
            reaction_kind = "test_fail" if success is False else "test_pass"
        evolved = apply_event(
            state,
            "PostToolUse",
            {"tool": tool_name, "success": success, "reactionKind": reaction_kind},
            update_stats=False,
            check_evolution=check_evolution,
        )
        summary["tools"] += 1
        if success is False:
            summary["failedTools"] += 1
        else:
            summary["successfulTools"] += 1

    return evolved


def apply_sync_stat_summary(state: dict[str, Any], summary: dict[str, int]) -> None:
    if not summary["lines"]:
        return

    fullness_delta = -min(6, max(1, summary["prompts"] // 20)) if summary["prompts"] else 0
    energy_delta = -min(6, max(1, (summary["prompts"] + summary["tools"]) // 80)) if summary["prompts"] or summary["tools"] else 0
    mood_delta = min(6, summary["sessions"] + max(0, summary["successfulTools"] // 50))
    stress_delta = min(10, summary["failedTools"]) - min(4, summary["successfulTools"] // 100)

    change_stats(
        state,
        fullness=fullness_delta,
        energy=energy_delta,
        mood=mood_delta,
        stress=stress_delta,
    )
    record_stat_care_mistakes(state)


def sync_session_logs(root: Path | None = None, *, apply_stop_decay: bool = True) -> tuple[dict[str, Any], dict[str, int]]:
    state = load_state()
    lifecycle_change = apply_lifecycle(state)
    care_call_change = maybe_update_care_call(state, allow_generate=False)
    ingest = state.setdefault("ingest", deepcopy(DEFAULT_INGEST))
    session_logs = ingest.setdefault("sessionLogs", {})
    summary = {
        "files": 0,
        "lines": 0,
        "sessions": 0,
        "prompts": 0,
        "tools": 0,
        "successfulTools": 0,
        "failedTools": 0,
        "stops": 0,
    }
    evolved = False

    for path in iter_session_logs(root):
        key = log_key(path)
        stat = path.stat()
        checkpoint = session_logs.setdefault(key, {})
        offset = max(0, safe_int(checkpoint.get("offset")))
        if stat.st_size < offset:
            offset = 0
            checkpoint.clear()
        checkpoint.setdefault("sessionStarted", False)

        with path.open("rb") as handle:
            handle.seek(offset)
            while True:
                line_start = handle.tell()
                raw = handle.readline()
                if not raw:
                    break
                record = decode_session_record(raw)
                if record is None:
                    offset = line_start
                    break
                offset = handle.tell()
                summary["lines"] += 1
                if apply_session_record(
                    state,
                    record,
                    key=key,
                    checkpoint=checkpoint,
                    summary=summary,
                    check_evolution=not evolved,
                ):
                    evolved = True

        if offset != max(0, safe_int(checkpoint.get("offset"))) or stat.st_size != max(0, safe_int(checkpoint.get("size"))):
            summary["files"] += 1
        checkpoint["offset"] = offset
        checkpoint["size"] = path.stat().st_size
        checkpoint["mtime"] = int(path.stat().st_mtime)

    apply_sync_stat_summary(state, summary)

    if apply_stop_decay and summary["lines"]:
        if apply_event(state, "Stop", {"source": "session_log_sync"}, update_stats=True, check_evolution=not evolved):
            evolved = True
        summary["stops"] = 1

    care_call_change = maybe_update_care_call(state) or care_call_change

    if not evolved and maybe_evolve(state):
        evolved = True

    if evolved or lifecycle_change == "reborn":
        if lifecycle_change == "reborn":
            set_reaction(state, "rebirth")
        save_state(state)
        install_stage(state["stage"], state=state)
    else:
        save_state(state)
    return state, summary


def session_log_checkpoints_at_end(root: Path | None = None) -> dict[str, dict[str, Any]]:
    checkpoints: dict[str, dict[str, Any]] = {}
    for path in iter_session_logs(root):
        stat = path.stat()
        checkpoints[log_key(path)] = {
            "offset": stat.st_size,
            "size": stat.st_size,
            "mtime": int(stat.st_mtime),
            "sessionStarted": True,
        }
    return checkpoints


def pet_pack_root(pack_id: str) -> Path:
    pack_id = validate_pet_pack_id(pack_id)
    return pet_packs_dir() / pack_id


def resolve_pack_stage_path(pack_root: Path, raw_path: Any) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise SystemExit("Pet pack stage paths must be non-empty strings.")
    if re.match(r"^[A-Za-z]:", raw_path) or raw_path.startswith(("/", "\\")):
        raise SystemExit("Pet pack stage paths must be relative paths.")
    candidate = (pack_root / raw_path).resolve()
    root = pack_root.resolve()
    if not candidate.is_relative_to(root):
        raise SystemExit("Pet pack stage paths cannot leave the pack folder.")
    return candidate


def validate_stage_package(stage_dir: Path, *, label: str) -> dict[str, Any]:
    manifest_path = stage_dir / "pet.json"
    sprite_path = stage_dir / "spritesheet.webp"
    if not manifest_path.exists():
        raise SystemExit(f"Missing pet.json for {label}: {manifest_path}")
    if not sprite_path.exists():
        raise SystemExit(f"Missing spritesheet.webp for {label}: {sprite_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"pet.json is not valid JSON for {label}: {manifest_path} ({exc})") from exc
    if not isinstance(manifest, dict):
        raise SystemExit(f"pet.json must contain a JSON object for {label}: {manifest_path}")
    if manifest.get("spritesheetPath", "spritesheet.webp") != "spritesheet.webp":
        raise SystemExit(f"{manifest_path} must reference spritesheet.webp")
    for key in ("id", "displayName"):
        if key in manifest and (not isinstance(manifest[key], str) or not manifest[key].strip()):
            raise SystemExit(f"{manifest_path} has an invalid {key}")
    if "description" in manifest and not isinstance(manifest["description"], str):
        raise SystemExit(f"{manifest_path} has an invalid description")
    return manifest


def validate_pet_pack_form(root: Path, pack_id: str, stage: str, form: Any) -> dict[str, Any]:
    if not isinstance(form, dict):
        raise SystemExit(f"Pet pack form for {pack_id}:{stage} must be an object.")
    form_id = validate_pet_pack_id(form.get("id"))
    asset_path = form.get("assetPath")
    if asset_path is None:
        raise SystemExit(f"Pet pack form '{form_id}' is missing assetPath.")
    asset_dir = resolve_pack_stage_path(root, asset_path)
    validate_stage_package(asset_dir, label=f"{pack_id}:{stage}:{form_id}")
    cleaned = dict(form)
    cleaned["id"] = form_id
    cleaned["name"] = str(cleaned.get("name") or cleaned.get("displayName") or form_id).strip() or form_id
    cleaned["assetPath"] = asset_path
    cleaned["path"] = str(cleaned.get("path") or form_id)
    cleaned["default"] = bool(cleaned.get("default", False))
    evolves_from = cleaned.get("evolvesFrom", [])
    if evolves_from is None:
        evolves_from = []
    if not isinstance(evolves_from, list):
        raise SystemExit(f"Pet pack form '{form_id}' evolvesFrom must be a list.")
    cleaned["evolvesFrom"] = [validate_pet_pack_id(item) for item in evolves_from]
    for key in ("requirements", "dw1Requirements", "sourceRequirements"):
        if key in cleaned and not isinstance(cleaned[key], dict):
            raise SystemExit(f"Pet pack form '{form_id}' {key} must be an object.")
    return cleaned


def validate_pet_pack_forms(root: Path, pack_id: str, forms: Any) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(forms, dict):
        raise SystemExit("Pet pack forms must be an object keyed by stage.")
    cleaned: dict[str, list[dict[str, Any]]] = {}
    seen_ids: set[str] = set()
    for stage in STAGES:
        raw_stage_forms = forms.get(stage, [])
        if not isinstance(raw_stage_forms, list):
            raise SystemExit(f"Pet pack forms.{stage} must be a list.")
        cleaned[stage] = []
        for form in raw_stage_forms:
            cleaned_form = validate_pet_pack_form(root, pack_id, stage, form)
            if cleaned_form["id"] in seen_ids:
                raise SystemExit(f"Duplicate pet pack form id: {cleaned_form['id']}")
            seen_ids.add(cleaned_form["id"])
            cleaned[stage].append(cleaned_form)
        if not cleaned[stage]:
            raise SystemExit(f"Pet pack forms.{stage} must include at least one form.")
    return cleaned


def find_pet_pack_root(path: Path) -> Path:
    root = path.expanduser().resolve()
    if (root / "pack.json").exists():
        return root
    candidates = [child for child in root.iterdir() if child.is_dir() and (child / "pack.json").exists()]
    if len(candidates) == 1:
        return candidates[0]
    raise SystemExit(f"Could not find pack.json at {root}")


def validate_pet_pack_root(root: Path) -> dict[str, Any]:
    root = find_pet_pack_root(root)
    manifest_path = root / "pack.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"pack.json is not valid JSON: {manifest_path} ({exc})") from exc
    if not isinstance(manifest, dict):
        raise SystemExit(f"pack.json must contain a JSON object: {manifest_path}")
    if safe_int(manifest.get("schemaVersion")) != 1:
        raise SystemExit("Pet pack schemaVersion must be 1.")
    pack_id = validate_pet_pack_id(manifest.get("id"))
    if pack_id == BUILTIN_PACK_ID:
        raise SystemExit(f"'{BUILTIN_PACK_ID}' is reserved for bundled pets.")
    stages = manifest.get("stages")
    forms = manifest.get("forms")
    if not isinstance(stages, dict) and not isinstance(forms, dict):
        raise SystemExit("Pet pack must define either a stages object or a forms object.")
    cleaned_forms = validate_pet_pack_forms(root, pack_id, forms) if isinstance(forms, dict) else None
    if isinstance(stages, dict):
        for stage in STAGES:
            if stage not in stages:
                raise SystemExit(f"Pet pack is missing stage '{stage}'.")
            stage_dir = resolve_pack_stage_path(root, stages[stage])
            validate_stage_package(stage_dir, label=f"{pack_id}:{stage}")
    cleaned = dict(manifest)
    cleaned["id"] = pack_id
    cleaned["name"] = str(cleaned.get("name") or pack_id).strip() or pack_id
    cleaned["author"] = str(cleaned.get("author") or "").strip()
    cleaned["description"] = str(cleaned.get("description") or "").strip()
    if isinstance(stages, dict):
        cleaned["stages"] = {stage: stages[stage] for stage in STAGES}
    elif cleaned_forms is not None:
        cleaned["stages"] = {stage: cleaned_forms[stage][0]["assetPath"] for stage in STAGES}
    if cleaned_forms is not None:
        cleaned["forms"] = cleaned_forms
    return cleaned


def load_installed_pet_pack(pack_id: str) -> tuple[Path, dict[str, Any]]:
    pack_id = validate_pet_pack_id(pack_id)
    if pack_id == BUILTIN_PACK_ID:
        return ASSET_ROOT.parent, builtin_pack_manifest()
    root = pet_pack_root(pack_id)
    if not root.exists():
        raise SystemExit(f"Pet pack '{pack_id}' is not installed. Run: pets list")
    return find_pet_pack_root(root), validate_pet_pack_root(root)


def pet_pack_display_name(pack_id: str) -> str:
    try:
        _root, manifest = load_installed_pet_pack(pack_id)
        return str(manifest.get("name") or pack_id)
    except SystemExit:
        return pack_id


def pet_pack_form_ids(pack_id: str) -> set[str]:
    try:
        _root, manifest = load_installed_pet_pack(pack_id)
    except SystemExit:
        return set()
    ids: set[str] = set()
    for forms in manifest.get("forms", {}).values():
        if isinstance(forms, list):
            ids.update(str(form.get("id", "")) for form in forms if isinstance(form, dict))
    return {form_id for form_id in ids if form_id}


def iter_installed_pet_packs() -> list[dict[str, Any]]:
    packs = []
    packs.append(
        {
            "id": BUILTIN_PACK_ID,
            "name": builtin_pack_manifest()["name"],
            "author": builtin_pack_manifest()["author"],
            "description": builtin_pack_manifest()["description"],
            "builtin": True,
            "path": str(ASSET_ROOT),
            "forms": 0,
        }
    )
    root = pet_packs_dir()
    if root.exists():
        for child in sorted(root.iterdir(), key=lambda item: item.name.lower()):
            if not child.is_dir():
                continue
            try:
                pack_root, manifest = load_installed_pet_pack(child.name)
            except SystemExit as exc:
                packs.append(
                    {
                        "id": child.name,
                        "name": child.name,
                        "author": "",
                        "description": "",
                        "builtin": False,
                        "path": str(child),
                        "error": str(exc),
                        "forms": 0,
                    }
                )
                continue
            form_count = sum(len(forms) for forms in manifest.get("forms", {}).values() if isinstance(forms, list))
            packs.append(
                {
                    "id": manifest["id"],
                    "name": manifest["name"],
                    "author": manifest.get("author", ""),
                    "description": manifest.get("description", ""),
                    "builtin": False,
                    "path": str(pack_root),
                    "forms": form_count,
                }
            )
    return packs


def form_asset_path_from_manifest(pack_root: Path, manifest: dict[str, Any], stage: str, form_id: str | None = None) -> Path | None:
    forms = pack_forms_for_stage(manifest, stage)
    if not forms:
        return None
    selected = None
    if form_id:
        for form in forms:
            if str(form.get("id")) == form_id:
                selected = form
                break
    if selected is None:
        selected = pack_default_form(forms)
    if selected is None:
        return None
    return resolve_pack_stage_path(pack_root, selected["assetPath"])


def stage_asset_dir(stage: str, pack_id: str | None = None, form_id: str | None = None) -> Path:
    if stage not in STAGES:
        raise SystemExit(f"Unknown stage '{stage}'. Expected one of: {', '.join(STAGES)}")
    resolved_pack_id = pack_id or active_pet_pack_id()
    if resolved_pack_id == BUILTIN_PACK_ID:
        path = ASSET_ROOT / stage
    else:
        pack_root, manifest = load_installed_pet_pack(resolved_pack_id)
        path = form_asset_path_from_manifest(pack_root, manifest, stage, form_id)
        if path is None:
            path = resolve_pack_stage_path(pack_root, manifest["stages"][stage])
    validate_stage_package(path, label=f"{resolved_pack_id}:{stage}")
    return path


def write_pet_package(stage: str, target_dir: Path, pet_id: str, *, sprite_name: str, form_id: str | None = None) -> Path:
    source_dir = stage_asset_dir(stage, form_id=form_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_dir / "spritesheet.webp", target_dir / sprite_name)

    manifest = json.loads((source_dir / "pet.json").read_text(encoding="utf-8"))
    active_manifest = {
        "id": pet_id,
        "displayName": manifest.get("displayName", "Codex Tomogatchi"),
        "description": manifest.get("description", "A Codex pet that grows with your work."),
        "spritesheetPath": sprite_name,
    }
    (target_dir / "pet.json").write_text(json.dumps(active_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target_dir


def install_stage_package(stage: str, *, state: dict[str, Any] | None = None) -> Path:
    form_id = None
    if state is not None and state.get("stage") == stage:
        form_id = str(state.get("evolution", {}).get("formId") or "")
    return write_pet_package(stage, active_pet_dir(stage), stage_pet_id(stage), sprite_name=f"spritesheet-{stage}.webp", form_id=form_id)


def install_all_stage_packages(*, state: dict[str, Any] | None = None) -> dict[str, Path]:
    return {stage: install_stage_package(stage, state=state) for stage in STAGES}


def cleanup_legacy_pet_package() -> None:
    if os.environ.get("CODEX_TOMOGATCHI_KEEP_LEGACY_PET", "").lower() in {"1", "true", "yes", "on"}:
        return
    target_dir = legacy_pet_dir()
    if target_dir.name != PET_ID or not target_dir.exists():
        return
    manifest_path = target_dir / "pet.json"
    if not manifest_path.exists():
        return
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    if manifest.get("id") == PET_ID:
        shutil.rmtree(target_dir)


def install_stage(stage: str, *, state: dict[str, Any] | None = None) -> Path:
    if state is None:
        state = load_state()
    stage_dirs = install_all_stage_packages(state=state)
    cleanup_legacy_pet_package()
    target_dir = stage_dirs[stage]
    config_path = select_codex_avatar(stage)
    pack_id = active_pet_pack_id()

    state["stage"] = stage
    state["assets"]["currentStage"] = stage
    state["assets"]["activePetPack"] = pack_id
    state["assets"]["activePetPackName"] = pet_pack_display_name(pack_id)
    state["assets"]["activePetId"] = stage_pet_id(stage)
    state["assets"]["installedPetPath"] = str(target_dir)
    state["assets"]["selectedAvatarId"] = selected_avatar_id(stage)
    state["assets"]["selectedAvatarConfigPath"] = str(config_path) if config_path is not None else None
    state["assets"]["installedStagePetPaths"] = {key: str(value) for key, value in stage_dirs.items()}
    save_state(state)
    return target_dir


def is_safe_zip_member(name: str) -> bool:
    normalized = name.replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
        return False
    parts = [part for part in normalized.split("/") if part]
    return bool(parts) and all(part not in {".", ".."} for part in parts)


def zip_destination(raw_output: str | None, default_dir: Path, default_name: str) -> Path:
    if raw_output:
        target = Path(raw_output).expanduser()
        if target.exists() and target.is_dir():
            target = target / default_name
    else:
        target = default_dir / default_name
    if target.suffix.lower() != ".zip":
        target = target.with_suffix(".zip")
    return target.resolve()


def write_zip_from_directory(source_root: Path, destination: Path, *, prefix: str) -> Path:
    source_root = source_root.expanduser().resolve()
    destination = destination.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix="tomogatchi-zip-", suffix=".zip", dir=str(destination.parent), delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(source_root.rglob("*")):
                if not path.is_file():
                    continue
                relative = path.relative_to(source_root).as_posix()
                archive.write(path, f"{prefix}/{relative}")
        os.replace(tmp_path, destination)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
    return destination


def extract_pet_pack_zip(source: Path, target: Path) -> None:
    with zipfile.ZipFile(source) as archive:
        for member in archive.infolist():
            if not is_safe_zip_member(member.filename):
                raise SystemExit(f"Unsafe path in pet pack zip: {member.filename}")
        for member in archive.infolist():
            if member.is_dir():
                continue
            relative = Path(*[part for part in member.filename.replace("\\", "/").split("/") if part])
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source_handle, destination.open("wb") as target_handle:
                shutil.copyfileobj(source_handle, target_handle)


def validate_pet_pack_source(source: Path) -> dict[str, Any]:
    source = source.expanduser().resolve()
    if not source.exists():
        raise SystemExit(f"Pet pack source does not exist: {source}")
    if source.is_file():
        if source.suffix.lower() != ".zip":
            raise SystemExit("Pet pack files must be .zip archives.")
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp_root = Path(tmp_name)
            extract_pet_pack_zip(source, tmp_root)
            return validate_pet_pack_root(find_pet_pack_root(tmp_root))
    if source.is_dir():
        return validate_pet_pack_root(source)
    raise SystemExit(f"Pet pack source must be a folder or .zip file: {source}")


def import_pet_pack(source: Path, *, replace: bool = False) -> dict[str, Any]:
    source = source.expanduser().resolve()
    if not source.exists():
        raise SystemExit(f"Pet pack source does not exist: {source}")

    with tempfile.TemporaryDirectory() as tmp_name:
        tmp_root = Path(tmp_name)
        if source.is_file():
            if source.suffix.lower() != ".zip":
                raise SystemExit("Pet pack files must be .zip archives.")
            extract_pet_pack_zip(source, tmp_root)
            pack_root = find_pet_pack_root(tmp_root)
        elif source.is_dir():
            pack_root = find_pet_pack_root(source)
        else:
            raise SystemExit(f"Pet pack source must be a folder or .zip file: {source}")

        manifest = validate_pet_pack_root(pack_root)
        destination = pet_pack_root(manifest["id"])
        if destination.exists() and not replace:
            raise SystemExit(f"Pet pack '{manifest['id']}' is already installed. Use --replace to overwrite it.")

        parent = destination.parent
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=str(parent)) as staging_name:
            staging = Path(staging_name) / manifest["id"]
            shutil.copytree(pack_root, staging)
            if destination.exists():
                shutil.rmtree(destination)
            shutil.move(str(staging), destination)

    return validate_pet_pack_root(destination)


def export_pet_pack(pack_id: str, output: str | None = None) -> Path:
    pack_id = validate_pet_pack_id(pack_id)
    if pack_id == BUILTIN_PACK_ID:
        raise SystemExit("The bundled default pack is not exported through pet-pack export.")
    pack_root, manifest = load_installed_pet_pack(pack_id)
    destination = zip_destination(output, exports_dir(), f"{manifest['id']}.codex-pet-pack.zip")
    return write_zip_from_directory(pack_root, destination, prefix=manifest["id"])


def select_pet_pack(pack_id: str) -> Path:
    pack_id = validate_pet_pack_id(pack_id)
    _pack_root, manifest = load_installed_pet_pack(pack_id)
    settings = load_settings()
    settings.setdefault("pets", {})["activePack"] = pack_id
    starter_id = str(settings.get("pets", {}).get("starterForm", ""))
    if starter_id and pack_form_by_id(manifest, "baby", starter_id) is None:
        settings["pets"]["starterForm"] = ""
    save_settings(settings)
    state = load_state()
    form = choose_form_for_stage(state, state.get("stage", "baby"))
    apply_form(state, state.get("stage", "baby"), form)
    return install_stage(state.get("stage", "baby"), state=state)


def do_pets_list(args: argparse.Namespace) -> int:
    active = active_pet_pack_id()
    packs = iter_installed_pet_packs()
    if args.json:
        print(json.dumps({"activePack": active, "packs": packs}, indent=2, sort_keys=True))
        return 0
    print(f"Pet packs path: {pet_packs_dir()}")
    print(f"Active pet pack: {active}")
    for pack in packs:
        marker = "*" if pack["id"] == active else "-"
        source = "builtin" if pack.get("builtin") else "custom"
        error = f" ({pack['error']})" if pack.get("error") else ""
        forms = f" | {pack['forms']} forms" if pack.get("forms") else ""
        print(f"{marker} {pack['id']} | {pack['name']} | {source}{forms}{error}")
    return 0


def do_pets_import(args: argparse.Namespace) -> int:
    manifest = import_pet_pack(Path(args.source), replace=args.replace)
    print(f"Imported pet pack '{manifest['id']}' ({manifest['name']})")
    if args.select:
        target = select_pet_pack(manifest["id"])
        print(f"Selected pet pack '{manifest['id']}' and installed current stage to {target}")
    return 0


def do_pets_validate(args: argparse.Namespace) -> int:
    manifest = validate_pet_pack_source(Path(args.source))
    form_count = sum(len(forms) for forms in manifest.get("forms", {}).values() if isinstance(forms, list))
    if args.json:
        print(
            json.dumps(
                {
                    "id": manifest["id"],
                    "name": manifest["name"],
                    "author": manifest.get("author", ""),
                    "description": manifest.get("description", ""),
                    "forms": form_count,
                    "stages": list(STAGES),
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        forms = f", {form_count} forms" if form_count else ""
        print(f"Valid pet pack: {manifest['id']} | {manifest['name']}{forms}")
    return 0


def do_pets_export(args: argparse.Namespace) -> int:
    target = export_pet_pack(args.pack_id, args.output)
    print(f"Exported pet pack '{validate_pet_pack_id(args.pack_id)}' to {target}")
    return 0


def do_pets_select(args: argparse.Namespace) -> int:
    target = select_pet_pack(args.pack_id)
    print(f"Selected pet pack '{validate_pet_pack_id(args.pack_id)}'")
    print(f"Installed current stage to {target}")
    return 0


def do_pets_forms(args: argparse.Namespace) -> int:
    pack_id = validate_pet_pack_id(args.pack_id) if args.pack_id else active_pet_pack_id()
    _pack_root, manifest = load_installed_pet_pack(pack_id)
    forms = {
        stage: [
            {
                "id": str(form.get("id")),
                "name": str(form.get("name") or form.get("displayName") or form.get("id")),
                "default": bool(form.get("default", False)),
                "evolvesFrom": list(form.get("evolvesFrom", [])) if isinstance(form.get("evolvesFrom", []), list) else [],
                "hasRequirements": isinstance(form.get("requirements"), dict),
            }
            for form in pack_forms_for_stage(manifest, stage)
        ]
        for stage in STAGES
    }
    selected_starter = active_starter_form_id() if pack_id == active_pet_pack_id() else ""
    if args.json:
        print(
            json.dumps(
                {
                    "packId": pack_id,
                    "packName": manifest.get("name", pack_id),
                    "activePack": active_pet_pack_id(),
                    "selectedStarter": selected_starter,
                    "forms": forms,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    print(f"Pet pack: {pack_id} | {manifest.get('name', pack_id)}")
    if not any(forms.values()):
        print("This pack uses one fixed form per stage and has no selectable starters.")
        return 0
    if selected_starter:
        print(f"Selected starter: {selected_starter}")
    for stage in STAGES:
        print(f"{stage}:")
        for form in forms[stage]:
            marker = "*" if stage == "baby" and form["id"] == selected_starter else "-"
            default = " default" if form["default"] else ""
            evolves_from = f" <- {', '.join(form['evolvesFrom'])}" if form["evolvesFrom"] else ""
            requirements = " requirements" if form["hasRequirements"] else ""
            print(f"  {marker} {form['id']} | {form['name']}{default}{evolves_from}{requirements}")
    return 0


def do_pets_hatch(args: argparse.Namespace) -> int:
    pack_id = active_pet_pack_id()
    if pack_id == BUILTIN_PACK_ID:
        raise SystemExit("Select a branching pet pack before hatching a starter.")
    _pack_root, manifest = load_installed_pet_pack(pack_id)
    form_id = validate_pet_pack_id(args.form_id)
    form = pack_form_by_id(manifest, "baby", form_id)
    if form is None:
        raise SystemExit(f"Baby form '{form_id}' is not available in active pack '{pack_id}'. Run: pets forms")

    settings = load_settings()
    settings.setdefault("pets", {})["starterForm"] = form_id
    save_settings(settings)

    state = default_state()
    state["evolution"]["lineage"] = []
    apply_form(state, "baby", choose_form_for_stage(state, "baby"))
    if not args.include_history:
        root = Path(args.sessions_dir).expanduser().resolve() if args.sessions_dir else None
        state["ingest"]["sessionLogs"] = session_log_checkpoints_at_end(root)
        state["ingest"]["pendingTools"] = {}
    save_state(state)
    target = install_stage("baby", state=state)
    suffix = " from current session-log position" if not args.include_history else " with existing session-log history enabled"
    print(f"Hatched {form.get('name') or form_id} ({form_id}){suffix}.")
    print(f"Installed baby stage to {target}")
    return 0


def do_status(args: argparse.Namespace) -> int:
    state = load_state()
    lifecycle_change = apply_lifecycle(state)
    care_call_change = maybe_update_care_call(state)
    if lifecycle_change or care_call_change:
        save_state(state)
        if lifecycle_change == "reborn":
            install_stage("baby", state=state)
    if args.json:
        print(json.dumps(state, indent=2, sort_keys=True))
        return 0
    stats = state["stats"]
    counters = state["counters"]
    branch = state["branchSignals"]
    evolution = state["evolution"]
    lifecycle = state["lifecycle"]
    status = lifecycle.get("status", "alive")
    print(
        f"Codex Tomogatchi: {state['stage']} | {evolution['formName']} | "
        f"{status} | level {state['level']} | {state['xp']} XP"
    )
    print(
        "Evolution: "
        f"gen {evolution['generation']}, path {evolution['path']}, "
        f"form {evolution['formId']}, care mistakes {evolution['careMistakes']}"
    )
    settings = load_settings()
    print(f"Pet pack: {state['assets'].get('activePetPack', BUILTIN_PACK_ID)} | {state['assets'].get('activePetPackName', '')}")
    print(f"Starter form: {settings['pets'].get('starterForm') or 'pack default'}")
    if status == "dead":
        print(f"Lifecycle: rebirth in {format_duration(seconds_until(lifecycle.get('rebirthDueAt')))}")
    elif not lifecycle_death_enabled():
        print("Lifecycle: death disabled in settings")
    else:
        print(f"Lifecycle: death in {format_duration(seconds_until(lifecycle.get('deathDueAt')))} without interaction")
    print(
        "Stats: "
        f"fullness {stats['fullness']}, energy {stats['energy']}, "
        f"mood {stats['mood']}, stress {stats['stress']}"
    )
    print(
        "Activity: "
        f"{counters['prompts']} prompts, {counters['sessions']} sessions, "
        f"{counters['toolUses']} tools ({counters['successfulTools']} success, {counters['failedTools']} failed)"
    )
    print(
        "Branch signals: "
        f"builder {branch['builder']}, explorer {branch['explorer']}, "
        f"debugger {branch['debugger']}, reviewer {branch['reviewer']}"
    )
    focus = evolution["focusPoints"]
    care = evolution["carePoints"]
    care_call = state["careCall"]
    print(
        "Generation focus: "
        f"builder {focus['builder']}, explorer {focus['explorer']}, "
        f"debugger {focus['debugger']}, reviewer {focus['reviewer']}"
    )
    print(
        "Care points: "
        f"feed {care['feed']}, rest {care['rest']}, play {care['play']}, comfort {care['comfort']}"
    )
    if care_call.get("active"):
        print(
            "Care call: "
            f"{care_call['kind']} ({care_call['reason']}), "
            f"due in {format_duration(seconds_until(care_call.get('dueAt')))}"
        )
    else:
        print(f"Care call: none (last {care_call.get('lastStatus', 'none')})")
    print(f"Selected avatar: {state['assets'].get('selectedAvatarId', selected_avatar_id(state['stage']))}")
    print(f"Installed pet path: {state['assets']['installedPetPath']}")
    return 0


def do_care(args: argparse.Namespace) -> int:
    state = load_state()
    lifecycle_change = apply_lifecycle(state)
    if lifecycle_change == "reborn":
        install_stage("baby", state=state)
    if not is_alive(state):
        save_state(state)
        remaining = format_duration(seconds_until(state["lifecycle"].get("rebirthDueAt")))
        print(f"Care skipped: Codex Tomogatchi is dead. Rebirth in {remaining}.")
        return do_status(argparse.Namespace(json=False))
    care = args.kind
    maybe_update_care_call(state, allow_generate=False)
    answered = answer_active_care_call(state, care)
    mark_interaction(state)
    add_care_point(state, care, 2 if answered else 1)
    if care == "feed":
        change_stats(state, fullness=18, mood=2, stress=-2)
    elif care == "rest":
        change_stats(state, energy=20, stress=-6, mood=2)
    elif care == "play":
        change_stats(state, mood=15, energy=-5, fullness=-4, stress=-4)
        add_care_xp(state, 1)
    elif care == "comfort":
        change_stats(state, stress=-15, mood=8, energy=2)
        add_training_point(state, "recovery")
    set_reaction(state, "care_answered" if answered else "care")
    maybe_update_care_call(state)
    evolved = maybe_evolve(state)
    save_state(state)
    if evolved:
        install_stage(state["stage"], state=state)
    suffix = " and answered the call" if answered else ""
    print(f"Care applied: {care}{suffix}")
    return do_status(argparse.Namespace(json=False))


def do_install(args: argparse.Namespace) -> int:
    state = load_state()
    lifecycle_change = apply_lifecycle(state)
    target = install_stage(args.stage or state["stage"], state=state)
    if lifecycle_change == "reborn":
        target = install_stage("baby", state=state)
    print(f"Installed Codex Tomogatchi stage '{state['stage']}' to {target}")
    print(f"Pet pack: {state['assets'].get('activePetPack', BUILTIN_PACK_ID)} | {state['assets'].get('activePetPackName', '')}")
    print(f"Selected Codex avatar: {selected_avatar_id(state['stage'])}")
    return 0


def do_evolve(args: argparse.Namespace) -> int:
    state = load_state()
    lifecycle_change = apply_lifecycle(state)
    if lifecycle_change == "reborn":
        install_stage("baby", state=state)
    if not is_alive(state):
        save_state(state)
        print(f"No evolution while dead. Rebirth in {format_duration(seconds_until(state['lifecycle'].get('rebirthDueAt')))}.")
        return 0
    before = state["stage"]
    evolved = maybe_evolve(state)
    if evolved:
        install_stage(state["stage"], state=state)
        print(f"Evolved from {before} to {state['stage']}.")
    else:
        save_state(state)
        print(f"No evolution yet. Current stage: {state['stage']} ({state['xp']} XP).")
    return 0


def do_profile(args: argparse.Namespace) -> int:
    state = load_state()
    apply_lifecycle(state)
    evolution = state["evolution"]
    if args.json:
        print(json.dumps(evolution, indent=2, sort_keys=True))
        return 0
    print(f"Generation {evolution['generation']} | {evolution['formName']} | {evolution['path']} path")
    print(f"Form id: {evolution['formId']} ({evolution['reason']})")
    print(f"Care mistakes: {evolution['careMistakes']} | {evolution['mistakesByKind']}")
    print(f"Care points: {evolution['carePoints']}")
    print(f"Care calls: {evolution['careCalls']}")
    print(f"Focus points: {evolution['focusPoints']}")
    print(f"Training points: {evolution['trainingPoints']}")
    next_path, next_reason = evolution_path_for_state(state, "teen" if state.get("stage") == "baby" else "adult")
    print(f"Evolution if threshold hit now: {next_path} ({next_reason})")
    return 0


def do_care_call(args: argparse.Namespace) -> int:
    state = load_state()
    lifecycle_change = apply_lifecycle(state)
    if lifecycle_change == "reborn":
        install_stage("baby", state=state)
    if args.force:
        start_care_call(state, args.force, "manual test", force=True)
    else:
        maybe_update_care_call(state)
    save_state(state)
    if args.json:
        print(json.dumps(state["careCall"], indent=2, sort_keys=True))
        return 0
    call = state["careCall"]
    if call.get("active"):
        print(
            "Care call active: "
            f"{call['kind']} ({call['reason']}), "
            f"due in {format_duration(seconds_until(call.get('dueAt')))}"
        )
    else:
        print(f"No active care call. Last status: {call.get('lastStatus', 'none')}.")
    return 0


def backup_metadata(state: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "createdAt": now_iso(),
        "app": PET_ID,
        "stateSchemaVersion": state.get("schemaVersion", SCHEMA_VERSION),
        "stage": state.get("stage", "baby"),
        "formId": state.get("evolution", {}).get("formId", ""),
        "activePack": settings.get("pets", {}).get("activePack", BUILTIN_PACK_ID),
        "contains": ["state.json", "settings.json"],
        "privacy": "Backup contains aggregate Tomogatchi state/settings only, not raw Codex session logs.",
    }


def create_backup(output: str | None = None) -> Path:
    state = load_state()
    settings = load_settings()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    destination = zip_destination(output, backups_dir(), f"codex-tomogatchi-backup-{stamp}.zip")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix="tomogatchi-backup-", suffix=".zip", dir=str(destination.parent), delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("metadata.json", json.dumps(backup_metadata(state, settings), indent=2, sort_keys=True) + "\n")
            archive.writestr("state.json", json.dumps(state, indent=2, sort_keys=True) + "\n")
            archive.writestr("settings.json", json.dumps(settings, indent=2, sort_keys=True) + "\n")
        os.replace(tmp_path, destination)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
    return destination


def iter_backups() -> list[dict[str, Any]]:
    root = backups_dir()
    if not root.exists():
        return []
    backups = []
    for path in sorted(root.glob("*.zip"), key=lambda item: item.stat().st_mtime, reverse=True):
        metadata: dict[str, Any] = {}
        try:
            with zipfile.ZipFile(path) as archive:
                if "metadata.json" in archive.namelist():
                    metadata = json.loads(archive.read("metadata.json").decode("utf-8"))
        except (OSError, zipfile.BadZipFile, json.JSONDecodeError):
            metadata = {}
        backups.append(
            {
                "path": str(path),
                "name": path.name,
                "size": path.stat().st_size,
                "createdAt": metadata.get("createdAt", ""),
                "stage": metadata.get("stage", ""),
                "formId": metadata.get("formId", ""),
                "activePack": metadata.get("activePack", ""),
            }
        )
    return backups


def read_backup_json(archive: zipfile.ZipFile, member_name: str) -> Any:
    names = archive.namelist()
    matches = [name for name in names if name == member_name or name.endswith(f"/{member_name}")]
    if not matches:
        raise SystemExit(f"Backup is missing {member_name}.")
    try:
        return json.loads(archive.read(matches[0]).decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Backup {member_name} is not valid JSON.") from exc


def restore_backup(source: Path) -> tuple[dict[str, Any], str]:
    source = source.expanduser().resolve()
    if not source.exists():
        raise SystemExit(f"Backup does not exist: {source}")
    if source.suffix.lower() != ".zip":
        raise SystemExit("Backups must be .zip files.")
    try:
        with zipfile.ZipFile(source) as archive:
            for member in archive.infolist():
                if not is_safe_zip_member(member.filename):
                    raise SystemExit(f"Unsafe path in backup zip: {member.filename}")
            raw_state = read_backup_json(archive, "state.json")
            raw_settings = read_backup_json(archive, "settings.json")
    except zipfile.BadZipFile as exc:
        raise SystemExit(f"Backup is not a valid zip file: {source}") from exc

    if not isinstance(raw_state, dict):
        raise SystemExit("Backup state.json must contain an object.")
    settings = merge_settings(raw_settings if isinstance(raw_settings, dict) else {})
    warning = ""
    pack_id = settings.get("pets", {}).get("activePack", BUILTIN_PACK_ID)
    if pack_id != BUILTIN_PACK_ID:
        try:
            load_installed_pet_pack(pack_id)
        except SystemExit:
            warning = f"Active pet pack '{pack_id}' is not installed; restored with bundled pets instead."
            settings["pets"]["activePack"] = BUILTIN_PACK_ID
            settings["pets"]["starterForm"] = ""
    save_settings(settings)
    state = merge_defaults(raw_state)
    save_state(state)
    install_stage(state.get("stage", "baby"), state=state)
    return load_state(), warning


def do_backup_create(args: argparse.Namespace) -> int:
    target = create_backup(args.output)
    print(f"Created backup: {target}")
    return 0


def do_backup_list(args: argparse.Namespace) -> int:
    backups = iter_backups()
    if args.json:
        print(json.dumps({"backupsPath": str(backups_dir()), "backups": backups}, indent=2, sort_keys=True))
        return 0
    print(f"Backups path: {backups_dir()}")
    if not backups:
        print("No backups yet.")
        return 0
    for backup in backups:
        details = f"{backup['stage']} {backup['formId']}".strip()
        pack = f" | {backup['activePack']}" if backup.get("activePack") else ""
        print(f"- {backup['name']} | {backup['createdAt']} | {details}{pack}")
    return 0


def do_backup_restore(args: argparse.Namespace) -> int:
    if not args.confirm:
        raise SystemExit("Refusing to restore without --confirm.")
    state, warning = restore_backup(Path(args.source))
    print(f"Restored backup: {args.source}")
    if warning:
        print(f"Warning: {warning}")
    print(f"Codex Tomogatchi: {state['stage']} | {state['evolution']['formName']} | {state['xp']} XP")
    return 0


def doctor_check(name: str, status: str, detail: str, checks: list[dict[str, str]]) -> None:
    checks.append({"name": name, "status": status, "detail": detail})


def collect_doctor_checks() -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    doctor_check("CODEX_HOME", "ok", str(codex_home()), checks)

    try:
        settings = load_settings()
        doctor_check("settings", "ok", str(settings_path()), checks)
    except SystemExit as exc:
        settings = deepcopy(DEFAULT_SETTINGS)
        doctor_check("settings", "error", str(exc), checks)

    try:
        state = load_state()
        doctor_check("state", "ok" if state_path().exists() else "warn", str(state_path()), checks)
    except SystemExit as exc:
        state = default_state()
        doctor_check("state", "error", str(exc), checks)

    try:
        pack_id = settings.get("pets", {}).get("activePack", BUILTIN_PACK_ID)
        _pack_root, manifest = load_installed_pet_pack(pack_id)
        doctor_check("active pet pack", "ok", f"{pack_id} | {manifest.get('name', pack_id)}", checks)
    except SystemExit as exc:
        doctor_check("active pet pack", "error", str(exc), checks)

    root = sessions_dir()
    if root.exists():
        count = sum(1 for _path in root.rglob("*.jsonl"))
        detail = f"{root} ({count} session log files)"
        if not count:
            detail += "; open Codex Desktop or run Codex CLI once so session logs exist"
        doctor_check("session logs", "ok" if count else "warn", detail, checks)
    else:
        doctor_check(
            "session logs",
            "warn",
            f"{root} does not exist yet; open Codex Desktop or run Codex CLI once",
            checks,
        )

    for stage in STAGES:
        pet_dir = active_pet_dir(stage)
        manifest_path = pet_dir / "pet.json"
        sprite_path = pet_dir / f"spritesheet-{stage}.webp"
        ok = manifest_path.exists() and sprite_path.exists()
        doctor_check(f"installed {stage} pet", "ok" if ok else "warn", str(pet_dir), checks)

    config_path = codex_config_path()
    selected_avatar = state.get("assets", {}).get("selectedAvatarId", selected_avatar_id(state.get("stage", "baby")))
    if config_path.exists():
        config_text = config_path.read_text(encoding="utf-8", errors="ignore")
        status = "ok" if selected_avatar in config_text else "warn"
        doctor_check("Codex avatar config", status, str(config_path), checks)
    else:
        doctor_check("Codex avatar config", "warn", f"{config_path} does not exist yet", checks)

    electron_cmd = PLUGIN_ROOT.parents[1] / "node_modules" / ".bin" / ("electron.cmd" if os.name == "nt" else "electron")
    doctor_check("Electron dependency", "ok" if electron_cmd.exists() else "warn", str(electron_cmd), checks)

    log_path = overlay_log_path()
    doctor_check("overlay log", "ok" if log_path.exists() else "warn", str(log_path), checks)
    doctor_check("backups folder", "ok" if backups_dir().exists() else "warn", str(backups_dir()), checks)
    return checks


def do_doctor(args: argparse.Namespace) -> int:
    checks = collect_doctor_checks()
    errors = [check for check in checks if check["status"] == "error"]
    if args.json:
        print(json.dumps({"ok": not errors, "checks": checks}, indent=2, sort_keys=True))
    else:
        print("Codex Tomogatchi doctor")
        for check in checks:
            print(f"[{check['status']}] {check['name']}: {check['detail']}")
    return 1 if errors else 0


def do_settings(args: argparse.Namespace) -> int:
    settings = load_settings()
    changed = False
    if args.init:
        changed = True
    if args.key:
        if args.value is None:
            raise SystemExit("Provide a value, for example: settings xp.pace slow")
        settings = set_nested_setting(settings, args.key, parse_setting_value(args.value))
        changed = True
    if changed:
        save_settings(settings)
        settings = load_settings()
    if args.json:
        print(json.dumps(settings, indent=2, sort_keys=True))
    else:
        print(f"Settings path: {settings_path()}")
        print(f"XP pace: {settings['xp']['pace']} (daily cap {daily_xp_cap()})")
        print(f"Death enabled: {settings['lifecycle']['deathEnabled']}")
        print(f"Care-call strictness: {settings['care']['callStrictness']}")
        print(f"Active pet pack: {settings['pets']['activePack']}")
        print(f"Starter form: {settings['pets'].get('starterForm') or 'pack default'}")
        print(
            "Overlay: "
            f"alwaysOnTop={settings['overlay']['alwaysOnTop']}, "
            f"startMode={settings['overlay']['startMode']}, "
            f"startMinimized={settings['overlay']['startMinimized']}"
        )
    return 0


def do_reset(args: argparse.Namespace) -> int:
    if not args.confirm:
        raise SystemExit("Refusing to reset without --confirm.")
    state = default_state()
    state["evolution"]["lineage"] = []
    apply_form(state, "baby", choose_form_for_stage(state, "baby"))
    if args.from_now:
        root = Path(args.sessions_dir).expanduser().resolve() if args.sessions_dir else None
        state["ingest"]["sessionLogs"] = session_log_checkpoints_at_end(root)
        state["ingest"]["pendingTools"] = {}
    save_state(state)
    install_stage("baby", state=state)
    suffix = " from current session-log position" if args.from_now else ""
    print(f"Codex Tomogatchi was reset to baby{suffix}.")
    return 0


def do_hook(args: argparse.Namespace) -> int:
    payload = read_hook_payload()
    state = record_event(args.event, payload)
    print(f"Codex Tomogatchi updated: {state['stage']} level {state['level']} ({state['xp']} XP)")
    return 0


def print_sync_summary(state: dict[str, Any], summary: dict[str, int]) -> None:
    print(
        "Synced Codex session logs: "
        f"{summary['sessions']} sessions, {summary['prompts']} prompts, "
        f"{summary['tools']} tools ({summary['successfulTools']} success, {summary['failedTools']} failed), "
        f"{summary['stops']} stop decays."
    )
    print(f"Codex Tomogatchi: {state['stage']} | level {state['level']} | {state['xp']} XP")


def do_sync(args: argparse.Namespace) -> int:
    root = Path(args.sessions_dir).expanduser().resolve() if args.sessions_dir else None
    state, summary = sync_session_logs(root, apply_stop_decay=not args.no_stop_decay)
    if args.json:
        print(json.dumps({"state": state, "summary": summary}, indent=2, sort_keys=True))
    else:
        print_sync_summary(state, summary)
    return 0


def do_watch(args: argparse.Namespace) -> int:
    root = Path(args.sessions_dir).expanduser().resolve() if args.sessions_dir else None
    interval = max(1.0, float(args.interval))
    print(f"Watching Codex session logs every {interval:g}s. Press Ctrl+C to stop.")
    try:
        while True:
            state, summary = sync_session_logs(root, apply_stop_decay=not args.no_stop_decay)
            if summary["lines"]:
                print_sync_summary(state, summary)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("Stopped Codex Tomogatchi watcher.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Codex Tomogatchi MVP CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status", help="Show the current pet state")
    status.add_argument("--json", action="store_true", help="Print raw JSON state")
    status.set_defaults(func=do_status)

    care = sub.add_parser("care", help="Care for the pet")
    care.add_argument("kind", choices=("feed", "rest", "play", "comfort"))
    care.set_defaults(func=do_care)

    install = sub.add_parser("install", help="Install the current stage into CODEX_HOME pets")
    install.add_argument("--stage", choices=STAGES)
    install.set_defaults(func=do_install)

    install_stage_parser = sub.add_parser("install-stage", help="Install a specific stage into CODEX_HOME pets")
    install_stage_parser.add_argument("stage", choices=STAGES)
    install_stage_parser.set_defaults(func=do_install)

    evolve = sub.add_parser("evolve", help="Check and apply evolution thresholds")
    evolve.add_argument("--check", action="store_true", help="Compatibility flag; evolution is always checked")
    evolve.set_defaults(func=do_evolve)

    profile = sub.add_parser("profile", help="Show evolution path, care mistakes, care points, and focus points")
    profile.add_argument("--json", action="store_true", help="Print raw evolution JSON")
    profile.set_defaults(func=do_profile)

    care_call = sub.add_parser("care-call", help="Check or force a care call")
    care_call.add_argument("--force", choices=CARE_KINDS, help="Force a care call for testing")
    care_call.add_argument("--json", action="store_true", help="Print raw care-call JSON")
    care_call.set_defaults(func=do_care_call)

    doctor = sub.add_parser("doctor", help="Check local setup health and common missing pieces")
    doctor.add_argument("--json", action="store_true", help="Print raw doctor checks")
    doctor.set_defaults(func=do_doctor)

    backup = sub.add_parser("backup", help="Create, list, and restore local state/settings backups")
    backup_sub = backup.add_subparsers(dest="backup_command", required=True)

    backup_create = backup_sub.add_parser("create", help="Create a privacy-safe state/settings backup")
    backup_create.add_argument("--output", help="Output zip path or directory")
    backup_create.set_defaults(func=do_backup_create)

    backup_list = backup_sub.add_parser("list", help="List local Tomogatchi backups")
    backup_list.add_argument("--json", action="store_true", help="Print raw backup list")
    backup_list.set_defaults(func=do_backup_list)

    backup_restore = backup_sub.add_parser("restore", help="Restore a backup zip")
    backup_restore.add_argument("source", help="Backup zip to restore")
    backup_restore.add_argument("--confirm", action="store_true", help="Confirm replacing current state/settings")
    backup_restore.set_defaults(func=do_backup_restore)

    settings = sub.add_parser("settings", help="Show or update Tomogatchi settings")
    settings.add_argument("--json", action="store_true", help="Print raw settings JSON")
    settings.add_argument("--init", action="store_true", help="Write default settings if missing")
    settings.add_argument("key", nargs="?", help="Optional section.key setting to update")
    settings.add_argument("value", nargs="?", help="Value to set when key is provided")
    settings.set_defaults(func=do_settings)

    pets = sub.add_parser("pets", help="Import, list, and select custom pet packs")
    pets_sub = pets.add_subparsers(dest="pets_command", required=True)

    pets_list = pets_sub.add_parser("list", help="List installed pet packs")
    pets_list.add_argument("--json", action="store_true", help="Print raw pet-pack JSON")
    pets_list.set_defaults(func=do_pets_list)

    pets_forms = pets_sub.add_parser("forms", help="List forms in the active or selected pet pack")
    pets_forms.add_argument("--pack-id", help="Installed pack id to inspect instead of the active pack")
    pets_forms.add_argument("--json", action="store_true", help="Print raw form JSON")
    pets_forms.set_defaults(func=do_pets_forms)

    pets_import = pets_sub.add_parser("import", help="Import a pet-pack folder or zip")
    pets_import.add_argument("source", help="Path to a pet-pack folder or .zip archive")
    pets_import.add_argument("--replace", action="store_true", help="Replace an installed pack with the same id")
    pets_import.add_argument("--select", action="store_true", help="Select the pack after importing it")
    pets_import.set_defaults(func=do_pets_import)

    pets_validate = pets_sub.add_parser("validate", help="Validate a pet-pack folder or zip before importing")
    pets_validate.add_argument("source", help="Path to a pet-pack folder or .zip archive")
    pets_validate.add_argument("--json", action="store_true", help="Print raw validation summary")
    pets_validate.set_defaults(func=do_pets_validate)

    pets_export = pets_sub.add_parser("export", help="Export an installed custom pet pack to a zip")
    pets_export.add_argument("pack_id", help="Installed custom pet pack id")
    pets_export.add_argument("--output", help="Output zip path or directory")
    pets_export.set_defaults(func=do_pets_export)

    pets_select = pets_sub.add_parser("select", help="Select an installed pet pack")
    pets_select.add_argument("pack_id", help="Installed pack id, or 'default' for bundled pets")
    pets_select.set_defaults(func=do_pets_select)

    pets_hatch = pets_sub.add_parser("hatch", help="Choose a baby form in the active branching pack and reset from now")
    pets_hatch.add_argument("form_id", help="Baby form id from 'pets forms'")
    pets_hatch.add_argument(
        "--include-history",
        action="store_true",
        help="Allow existing session-log history to replay after hatching",
    )
    pets_hatch.add_argument("--sessions-dir", help="Override the Codex sessions directory for the default from-now checkpoint")
    pets_hatch.set_defaults(func=do_pets_hatch)

    reset = sub.add_parser("reset", help="Reset local Tomogatchi state")
    reset.add_argument("--confirm", action="store_true")
    reset.add_argument("--from-now", action="store_true", help="Skip existing session-log history after resetting")
    reset.add_argument("--sessions-dir", help="Override the Codex sessions directory when using --from-now")
    reset.set_defaults(func=do_reset)

    hook = sub.add_parser("hook", help="Record a Codex hook event")
    hook.add_argument("event", choices=("SessionStart", "UserPromptSubmit", "PostToolUse", "Stop"))
    hook.set_defaults(func=do_hook)

    sync = sub.add_parser("sync", help="Sync activity from Codex session logs")
    sync.add_argument("--sessions-dir", help="Override the Codex sessions directory")
    sync.add_argument("--no-stop-decay", action="store_true", help="Do not apply one light decay after new log activity")
    sync.add_argument("--json", action="store_true", help="Print raw JSON state and sync summary")
    sync.set_defaults(func=do_sync)

    watch = sub.add_parser("watch", help="Continuously sync activity from Codex session logs")
    watch.add_argument("--sessions-dir", help="Override the Codex sessions directory")
    watch.add_argument("--interval", type=float, default=5.0, help="Polling interval in seconds")
    watch.add_argument("--no-stop-decay", action="store_true", help="Do not apply one light decay after new log activity")
    watch.set_defaults(func=do_watch)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
