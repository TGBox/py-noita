"""Unit tests for environmental acoustics, liquid low-pass filtering, cave reverb, and low-HP heartbeat."""

import unittest
import numpy as np
import pygame

from py_noita.audio.acoustics import (
    AcousticsEngine,
    iir_lowpass_filter_1d,
    comb_reverb_filter_1d,
    synth_heartbeat_thump,
)
from py_noita.audio.audio_manager import AudioManager
from py_noita.entities.player import Player
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import MAT_AIR, MAT_BLOOD, MAT_ACID, MAT_BONE


class TestAcoustics(unittest.TestCase):
    def setUp(self):
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            except Exception:
                pass

    def test_lowpass_filter_dsp(self):
        """Verify 1-pole IIR lowpass filter attenuates high frequencies."""
        sr = 44100
        t = np.linspace(0, 0.05, int(sr * 0.05), endpoint=False)
        # High frequency sine wave (5000 Hz)
        high_freq = np.sin(2 * np.pi * 5000.0 * t).astype(np.float32)
        # Low cutoff alpha
        filtered = iir_lowpass_filter_1d(high_freq, alpha=0.04)

        # Filtered signal amplitude should be substantially lower than original
        self.assertLess(np.max(np.abs(filtered[200:])), np.max(np.abs(high_freq)) * 0.4)

    def test_comb_reverb_filter_dsp(self):
        """Verify comb filter creates decaying feedback echoes from an impulse."""
        buf = np.zeros(2000, dtype=np.float32)
        buf[0] = 1.0  # Unit impulse
        delay = 200
        reverbed = comb_reverb_filter_1d(buf, delay_samples=delay, feedback=0.5, wet=0.5)

        # Check that an echo exists at index 200
        self.assertGreater(abs(reverbed[delay]), 0.15)
        # And next echo at 400 with decay
        self.assertGreater(abs(reverbed[delay * 2]), 0.05)
        self.assertLess(abs(reverbed[delay * 2]), abs(reverbed[delay]))

    def test_heartbeat_synthesis(self):
        """Verify procedural heartbeat thump sound synthesis."""
        sound = synth_heartbeat_thump(pitch=50.0, duration=0.2)
        self.assertIsInstance(sound, pygame.mixer.Sound)
        self.assertGreater(sound.get_length(), 0.15)

    def test_submergence_detection_and_muffling(self):
        """Verify liquid submergence increases submerged_factor and muffles high end."""
        engine = AcousticsEngine()
        grid = SimulationGrid(100, 100)
        player = Player(40, 40)

        # In air: dry factor is 0
        engine.update(0.1, player, grid)
        self.assertAlmostEqual(engine.submerged_factor, 0.0, places=1)

        # Fill surroundings with blood
        for x in range(35, 55):
            for y in range(35, 60):
                grid.set_material(x, y, MAT_BLOOD)

        # Update several ticks in liquid
        for _ in range(15):
            engine.update(0.1, player, grid)

        self.assertGreater(engine.submerged_factor, 0.8)

        # Check music modifiers: drums should be heavily muffled, bass boosted
        amb, bass, drums, tex, duck = engine.get_music_modifiers()
        self.assertLess(drums, 0.35)
        self.assertGreater(bass, 1.15)

    def test_cavern_openness_reverb(self):
        """Verify cavern reverb increases in large open chambers compared to solid tunnels."""
        engine_tunnel = AcousticsEngine()
        grid_tunnel = SimulationGrid(120, 120)
        # Fill whole grid with dense bone rock
        for x in range(120):
            for y in range(120):
                grid_tunnel.set_material(x, y, MAT_BONE)

        player = Player(50, 50)
        for _ in range(10):
            engine_tunnel.update(0.1, player, grid_tunnel)

        # In dense rock tunnel, reverb should be near zero
        self.assertLess(engine_tunnel.cavern_reverb_wet, 0.15)

        # In large open air cavern
        engine_cavern = AcousticsEngine()
        grid_cavern = SimulationGrid(120, 120)  # default is MAT_AIR
        for _ in range(15):
            engine_cavern.update(0.1, player, grid_cavern)

        self.assertGreater(engine_cavern.cavern_reverb_wet, 0.6)

    def test_low_hp_heartbeat_ducking(self):
        """Verify low HP (<25%) activates heartbeat loop and sidechain audio ducking."""
        engine = AcousticsEngine()
        player = Player(50, 50)
        grid = SimulationGrid(100, 100)

        # Full HP: no heartbeat, ducking is 1.0
        player.hp = player.max_hp
        for _ in range(5):
            engine.update(0.1, player, grid)
        self.assertFalse(engine.heartbeat_active)
        self.assertAlmostEqual(engine.heartbeat_ducking, 1.0, places=1)

        # Critical low HP (15 HP out of 100)
        player.hp = 15.0
        # Tick until heart thump triggers
        ducked = False
        for _ in range(30):
            engine.update(0.05, player, grid)
            if engine.heartbeat_ducking < 0.6:
                ducked = True
                break

        self.assertTrue(engine.heartbeat_active)
        self.assertTrue(ducked, "Heartbeat sidechain ducking did not drop volume during thump!")

    def test_audio_manager_acoustics_integration(self):
        """Verify AudioManager updates AcousticsEngine and modulates playback."""
        am = AudioManager()
        self.assertTrue(hasattr(am, "acoustics"))
        self.assertIsInstance(am.acoustics, AcousticsEngine)

        grid = SimulationGrid(60, 60)
        player = Player(25, 25)
        am.update(0.05, player=player, grid=grid)


if __name__ == "__main__":
    unittest.main()
