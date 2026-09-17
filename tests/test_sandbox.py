"""Unit tests for Bio-Sandbox level generation, TestDummy DPS, and dynamic viewport scaling."""

import unittest
import pygame

from py_noita.rendering.renderer import Renderer
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import (
    MAT_ACID,
    MAT_BLOOD,
    MAT_WALL_BONE,
    MAT_WATER,
)
from py_noita.world.sandbox import TestDummy, generate_sandbox_level


class TestSandboxAndViewport(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.grid = SimulationGrid(width=400, height=250)

    def test_sandbox_level_generation(self):
        """Sandbox level generates indestructible walls, material basins, exit portal, and test dummies."""
        spawn_pos, portal, dummies = generate_sandbox_level(self.grid)

        # 1. Spawn position valid
        self.assertGreater(spawn_pos[0], 0)
        self.assertGreater(spawn_pos[1], 0)

        # 2. Exit portal generated
        self.assertIsNotNone(portal)
        self.assertGreater(portal.x, 0)

        # 3. Dummies generated
        self.assertGreaterEqual(len(dummies), 2)
        for dummy in dummies:
            self.assertIsInstance(dummy, TestDummy)
            self.assertEqual(dummy.enemy_type, "TEST_DUMMY")
            self.assertEqual(dummy.hp, 99999.0)

        # 4. Outer walls are indestructible MAT_WALL_BONE
        self.assertEqual(self.grid.get_pixel(5, 5), MAT_WALL_BONE)
        self.assertEqual(self.grid.get_pixel(self.grid.width - 5, 5), MAT_WALL_BONE)

        # 5. Check presence of material testing pools
        mats_in_grid = set(self.grid.grid.flatten())
        self.assertIn(MAT_WATER, mats_in_grid)
        self.assertIn(MAT_BLOOD, mats_in_grid)
        self.assertIn(MAT_ACID, mats_in_grid)

    def test_test_dummy_dps_tracking(self):
        """TestDummy remains indestructible, tracks total damage and calculates DPS."""
        dummy = TestDummy(100.0, 100.0)
        self.assertEqual(dummy.hp, 99999.0)

        # Hit dummy for 150 damage
        dummy.take_damage(150.0)
        self.assertEqual(dummy.hp, 99999.0, "Dummy must be indestructible")
        self.assertEqual(dummy.total_damage_taken, 150.0)

        # Simulate 1 second elapsed to calculate DPS
        dummy.update(player=None, grid=self.grid, dt=1.0)
        self.assertAlmostEqual(dummy.current_dps, 150.0, delta=1.0)
        self.assertEqual(dummy.dps_damage, 0.0)

    def test_dynamic_viewport_no_black_bars(self):
        """Renderer dynamic viewport fills 100% of target resolution without black borders."""
        renderer = Renderer(screen_res=(1920, 1080))
        # Default fill mode has dest_rect covering full screen
        self.assertEqual(renderer.dest_rect.topleft, (0, 0))
        self.assertEqual(renderer.dest_rect.size, (1920, 1080))

        # Test ultrawide resolution 2560x1080
        renderer.set_resolution((2560, 1080))
        self.assertEqual(renderer.dest_rect.topleft, (0, 0))
        self.assertEqual(renderer.dest_rect.size, (2560, 1080))
        # Viewport width scales dynamically to show wider world
        self.assertGreater(renderer.view_w, 640)

        # Test 1440p resolution 2560x1440
        renderer.set_resolution((2560, 1440))
        self.assertEqual(renderer.dest_rect.topleft, (0, 0))
        self.assertEqual(renderer.dest_rect.size, (2560, 1440))


if __name__ == "__main__":
    unittest.main()
