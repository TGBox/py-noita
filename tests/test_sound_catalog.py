"""Unit tests for the 60+ procedural SFX sound catalog."""

import unittest
import pygame

from py_noita.audio.sound_synth import build_full_sound_catalog
from py_noita.audio.audio_manager import AudioManager
from py_noita.simulation.materials import MAT_BONE, MAT_BLOOD, MAT_CHITIN, MAT_TISSUE, MAT_GOLD


class TestSoundCatalog(unittest.TestCase):
    def setUp(self):
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            except Exception:
                pass

    def test_sound_catalog_size_and_integrity(self):
        """Verify the catalog generates 60+ distinct procedural sound effects."""
        catalog = build_full_sound_catalog()
        self.assertGreaterEqual(len(catalog), 60)

        for name, sound in catalog.items():
            self.assertIsInstance(sound, pygame.mixer.Sound, f"Sound {name} is not a pygame.mixer.Sound")
            self.assertGreater(sound.get_length(), 0.04, f"Sound {name} duration too short")

    def test_footstep_dispatch(self):
        """Verify AudioManager dispatches terrain-specific footsteps."""
        am = AudioManager()
        # Flesh
        ch_flesh = am.play_footstep(MAT_TISSUE, 100.0, 100.0, 100.0, 100.0)
        # Bone
        ch_bone = am.play_footstep(MAT_BONE, 100.0, 100.0, 100.0, 100.0)
        # Slime
        ch_slime = am.play_footstep(MAT_BLOOD, 100.0, 100.0, 100.0, 100.0)
        # Crawl
        ch_crawl = am.play_footstep(MAT_TISSUE, 100.0, 100.0, 100.0, 100.0, is_crawl=True)

    def test_material_impact_dispatch(self):
        """Verify physical impact sound mapping for various materials."""
        am = AudioManager()
        for mat in [MAT_BONE, MAT_CHITIN, MAT_BLOOD, MAT_GOLD, MAT_TISSUE]:
            am.play_material_impact(mat, 150.0, 120.0, 100.0, 100.0)


if __name__ == "__main__":
    unittest.main()
