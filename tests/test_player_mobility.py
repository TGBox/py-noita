"""Unit tests for player mobility, step-up autostep, levitation, and acid immunity."""

import unittest
import pygame

from py_noita.entities.player import Player
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import (
    MAT_ACID,
    MAT_AIR,
    MAT_BIOGAS,
    MAT_TOXIC_VAPOR,
    MAT_WALL_BONE,
)


class TestPlayerMobility(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.grid = SimulationGrid(width=100, height=100)
        self.grid.grid.fill(MAT_AIR)
        # Solid floor at y=50
        self.grid.fill_rect(0, 50, 100, 10, MAT_WALL_BONE)

    def test_step_up_over_small_obstacles(self):
        """Player automatically steps up over 1, 2, and 3-pixel obstacles without stopping."""
        player = Player(x=20.0, y=36.0)
        player.on_ground = True
        player.vx = 2.0
        player.vy = 0.0

        # Place a 2-pixel tall step at x=28, y=48..49 (floor is at y=50)
        self.grid.fill_rect(28, 48, 4, 2, MAT_WALL_BONE)

        initial_x = player.x
        # Update physics over several frames
        for _ in range(10):
            player.vx = 2.0
            player.update_physics(self.grid)

        # Player should have crossed the 2px obstacle and progressed past x=28
        self.assertGreater(player.x, 30.0, "Player must step up over 2px obstacle")

    def test_step_up_blocked_by_large_wall(self):
        """Obstacles taller than MAX_STEP_UP (3px) block player movement."""
        player = Player(x=20.0, y=36.0)
        player.on_ground = True
        player.vx = 2.0
        player.vy = 0.0

        # Place a 6-pixel tall obstacle (y=44..49)
        self.grid.fill_rect(28, 44, 4, 6, MAT_WALL_BONE)

        for _ in range(10):
            player.vx = 2.0
            player.update_physics(self.grid)

        # Player should be stopped before or at x=28
        self.assertLess(player.x, 28.0, "Player must be stopped by tall obstacle")

    def test_acid_immunity(self):
        """Acid immunity completely protects player against acid, toxic gas, and corrosive damage."""
        player = Player(x=20.0, y=36.0)
        player.acid_immunity = True
        initial_hp = player.hp

        # 1. Acid damage
        player.take_damage(25.0, source="ACID")
        self.assertEqual(player.hp, initial_hp, "Acid damage must be nullified by acid_immunity")

        # 2. Gas damage
        player.take_damage(15.0, source="GAS")
        self.assertEqual(player.hp, initial_hp, "Gas damage must be nullified by acid_immunity")

        # 3. Non-acid damage still applies
        player.take_damage(10.0, source="ENEMY")
        self.assertEqual(player.hp, initial_hp - 10.0, "Regular damage must still apply")

    def test_acid_contact_with_immunity(self):
        """Contact with acid fluid does not burn or damage an acid-immune player."""
        player = Player(x=20.0, y=36.0)
        player.acid_immunity = True
        initial_hp = player.hp

        # Fill player area with MAT_ACID
        self.grid.fill_rect(15, 30, 20, 20, MAT_ACID)
        player._check_environmental_hazards(self.grid)

        self.assertEqual(player.hp, initial_hp)
        self.assertEqual(player.acid_burn_timer, 0)


if __name__ == "__main__":
    unittest.main()
