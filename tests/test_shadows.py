"""Unit tests for Dynamic 2D Raymarched Shadows (Lighting Engine)."""

import math
import unittest
import numpy as np
import pygame

from py_noita.rendering.lighting import (
    COS_TABLE,
    NUM_SHADOW_RAYS,
    SIN_TABLE,
    LightSource,
    LightingEngine,
    raymarch_2d_shadows,
)
from py_noita.simulation.materials import MAT_AIR, MAT_BONE, MAT_TISSUE, PROP_STATE


class TestRaymarched2DShadows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_raymarch_kernel_clear_space(self):
        """In open air, all rays reach the full light radius."""
        grid = np.zeros((100, 100), dtype=np.uint8)
        out_dist = np.zeros(NUM_SHADOW_RAYS, dtype=np.float32)

        raymarch_2d_shadows(grid, PROP_STATE, 50.0, 50.0, 30.0, COS_TABLE, SIN_TABLE, out_dist)

        for d in out_dist:
            self.assertAlmostEqual(d, 30.0)

    def test_raymarch_kernel_wall_occlusion(self):
        """Solid terrain wall obstructs rays in its angular direction."""
        grid = np.zeros((100, 100), dtype=np.uint8)
        # Vertical bone wall at x = 60 (distance 10 from light at 50, 50)
        grid[20:80, 60] = MAT_BONE
        out_dist = np.zeros(NUM_SHADOW_RAYS, dtype=np.float32)

        raymarch_2d_shadows(grid, PROP_STATE, 50.0, 50.0, 30.0, COS_TABLE, SIN_TABLE, out_dist)

        # Ray 0 (facing directly right, angle 0) should hit wall at distance 10
        self.assertAlmostEqual(out_dist[0], 10.0, delta=1.5)

        # Rays facing left (around ray NUM_SHADOW_RAYS // 2) should reach full radius
        self.assertAlmostEqual(out_dist[NUM_SHADOW_RAYS // 2], 30.0)

    def test_lighting_engine_renders_soft_shadow(self):
        """LightingEngine renders shadowed light where space behind solid wall remains dark."""
        engine = LightingEngine(view_width=100, view_height=100)
        grid = np.zeros((100, 100), dtype=np.uint8)

        # Place solid tissue pillar at x=55 to 60, y=40 to 60
        grid[40:60, 55:60] = MAT_TISSUE

        # Point light at (45, 50) with radius 35, shining bright yellow/white
        light = LightSource(world_x=45.0, world_y=50.0, radius=35.0, color=(255, 240, 180), intensity=1.0, cast_shadows=True)

        dest_surface = pygame.Surface((100, 100))
        dest_surface.fill((200, 200, 200))  # Base world terrain

        engine.render(dest_surface, cam_x=0, cam_y=0, lights=[light], grid_grid=grid)

        # Pixel directly in front of light (e.g. x=35, y=50) should be brightly lit
        lit_pixel = dest_surface.get_at((35, 50))

        # Pixel behind the solid wall pillar (e.g. x=75, y=50) should be in the shadow
        shadowed_pixel = dest_surface.get_at((75, 50))

        # Lit pixel should be significantly brighter than shadowed pixel
        self.assertGreater(lit_pixel.r, shadowed_pixel.r + 30)
        self.assertGreater(lit_pixel.g, shadowed_pixel.g + 30)

    def test_lighting_resize(self):
        """Engine cleanly resizes internal lighting surfaces."""
        engine = LightingEngine(view_width=100, view_height=80)
        self.assertEqual(engine.light_surface.get_size(), (100, 80))
        engine.resize(160, 90)
        self.assertEqual(engine.light_surface.get_size(), (160, 90))


if __name__ == "__main__":
    unittest.main()
