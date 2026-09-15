"""Unit tests for SteamworksIntegration, Steam Achievements, and Steam Deck profile."""

import os
from pathlib import Path
import shutil
import tempfile
import unittest
import pygame

from py_noita.system.steamworks import (
    ACHIEVEMENT_CATALOG,
    SteamAchievement,
    SteamToastNotification,
    SteamworksIntegration,
)


class TestSteamworks(unittest.TestCase):
    """Test suite for Steamworks integration, achievements, toast notifications, and cloud sync."""

    def setUp(self):
        pygame.init()
        self.temp_dir = tempfile.mkdtemp()
        self.save_dir = Path(self.temp_dir)
        self.steam = SteamworksIntegration(save_dir=self.save_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        pygame.quit()

    def test_achievement_catalog_integrity(self):
        """Verify catalog contains 40 achievements with complete dual-language metadata."""
        self.assertGreaterEqual(len(ACHIEVEMENT_CATALOG), 40)
        seen_ids = set()
        for ach in ACHIEVEMENT_CATALOG:
            self.assertNotIn(ach.id, seen_ids, f"Duplicate achievement ID: {ach.id}")
            seen_ids.add(ach.id)
            self.assertTrue(ach.id.startswith("ACH_"), f"Invalid ID prefix: {ach.id}")
            self.assertTrue(len(ach.name_de) > 0)
            self.assertTrue(len(ach.name_en) > 0)
            self.assertTrue(len(ach.desc_de) > 0)
            self.assertTrue(len(ach.desc_en) > 0)

    def test_unlock_achievement_and_toast(self):
        """Verify unlocking achievement triggers state update and spawns toast notification."""
        self.assertFalse(self.steam.is_achievement_unlocked("ACH_FIRST_KILL"))
        self.assertEqual(len(self.steam.active_toasts), 0)

        # Unlock first time
        unlocked = self.steam.unlock_achievement("ACH_FIRST_KILL")
        self.assertTrue(unlocked)
        self.assertTrue(self.steam.is_achievement_unlocked("ACH_FIRST_KILL"))
        self.assertEqual(len(self.steam.active_toasts), 1)
        toast = self.steam.active_toasts[0]
        self.assertEqual(toast.ach.id, "ACH_FIRST_KILL")

        # Unlock second time (should be idempotent and return False)
        unlocked_again = self.steam.unlock_achievement("ACH_FIRST_KILL")
        self.assertFalse(unlocked_again)
        self.assertEqual(len(self.steam.active_toasts), 1)

        # Unknown ID
        self.assertFalse(self.steam.unlock_achievement("ACH_NONEXISTENT"))

    def test_toast_animation_and_expiry(self):
        """Verify toast notification slides and eventually expires."""
        self.steam.unlock_achievement("ACH_KILLS_50")
        self.assertEqual(len(self.steam.active_toasts), 1)
        toast = self.steam.active_toasts[0]

        # Initial slide_y should be negative (off-screen top)
        self.assertLess(toast.slide_y, 0)

        # Update 0.2s -> slides down toward target_y
        self.steam.update(0.2)
        self.assertGreater(toast.slide_y, -60.0)

        # Fast forward past lifetime (4.5s)
        self.steam.update(5.0)
        self.assertEqual(len(self.steam.active_toasts), 0)

    def test_toast_rendering_both_languages(self):
        """Verify drawing toasts renders without error in DE and EN."""
        surface = pygame.Surface((640, 360))
        self.steam.unlock_achievement("ACH_KILL_WORM")

        # Render in German
        self.steam.draw_toasts(surface, lang="de")
        # Render in English
        self.steam.draw_toasts(surface, lang="en")

    def test_achievements_persistence_and_reload(self):
        """Verify achievements are saved to disk and restored properly."""
        self.steam.unlock_achievement("ACH_SECRET_ORB")
        self.steam.unlock_achievement("ACH_DNA_TABLET")

        # Create a new integration instance pointing to the same save directory
        new_steam = SteamworksIntegration(save_dir=self.save_dir)
        self.assertTrue(new_steam.is_achievement_unlocked("ACH_SECRET_ORB"))
        self.assertTrue(new_steam.is_achievement_unlocked("ACH_DNA_TABLET"))
        self.assertFalse(new_steam.is_achievement_unlocked("ACH_CORE_BOSS"))

        unlocked_cnt, total_cnt = new_steam.get_unlocked_count()
        self.assertEqual(unlocked_cnt, 2)
        self.assertGreaterEqual(total_cnt, 40)

    def test_cloud_save_sync_manifest(self):
        """Verify Steam Cloud sync manifest generates expected metadata."""
        meta = self.steam.sync_cloud_save()
        self.assertIn("last_synced", meta)
        self.assertIn("files_synced", meta)
        self.assertIn("achievements.json", meta["files_synced"])
        self.assertTrue(self.steam.cloud_sync_meta_file.exists())

    def test_steam_deck_profile(self):
        """Verify Steam Deck profile configuration."""
        profile = self.steam.get_steam_deck_profile()
        self.assertEqual(profile["target_fps"], 60)
        self.assertEqual(profile["resolution"], [1280, 800])
        self.assertEqual(profile["window_mode"], "FULLSCREEN")
        self.assertGreater(profile["hud_scale"], 1.0)
        self.assertGreater(profile["gamepad_deadzone"], 0.0)


if __name__ == "__main__":
    unittest.main()
