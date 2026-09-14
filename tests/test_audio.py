"""Unit tests for procedural audio synthesizer."""

import unittest
import pygame

from py_noita.audio.sound_synth import (
    synth_acid_sizzle,
    synth_bone_crack,
    synth_explosion,
    synth_pickup,
    synth_shot,
    synth_squelch,
)
from py_noita.audio.audio_manager import AudioManager


class TestAudio(unittest.TestCase):
    def setUp(self):
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

    def test_sound_synthesis(self):
        """Verify procedural sounds synthesize without errors into valid Sound objects."""
        s1 = synth_squelch()
        self.assertIsInstance(s1, pygame.mixer.Sound)
        self.assertGreater(s1.get_length(), 0.05)

        s2 = synth_acid_sizzle()
        self.assertIsInstance(s2, pygame.mixer.Sound)

        s3 = synth_explosion()
        self.assertIsInstance(s3, pygame.mixer.Sound)
        self.assertGreater(s3.get_length(), 0.3)

        s4 = synth_shot()
        self.assertIsInstance(s4, pygame.mixer.Sound)

        s5 = synth_bone_crack()
        self.assertIsInstance(s5, pygame.mixer.Sound)

        s6 = synth_pickup()
        self.assertIsInstance(s6, pygame.mixer.Sound)

    def test_audio_manager(self):
        """Verify audio manager initializes and caches all sound effects."""
        am = AudioManager()
        self.assertTrue(am.initialized)
        self.assertIn("explosion", am.sounds)
        self.assertIn("acid", am.sounds)


if __name__ == "__main__":
    unittest.main()
