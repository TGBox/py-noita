"""Unit tests for the multi-track adaptive bio-horror soundtrack engine."""

import unittest
import pygame
import numpy as np

from py_noita.audio.music_engine import (
    AdaptiveMusicEngine,
    synth_biome_track,
    THEME_INCUBATION,
    THEME_BOSS,
    CHANNEL_AMBIENT,
    CHANNEL_BASS,
    CHANNEL_DRUMS,
    CHANNEL_TEXTURE,
)
from py_noita.audio.audio_manager import AudioManager


class TestAdaptiveMusic(unittest.TestCase):
    def setUp(self):
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            except Exception:
                pass

    def test_procedural_stem_synthesis(self):
        """Verify that all 4 stem types synthesize cleanly for biomes, sanctuary, and boss."""
        for theme_id in [0, 2, 6, THEME_INCUBATION, THEME_BOSS]:
            for stem_type in ["ambient", "bass", "drums", "texture"]:
                sound = synth_biome_track(theme_id, stem_type, duration=0.5)
                self.assertIsInstance(sound, pygame.mixer.Sound)
                self.assertGreater(sound.get_length(), 0.4)

    def test_music_engine_transitions(self):
        """Verify biome theme transitions and channel playback initialization."""
        engine = AdaptiveMusicEngine()
        if not engine.initialized:
            self.skipTest("Mixer not available in environment")

        engine.set_theme(0)
        self.assertEqual(engine.current_theme, 0)
        self.assertIn("ambient", engine.current_stems)
        self.assertIn("drums", engine.current_stems)

        # Transition to incubation sanctuary
        engine.set_theme(THEME_INCUBATION)
        self.assertEqual(engine.current_theme, THEME_INCUBATION)

        # Transition to boss theme
        engine.set_theme(THEME_BOSS)
        self.assertEqual(engine.current_theme, THEME_BOSS)

        engine.stop_all()

    def test_combat_intensity_crossfading(self):
        """Verify combat intensity ramps drum and bass stems smoothly."""
        engine = AdaptiveMusicEngine()
        if not engine.initialized:
            self.skipTest("Mixer not available in environment")

        engine.set_theme(1)
        engine.set_combat_intensity(0.0)
        engine.update(1.0)
        self.assertLess(engine.vol_drums, 0.2)

        # Trigger combat: drums should ramp up rapidly
        engine.set_combat_intensity(1.0)
        for _ in range(10):
            engine.update(0.1)

        self.assertGreater(engine.vol_drums, 0.7)

        # Exit combat: drums fade out smoothly
        engine.set_combat_intensity(0.0)
        for _ in range(30):
            engine.update(0.1)

        self.assertLess(engine.vol_drums, 0.15)
        engine.stop_all()

    def test_audio_manager_integration(self):
        """Verify AudioManager controls and updates the adaptive music engine."""
        am = AudioManager()
        self.assertTrue(hasattr(am, "music"))
        self.assertIsInstance(am.music, AdaptiveMusicEngine)
        if am.music.initialized:
            am.music.set_theme(2)
            self.assertEqual(am.music.current_theme, 2)
            am.update(0.05)
            am.music.stop_all()


if __name__ == "__main__":
    unittest.main()
