"""Unit tests for player bio-status effects, physical reactions, and dynamic mutations."""

import math
import unittest
import pygame

from py_noita.entities.player import Player
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import (
    MAT_ACID,
    MAT_AIR,
    MAT_BILE,
    MAT_BIOGAS,
    MAT_BLOOD,
    MAT_FIRE,
    MAT_LYMPH,
    MAT_MUTAGEN,
    MAT_PUS,
    MAT_SPORES,
    MAT_SULFUR_SPORES,
    MAT_TOXIC_VAPOR,
    MAT_WATER,
)


class TestBioStatusEffects(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.grid = SimulationGrid(width=100, height=100)
        self.player = Player(x=50.0, y=50.0)

    def tearDown(self):
        pygame.quit()

    def test_bile_slippery_and_fire_vuln(self):
        """Bile causes low friction sliding and increased fire vulnerability."""
        self.grid.set_pixel(54, 56, MAT_BILE)
        self.player._check_environmental_hazards(self.grid)
        self.assertGreater(self.player.bile_slippery_timer, 0)

        # Apply input and check low friction lerp
        self.player.apply_input(move_x=1.0, hover=False)
        self.assertGreater(self.player.vx, 0.0)

        # Higher damage when on fire
        hp_before = self.player.hp
        self.player.take_damage(10.0, source="FIRE")
        damage_taken = hp_before - self.player.hp
        self.assertAlmostEqual(damage_taken, 15.0)  # 1.5x fire vulnerability

    def test_mutagen_frenzy_and_extra_tentacles(self):
        """Mutagen grants speed boost and activates sprouting extra mini-tentacles."""
        self.grid.set_pixel(54, 56, MAT_MUTAGEN)
        self.player._check_environmental_hazards(self.grid)
        self.assertGreater(self.player.mutagen_frenzy_timer, 0)

        # Normal player move speed vs frenzy
        p_normal = Player(x=20.0, y=20.0)
        p_normal.apply_input(move_x=1.0, hover=False)
        self.player.apply_input(move_x=1.0, hover=False)
        self.assertGreater(self.player.vx, p_normal.vx)

        # Extra tentacles exist and can be updated/drawn
        surface = pygame.Surface((100, 100))
        self.player.update_physics(self.grid)
        self.player.draw(surface, 0, 0)
        self.assertEqual(len(self.player.extra_tentacles), 3)

    def test_spore_booster(self):
        """Spores trigger upward impulse and enhanced levitation."""
        self.grid.set_pixel(54, 56, MAT_SPORES)
        self.player._check_environmental_hazards(self.grid)
        self.assertGreater(self.player.spore_boost_timer, 0)

        # Levitation hover impulse is amplified
        p_normal = Player(x=20.0, y=20.0)
        p_normal.apply_input(move_x=0.0, hover=True)
        self.player.apply_input(move_x=0.0, hover=True)
        self.assertLess(self.player.vy, p_normal.vy)  # More negative = stronger upward thrust

    def test_pus_slow_and_resistance(self):
        """Pus slows player down but grants 20% physical blunt resistance."""
        self.grid.set_pixel(54, 56, MAT_PUS)
        self.player._check_environmental_hazards(self.grid)
        self.assertGreater(self.player.pus_sticky_timer, 0)

        # Move speed is slower than normal
        p_normal = Player(x=20.0, y=20.0)
        p_normal.apply_input(move_x=1.0, hover=False)
        self.player.apply_input(move_x=1.0, hover=False)
        self.assertLess(self.player.vx, p_normal.vx)

        # Damage resistance
        hp_before = self.player.hp
        self.player.take_damage(10.0, source="DAMAGE")
        damage_taken = hp_before - self.player.hp
        self.assertAlmostEqual(damage_taken, 8.0)  # 20% resistance (0.8x)

    def test_gas_exposure(self):
        """Toxic gas accumulates exposure and deals cough damage."""
        self.grid.set_pixel(54, 56, MAT_TOXIC_VAPOR)
        for _ in range(25):
            self.player._check_environmental_hazards(self.grid)
        self.assertGreater(self.player.gas_exposure_timer, 40)

        # Clear gas and step through cough interval ticks
        self.grid.set_pixel(54, 56, MAT_AIR)
        hp_before = self.player.hp
        # Run 25 steps to guarantee crossing a 20-tick cough interval
        for _ in range(25):
            self.player._check_environmental_hazards(self.grid)
        self.assertLess(self.player.hp, hp_before)

    def test_water_cleansing(self):
        """Water and lymph cleanse coatings and status timers."""
        self.player.bile_slippery_timer = 100
        self.player.pus_sticky_timer = 100
        self.player.gas_exposure_timer = 80
        self.player.on_fire = True

        self.grid.set_pixel(54, 56, MAT_WATER)
        self.player._check_environmental_hazards(self.grid)

        self.assertEqual(self.player.bile_slippery_timer, 0)
        self.assertEqual(self.player.pus_sticky_timer, 0)
        self.assertEqual(self.player.gas_exposure_timer, 0)
        self.assertFalse(self.player.on_fire)


if __name__ == "__main__":
    unittest.main()
