from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "codex-tomogatchi" / "scripts" / "tomogatchi.py"
spec = importlib.util.spec_from_file_location("tomogatchi", SCRIPT)
tomogatchi = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(tomogatchi)


class TomogatchiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.state = self.root / "state.json"
        self.settings = self.root / "settings.json"
        self.sessions = self.root / "sessions"
        self.pet_dir = self.root / "pets" / "codex-tomogatchi"
        self.baby_pet_dir = self.root / "pets" / "codex-tomogatchi-baby"
        self.teen_pet_dir = self.root / "pets" / "codex-tomogatchi-teen"
        self.adult_pet_dir = self.root / "pets" / "codex-tomogatchi-adult"
        self.config = self.root / "codex-home" / "config.toml"
        self.env = patch.dict(
            os.environ,
            {
                "CODEX_TOMOGATCHI_STATE": str(self.state),
                "CODEX_TOMOGATCHI_SETTINGS": str(self.settings),
                "CODEX_TOMOGATCHI_PET_DIR": str(self.pet_dir),
                "CODEX_TOMOGATCHI_SESSIONS_DIR": str(self.sessions),
                "CODEX_HOME": str(self.root / "codex-home"),
            },
            clear=False,
        )
        self.env.start()
        self.addCleanup(self.env.stop)

    def load_json(self) -> dict:
        return json.loads(self.state.read_text(encoding="utf-8"))

    def write_session_log(self, *records: dict) -> Path:
        path = self.sessions / "2026" / "06" / "02" / "rollout-test.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record) + "\n")
        return path

    def test_default_state_shape(self) -> None:
        state = tomogatchi.load_state()
        self.assertEqual(state["schemaVersion"], 1)
        self.assertEqual(state["stage"], "baby")
        self.assertEqual(state["xp"], 0)
        self.assertEqual(set(state["stats"]), {"fullness", "energy", "mood", "stress"})
        self.assertEqual(set(state["counters"]), {"prompts", "sessions", "turns", "toolUses", "successfulTools", "failedTools"})
        self.assertEqual(set(state["branchSignals"]), {"builder", "explorer", "debugger", "reviewer"})
        self.assertEqual(state["assets"]["activePetId"], "codex-tomogatchi-baby")
        self.assertEqual(state["assets"]["selectedAvatarId"], "custom:codex-tomogatchi-baby")
        self.assertEqual(state["turnState"], {"currentTurn": 0, "toolBonusAwardedForTurn": 0})
        self.assertIn("careXpAwarded", state["daily"])
        self.assertEqual(state["lifecycle"]["status"], "alive")
        self.assertIn("lastInteractionAt", state["lifecycle"])
        self.assertIn("deathDueAt", state["lifecycle"])
        self.assertEqual(state["reaction"]["kind"], "")
        self.assertFalse(state["careCall"]["active"])
        self.assertEqual(state["careCall"]["lastStatus"], "none")
        self.assertEqual(state["evolution"]["generation"], 1)
        self.assertEqual(state["evolution"]["formId"], "sparkbit")
        self.assertEqual(state["evolution"]["formName"], "Sparkbit")
        self.assertEqual(state["evolution"]["careMistakes"], 0)
        self.assertEqual(state["evolution"]["careCalls"]["answered"], 0)
        self.assertEqual(state["evolution"]["careCalls"]["missed"], 0)
        self.assertEqual(set(state["evolution"]["focusPoints"]), {"builder", "explorer", "debugger", "reviewer"})

    def test_prompt_and_tool_events_update_counters(self) -> None:
        tomogatchi.record_event("SessionStart", {})
        tomogatchi.record_event("UserPromptSubmit", {"prompt": "secret prompt that must not persist"})
        tomogatchi.record_event("PostToolUse", {"tool": "Bash", "command": "do not store me", "success": True})
        state = self.load_json()
        self.assertEqual(state["counters"]["sessions"], 1)
        self.assertEqual(state["counters"]["prompts"], 1)
        self.assertEqual(state["counters"]["turns"], 1)
        self.assertEqual(state["counters"]["toolUses"], 1)
        self.assertEqual(state["counters"]["successfulTools"], 1)
        self.assertEqual(state["xp"], tomogatchi.TURN_XP + tomogatchi.TURN_TOOL_BONUS_XP)
        self.assertEqual(state["reaction"]["kind"], "tool_success")
        self.assertEqual(state["reaction"]["message"], tomogatchi.REACTION_MESSAGES["tool_success"])
        self.assertGreater(state["evolution"]["focusPoints"]["builder"], 0)
        self.assertEqual(state["evolution"]["trainingPoints"]["focus"], 1)

    def test_privacy_drops_raw_payload_text(self) -> None:
        payload = {
            "prompt": "super secret prompt",
            "command": "cat private_file",
            "output": "private output",
            "success": False,
        }
        tomogatchi.record_event("PostToolUse", payload)
        raw_state = self.state.read_text(encoding="utf-8")
        self.assertNotIn("super secret prompt", raw_state)
        self.assertNotIn("cat private_file", raw_state)
        self.assertNotIn("private output", raw_state)
        state = self.load_json()
        self.assertEqual(state["counters"]["failedTools"], 1)
        self.assertGreater(state["stats"]["stress"], 15)
        self.assertEqual(state["reaction"]["kind"], "tool_failure")
        self.assertNotIn("cat private_file", state["reaction"]["message"])
        self.assertEqual(state["evolution"]["trainingPoints"]["recovery"], 1)

    def test_evolution_thresholds(self) -> None:
        state = tomogatchi.load_state()
        state["xp"] = tomogatchi.THRESHOLDS["teen"] - 1
        self.assertFalse(tomogatchi.maybe_evolve(state))
        self.assertEqual(state["stage"], "baby")
        state["xp"] = tomogatchi.THRESHOLDS["teen"]
        self.assertTrue(tomogatchi.maybe_evolve(state))
        self.assertEqual(state["stage"], "teen")
        self.assertEqual(state["evolution"]["assetStage"], "teen")
        self.assertEqual(state["evolution"]["formName"], "Byteclaw")
        state["xp"] = tomogatchi.THRESHOLDS["adult"]
        self.assertTrue(tomogatchi.maybe_evolve(state))
        self.assertEqual(state["stage"], "adult")
        self.assertEqual(state["evolution"]["assetStage"], "adult")
        self.assertEqual(state["evolution"]["formName"], "Coremaw")

    def test_evolution_does_not_skip_stages(self) -> None:
        state = tomogatchi.load_state()
        state["xp"] = tomogatchi.THRESHOLDS["adult"] + 100
        self.assertTrue(tomogatchi.maybe_evolve(state))
        self.assertEqual(state["stage"], "teen")
        self.assertTrue(tomogatchi.maybe_evolve(state))
        self.assertEqual(state["stage"], "adult")

    def test_daily_xp_cap(self) -> None:
        state = tomogatchi.load_state()
        for _ in range(100):
            tomogatchi.add_xp(state, 2)
        self.assertEqual(state["daily"]["xpAwarded"], tomogatchi.DAILY_XP_CAP)
        self.assertEqual(state["xp"], tomogatchi.DAILY_XP_CAP)

    def test_tool_calls_without_prompt_do_not_gain_xp(self) -> None:
        tomogatchi.record_event("PostToolUse", {"tool": "shell_command", "success": True})
        tomogatchi.record_event("PostToolUse", {"tool": "shell_command", "success": True})
        state = self.load_json()
        self.assertEqual(state["counters"]["toolUses"], 2)
        self.assertEqual(state["counters"]["successfulTools"], 2)
        self.assertEqual(state["xp"], 0)

    def test_tool_success_bonus_is_once_per_turn(self) -> None:
        tomogatchi.record_event("UserPromptSubmit", {})
        tomogatchi.record_event("PostToolUse", {"tool": "shell_command", "success": True})
        tomogatchi.record_event("PostToolUse", {"tool": "shell_command", "success": True})
        state = self.load_json()
        self.assertEqual(state["xp"], tomogatchi.TURN_XP + tomogatchi.TURN_TOOL_BONUS_XP)

        tomogatchi.record_event("UserPromptSubmit", {})
        tomogatchi.record_event("PostToolUse", {"tool": "shell_command", "success": True})
        state = self.load_json()
        self.assertEqual(state["xp"], (tomogatchi.TURN_XP + tomogatchi.TURN_TOOL_BONUS_XP) * 2)

    def test_play_care_xp_is_capped_per_day(self) -> None:
        state = tomogatchi.load_state()
        for _ in range(20):
            tomogatchi.change_stats(state, mood=1)
            tomogatchi.add_care_xp(state, 1)
        self.assertEqual(state["daily"]["careXpAwarded"], tomogatchi.CARE_XP_DAILY_CAP)
        self.assertEqual(state["xp"], tomogatchi.CARE_XP_DAILY_CAP)

    def test_lifecycle_dies_after_neglect(self) -> None:
        state = tomogatchi.load_state()
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        state["lifecycle"]["lastInteractionAt"] = tomogatchi.to_iso(start)

        change = tomogatchi.apply_lifecycle(state, start + timedelta(seconds=tomogatchi.NEGLECT_DEATH_SECONDS + 1))

        self.assertEqual(change, "died")
        self.assertEqual(state["lifecycle"]["status"], "dead")
        self.assertEqual(state["lifecycle"]["diedAt"], tomogatchi.to_iso(start + timedelta(seconds=tomogatchi.NEGLECT_DEATH_SECONDS)))
        self.assertEqual(
            state["lifecycle"]["rebirthDueAt"],
            tomogatchi.to_iso(start + timedelta(seconds=tomogatchi.NEGLECT_DEATH_SECONDS + tomogatchi.REBIRTH_SECONDS)),
        )
        self.assertEqual(state["stats"], {"fullness": 0, "energy": 0, "mood": 0, "stress": 100})

    def test_lifecycle_rebirth_returns_to_baby_after_enough_time(self) -> None:
        state = tomogatchi.load_state()
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        state["stage"] = "adult"
        state["xp"] = 999
        state["level"] = 20
        state["counters"]["prompts"] = 12
        state["lifecycle"]["lastInteractionAt"] = tomogatchi.to_iso(start)

        change = tomogatchi.apply_lifecycle(
            state,
            start + timedelta(seconds=tomogatchi.NEGLECT_DEATH_SECONDS + tomogatchi.REBIRTH_SECONDS + 1),
        )

        self.assertEqual(change, "reborn")
        self.assertEqual(state["lifecycle"]["status"], "alive")
        self.assertEqual(state["lifecycle"]["deaths"], 1)
        self.assertEqual(state["lifecycle"]["rebirths"], 1)
        self.assertEqual(state["evolution"]["generation"], 2)
        self.assertEqual(state["evolution"]["formId"], "sparkbit")
        self.assertEqual(state["evolution"]["careMistakes"], 0)
        self.assertEqual(state["stage"], "baby")
        self.assertEqual(state["xp"], 0)
        self.assertEqual(state["level"], 1)
        self.assertEqual(state["stats"], tomogatchi.DEFAULT_STATS)
        self.assertEqual(state["counters"]["prompts"], 12)

    def test_dead_pet_counts_activity_but_does_not_gain_xp(self) -> None:
        state = tomogatchi.load_state()
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        state["lifecycle"]["status"] = "dead"
        state["lifecycle"]["diedAt"] = tomogatchi.to_iso(now)
        state["lifecycle"]["rebirthDueAt"] = tomogatchi.to_iso(now + timedelta(seconds=tomogatchi.REBIRTH_SECONDS))

        evolved = tomogatchi.apply_event(state, "UserPromptSubmit", {})

        self.assertFalse(evolved)
        self.assertEqual(state["lifecycle"]["status"], "dead")
        self.assertEqual(state["counters"]["prompts"], 1)
        self.assertEqual(state["xp"], 0)

    def test_settings_can_change_xp_pace(self) -> None:
        tomogatchi.main(["settings", "xp.pace", "fast"])
        tomogatchi.record_event("UserPromptSubmit", {})
        state = self.load_json()
        self.assertEqual(state["xp"], tomogatchi.effective_xp(tomogatchi.TURN_XP))
        self.assertGreater(state["xp"], tomogatchi.TURN_XP)

    def test_settings_can_disable_death(self) -> None:
        tomogatchi.main(["settings", "lifecycle.deathEnabled", "false"])
        state = tomogatchi.load_state()
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        state["lifecycle"]["lastInteractionAt"] = tomogatchi.to_iso(start)

        change = tomogatchi.apply_lifecycle(
            state,
            start + timedelta(seconds=tomogatchi.NEGLECT_DEATH_SECONDS + tomogatchi.REBIRTH_SECONDS + 1),
        )

        self.assertIsNone(change)
        self.assertEqual(state["lifecycle"]["status"], "alive")

    def test_care_actions_add_generation_care_points(self) -> None:
        before = tomogatchi.load_state()
        tomogatchi.save_state(before)
        tomogatchi.main(["care", "feed"])
        state = self.load_json()
        self.assertEqual(state["evolution"]["carePoints"]["feed"], 1)
        self.assertEqual(state["evolution"]["trainingPoints"]["care"], 1)

    def test_care_call_starts_from_stat_need(self) -> None:
        state = tomogatchi.load_state()
        at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        state["stats"]["fullness"] = 30

        change = tomogatchi.maybe_update_care_call(state, at=at)

        self.assertEqual(change, "started")
        self.assertTrue(state["careCall"]["active"])
        self.assertEqual(state["careCall"]["kind"], "feed")
        self.assertEqual(state["careCall"]["reason"], "hungry")
        self.assertEqual(state["reaction"]["kind"], "care_call")

    def test_matching_care_answers_active_call(self) -> None:
        state = tomogatchi.load_state()
        state["stats"]["fullness"] = 30
        tomogatchi.maybe_update_care_call(state, at=datetime.now(timezone.utc))
        tomogatchi.save_state(state)

        tomogatchi.main(["care", "feed"])
        after = self.load_json()

        self.assertFalse(after["careCall"]["active"])
        self.assertEqual(after["careCall"]["lastStatus"], "answered")
        self.assertEqual(after["evolution"]["careCalls"]["answered"], 1)
        self.assertEqual(after["evolution"]["careCalls"]["byKind"]["feed"], 1)
        self.assertEqual(after["evolution"]["carePoints"]["feed"], 2)
        self.assertEqual(after["reaction"]["kind"], "care_answered")

    def test_expired_care_call_counts_as_missed_mistake(self) -> None:
        state = tomogatchi.load_state()
        at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        state["stats"]["stress"] = 90
        tomogatchi.maybe_update_care_call(state, at=at)

        change = tomogatchi.maybe_update_care_call(
            state,
            at=at + timedelta(seconds=tomogatchi.CARE_CALL_RESPONSE_SECONDS + 1),
        )

        self.assertEqual(change, "missed")
        self.assertFalse(state["careCall"]["active"])
        self.assertEqual(state["careCall"]["lastStatus"], "missed")
        self.assertEqual(state["evolution"]["careCalls"]["missed"], 1)
        self.assertEqual(state["evolution"]["careCalls"]["missedByKind"]["comfort"], 1)
        self.assertEqual(state["evolution"]["mistakesByKind"]["stress"], 1)
        self.assertEqual(state["reaction"]["kind"], "care_miss")

    def test_stat_conditions_add_capped_care_mistakes(self) -> None:
        state = tomogatchi.load_state()
        state["stats"].update({"fullness": 0, "energy": 0, "mood": 0, "stress": 100})

        tomogatchi.record_stat_care_mistakes(state)
        tomogatchi.record_stat_care_mistakes(state)

        self.assertEqual(state["evolution"]["careMistakes"], 3)
        self.assertEqual(state["evolution"]["mistakesByKind"]["neglect"], 1)
        self.assertEqual(state["evolution"]["mistakesByKind"]["overwork"], 1)
        self.assertEqual(state["evolution"]["mistakesByKind"]["stress"], 1)

    def test_evolution_path_prefers_partner_for_good_care(self) -> None:
        state = tomogatchi.load_state()
        for kind in ("feed", "rest", "play", "comfort", "feed", "rest"):
            tomogatchi.add_care_point(state, kind)

        path, reason = tomogatchi.evolution_path_for_state(state)

        self.assertEqual(path, "partner")
        self.assertIn("care", reason)

    def test_evolution_path_prefers_wild_for_care_mistakes(self) -> None:
        state = tomogatchi.load_state()
        state["evolution"]["careMistakes"] = 5

        path, reason = tomogatchi.evolution_path_for_state(state)

        self.assertEqual(path, "wild")
        self.assertIn("mistakes", reason)

    def test_evolution_path_prefers_wild_for_missed_calls(self) -> None:
        state = tomogatchi.load_state()
        state["evolution"]["careCalls"]["missed"] = 3

        path, reason = tomogatchi.evolution_path_for_state(state)

        self.assertEqual(path, "wild")
        self.assertIn("mistakes", reason)

    def test_evolution_path_uses_dominant_focus(self) -> None:
        state = tomogatchi.load_state()
        for _ in range(4):
            tomogatchi.add_focus_point(state, "debugger")

        path, reason = tomogatchi.evolution_path_for_state(state)

        self.assertEqual(path, "debugger")
        self.assertIn("debugger", reason)

    def test_prompt_reaction_stores_no_prompt_text(self) -> None:
        tomogatchi.record_event("UserPromptSubmit", {"prompt": "private idea"})
        state = self.load_json()
        self.assertEqual(state["reaction"]["kind"], "prompt")
        self.assertNotIn("private idea", self.state.read_text(encoding="utf-8"))

    def test_session_log_test_reactions_keep_output_private(self) -> None:
        self.write_session_log(
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call",
                    "call_id": "call_test",
                    "name": "shell_command",
                    "arguments": "pytest secret_suite",
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call_output",
                    "call_id": "call_test",
                    "output": "Exit code: 0\nOutput:\n17 passed secret output",
                },
            },
        )

        state, summary = tomogatchi.sync_session_logs(apply_stop_decay=False)

        self.assertEqual(summary["tools"], 1)
        self.assertEqual(state["reaction"]["kind"], "test_pass")
        raw_state = self.state.read_text(encoding="utf-8")
        self.assertNotIn("secret_suite", raw_state)
        self.assertNotIn("secret output", raw_state)

    def test_care_action_changes_stats(self) -> None:
        before = tomogatchi.load_state()
        tomogatchi.save_state(before)
        tomogatchi.main(["care", "feed"])
        after = self.load_json()
        self.assertGreater(after["stats"]["fullness"], before["stats"]["fullness"])

    def test_install_stage_writes_active_pet_manifest(self) -> None:
        self.pet_dir.mkdir(parents=True)
        (self.pet_dir / "pet.json").write_text(
            json.dumps({"id": "codex-tomogatchi", "spritesheetPath": "spritesheet.webp"}),
            encoding="utf-8",
        )
        (self.pet_dir / "spritesheet.webp").write_text("old mirror", encoding="utf-8")

        tomogatchi.install_stage("baby")
        manifest = json.loads((self.baby_pet_dir / "pet.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["id"], "codex-tomogatchi-baby")
        self.assertEqual(manifest["spritesheetPath"], "spritesheet-baby.webp")
        self.assertTrue((self.baby_pet_dir / "spritesheet-baby.webp").exists())

        self.assertFalse(self.pet_dir.exists())
        self.assertTrue(self.teen_pet_dir.exists())
        self.assertTrue(self.adult_pet_dir.exists())
        self.assertIn('selected-avatar-id = "custom:codex-tomogatchi-baby"', self.config.read_text(encoding="utf-8"))

    def test_install_stage_switches_selected_avatar_config(self) -> None:
        self.config.parent.mkdir(parents=True, exist_ok=True)
        self.config.write_text("[desktop]\nconversationDetailMode = \"STEPS_COMMANDS\"\n", encoding="utf-8")
        tomogatchi.install_stage("teen")

        state = self.load_json()
        self.assertEqual(state["assets"]["activePetId"], "codex-tomogatchi-teen")
        self.assertEqual(state["assets"]["selectedAvatarId"], "custom:codex-tomogatchi-teen")
        self.assertEqual(Path(state["assets"]["installedPetPath"]), self.teen_pet_dir)
        config_text = self.config.read_text(encoding="utf-8")
        self.assertIn('conversationDetailMode = "STEPS_COMMANDS"', config_text)
        self.assertIn('selected-avatar-id = "custom:codex-tomogatchi-teen"', config_text)

    def test_session_log_sync_updates_counters_once_and_keeps_privacy(self) -> None:
        self.write_session_log(
            {"type": "session_meta", "payload": {"source": "exec"}},
            {"type": "event_msg", "payload": {"type": "user_message", "message": "secret prompt"}},
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call",
                    "call_id": "call_1",
                    "name": "shell_command",
                    "arguments": "secret command",
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call_output",
                    "call_id": "call_1",
                    "output": "Exit code: 1\nOutput:\nsecret output",
                },
            },
        )

        state, summary = tomogatchi.sync_session_logs(apply_stop_decay=False)
        self.assertEqual(summary["sessions"], 1)
        self.assertEqual(summary["prompts"], 1)
        self.assertEqual(summary["tools"], 1)
        self.assertEqual(summary["failedTools"], 1)
        self.assertEqual(state["counters"]["sessions"], 1)
        self.assertEqual(state["counters"]["prompts"], 1)
        self.assertEqual(state["counters"]["toolUses"], 1)
        self.assertEqual(state["counters"]["failedTools"], 1)

        raw_state = self.state.read_text(encoding="utf-8")
        self.assertNotIn("secret prompt", raw_state)
        self.assertNotIn("secret command", raw_state)
        self.assertNotIn("secret output", raw_state)

        state_again, summary_again = tomogatchi.sync_session_logs(apply_stop_decay=False)
        self.assertEqual(summary_again["lines"], 0)
        self.assertEqual(state_again["counters"], state["counters"])

    def test_reset_from_now_skips_existing_session_log_history(self) -> None:
        self.write_session_log(
            {"type": "session_meta", "payload": {"source": "exec"}},
            {"type": "event_msg", "payload": {"type": "user_message", "message": "old prompt"}},
        )

        tomogatchi.main(["reset", "--confirm", "--from-now"])
        state, summary = tomogatchi.sync_session_logs(apply_stop_decay=False)
        self.assertEqual(summary["lines"], 0)
        self.assertEqual(state["stage"], "baby")
        self.assertEqual(state["xp"], 0)
        self.assertEqual(state["counters"]["prompts"], 0)

        self.write_session_log({"type": "event_msg", "payload": {"type": "user_message", "message": "new prompt"}})
        state, summary = tomogatchi.sync_session_logs(apply_stop_decay=False)
        self.assertEqual(summary["lines"], 1)
        self.assertEqual(state["counters"]["prompts"], 1)
        self.assertEqual(state["xp"], tomogatchi.TURN_XP)


if __name__ == "__main__":
    unittest.main()
