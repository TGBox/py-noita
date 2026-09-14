"""Unit tests for 3D stereo panning and exponential distance attenuation."""

import unittest
import math
import pygame

from py_noita.audio.spatial import (
    SpatialAudioEngine,
    calculate_stereo_panning,
    calculate_distance_attenuation,
    compute_spatial_volumes,
)
from py_noita.audio.audio_manager import AudioManager


class TestSpatialAudio(unittest.TestCase):
    def setUp(self):
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            except Exception:
                pass

    def test_equal_power_panning_law(self):
        """Verify stereo panning obeys equal power law (left^2 + right^2 == 1.0)."""
        # Full left
        l, r = calculate_stereo_panning(-300.0, pan_width=260.0)
        self.assertAlmostEqual(l, 1.0, places=3)
        self.assertAlmostEqual(r, 0.0, places=3)

        # Full right
        l, r = calculate_stereo_panning(300.0, pan_width=260.0)
        self.assertAlmostEqual(l, 0.0, places=3)
        self.assertAlmostEqual(r, 1.0, places=3)

        # Center
        l, r = calculate_stereo_panning(0.0, pan_width=260.0)
        self.assertAlmostEqual(l, r, places=3)
        self.assertAlmostEqual(l**2 + r**2, 1.0, places=3)

        # Intermediate angles
        for dx in [-200, -100, -50, 50, 100, 200]:
            left, right = calculate_stereo_panning(float(dx), pan_width=260.0)
            power = left**2 + right**2
            self.assertAlmostEqual(power, 1.0, places=3)

    def test_distance_attenuation(self):
        """Verify exponential distance attenuation curve."""
        # Within min distance: full volume
        self.assertEqual(calculate_distance_attenuation(20.0, min_distance=40.0, max_distance=600.0), 1.0)
        self.assertEqual(calculate_distance_attenuation(40.0, min_distance=40.0, max_distance=600.0), 1.0)

        # Beyond max distance: complete silence
        self.assertEqual(calculate_distance_attenuation(650.0, min_distance=40.0, max_distance=600.0), 0.0)

        # Monotonically decreasing
        d1 = calculate_distance_attenuation(100.0, min_distance=40.0, max_distance=600.0)
        d2 = calculate_distance_attenuation(250.0, min_distance=40.0, max_distance=600.0)
        d3 = calculate_distance_attenuation(450.0, min_distance=40.0, max_distance=600.0)

        self.assertGreater(d1, d2)
        self.assertGreater(d2, d3)
        self.assertGreater(d3, 0.0)

    def test_compute_spatial_volumes(self):
        """Verify stereo channel volume distribution in 2D space."""
        # Sound at player pos
        vl, vr = compute_spatial_volumes(100.0, 100.0, 100.0, 100.0, base_volume=1.0)
        self.assertAlmostEqual(vl, vr, places=2)
        self.assertGreater(vl, 0.6)

        # Sound directly to the left (50px left)
        vl, vr = compute_spatial_volumes(50.0, 100.0, 100.0, 100.0, base_volume=1.0)
        self.assertGreater(vl, vr)

        # Sound directly to the right (50px right)
        vl, vr = compute_spatial_volumes(150.0, 100.0, 100.0, 100.0, base_volume=1.0)
        self.assertGreater(vr, vl)

        # Sound beyond maximum hearing distance
        vl, vr = compute_spatial_volumes(1000.0, 100.0, 100.0, 100.0, base_volume=1.0, max_dist=600.0)
        self.assertEqual(vl, 0.0)
        self.assertEqual(vr, 0.0)

    def test_audio_manager_play_spatial(self):
        """Verify AudioManager play_spatial method handles coordinates properly."""
        am = AudioManager()
        self.assertTrue(hasattr(am, "spatial"))
        self.assertIsInstance(am.spatial, SpatialAudioEngine)

        # Play sound to the left
        ch = am.play_spatial("explosion", world_x=50.0, world_y=100.0, listener_x=150.0, listener_y=100.0)
        # Verify it succeeds without exception
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
