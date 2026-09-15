"""Unit tests for Localization (i18n), Photosensitivity Mode, and HUD Scaling."""

from pathlib import Path
import shutil
import tempfile
import unittest
import pygame

from py_noita.rendering.shaders import ShaderPostProcessor
from py_noita.system.localization import Localization, loc
from py_noita.system.settings_manager import SettingsManager
from py_noita.ui.hud import HUD


class TestLocalizationAndAccessibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.filepath = Path(self.temp_dir) / "settings.json"
        self.settings = SettingsManager(filepath=self.filepath)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_localization_bilingual_dictionary(self):
        l = Localization("de")
        self.assertEqual(l.t("menu_title"), "PY-NOITA // MIKROKOSMOS")
        self.assertEqual(l.translate_material(21), "Magensäure")
        self.assertEqual(l.translate_biome_name(2), "Magensäure-Kavernen")

        # Switch to English
        l.set_language("en")
        self.assertEqual(l.t("menu_title"), "PY-NOITA // MICROCOSM")
        self.assertEqual(l.translate_material(21), "Gastric Acid")
        self.assertEqual(l.translate_biome_name(2), "Gastric Acid Caverns")

        # Formatting parameters
        msg = l.t("hud_depth", depth=450)
        self.assertEqual(msg, "DEPTH: 450m")

    def test_photosensitivity_mode_in_post_processor(self):
        pp = ShaderPostProcessor(320, 180)
        self.assertFalse(pp.photosensitivity_mode)

        # Standard mode: explosion causes chromatic aberration spike
        pp.trigger_detonation(160, 90, 0, 0, power=40.0)
        self.assertGreater(pp.chromatic_aberration, 0.5)

        # Enable photosensitivity mode
        pp.photosensitivity_mode = True
        pp.trigger_detonation(160, 90, 0, 0, power=40.0)
        self.assertEqual(pp.chromatic_aberration, 0.0)

        # Low-HP pulse suppression: standard pulsates, photosensitive is clamped and non-strobing
        pp.update(0.016, heat_val=0.0, acid_val=0.0, player_hp_ratio=0.10)
        self.assertEqual(pp.low_hp_pulse, 0.25)

    def test_hud_scaling(self):
        hud_1080 = HUD(scale=1.0)
        font_size_1080 = hud_1080.font.get_height()

        hud_4k = HUD(scale=2.0)
        font_size_4k = hud_4k.font.get_height()

        self.assertGreater(font_size_4k, font_size_1080)

        # Dynamic set_scale
        hud_1080.set_scale(1.5)
        self.assertGreater(hud_1080.font.get_height(), font_size_1080)

    def test_settings_persistence_of_accessibility(self):
        self.settings.language = "en"
        self.settings.photosensitivity_mode = True
        self.settings.hud_scale = 1.5
        self.settings.save()

        # Reload
        reloaded = SettingsManager(filepath=self.filepath)
        self.assertEqual(reloaded.language, "en")
        self.assertTrue(reloaded.photosensitivity_mode)
        self.assertAlmostEqual(reloaded.hud_scale, 1.5, places=2)
        self.assertEqual(loc.get_language(), "en")


if __name__ == "__main__":
    unittest.main()
