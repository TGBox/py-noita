"""Unit tests for Liquid Shaders, Menisci, Surface Tension, and Specular Reflections."""

import unittest
import numpy as np
import pygame

from py_noita.config import COLOR_BG_DARK
from py_noita.rendering.renderer import Renderer, render_slice_to_surfarray
from py_noita.simulation.materials import (
    LUT_COLORS,
    MAT_ACID,
    MAT_AIR,
    MAT_BONE,
    MAT_BLOOD,
    MAT_MUTAGEN,
    MAT_TISSUE,
    PROP_STATE,
)


class TestLiquidShaders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_specular_wave_highlights_on_liquid_surface(self):
        """Liquid exposed to air at the surface exhibits specular wave gleam."""
        grid_w, grid_h = 60, 40
        grid = np.zeros((grid_h, grid_w), dtype=np.uint8)
        color_var = np.zeros((grid_h, grid_w), dtype=np.uint8)

        # Fill bottom half with blood
        grid[20:40, :] = MAT_BLOOD

        out1 = np.zeros((grid_w, grid_h, 3), dtype=np.uint8)
        out2 = np.zeros((grid_w, grid_h, 3), dtype=np.uint8)

        # Render at time 0.0 and time 1.0
        render_slice_to_surfarray(
            grid, color_var, 0, 0, out1, LUT_COLORS, PROP_STATE,
            COLOR_BG_DARK[0], COLOR_BG_DARK[1], COLOR_BG_DARK[2], time_val=0.0
        )
        render_slice_to_surfarray(
            grid, color_var, 0, 0, out2, LUT_COLORS, PROP_STATE,
            COLOR_BG_DARK[0], COLOR_BG_DARK[1], COLOR_BG_DARK[2], time_val=1.0
        )

        # Surface row (y = 20) should have specular highlight exceeding base blood red
        surface_pixels_t0 = [out1[x, 20, 0] for x in range(grid_w)]
        base_blood_r = LUT_COLORS[MAT_BLOOD, 0]

        # There should be peak highlights brighter than base color
        max_spec = max(surface_pixels_t0)
        self.assertGreater(max_spec, base_blood_r)

        # High-frequency wave shifts over time, so pixel outputs at t0 vs t1 differ
        self.assertFalse(np.array_equal(out1[:, 20, :], out2[:, 20, :]))

        # Submerged deep liquid (y = 35) should NOT have specular surface wave flares
        deep_pixels_t0 = out1[:, 35, 0]
        deep_pixels_t1 = out2[:, 35, 0]
        self.assertTrue(np.array_equal(deep_pixels_t0, deep_pixels_t1))

    def test_viscous_meniscus_at_container_walls(self):
        """Air cell directly above liquid and adjacent to solid wall gets capillary meniscus climb."""
        grid_w, grid_h = 20, 20
        grid = np.zeros((grid_h, grid_w), dtype=np.uint8)
        color_var = np.zeros((grid_h, grid_w), dtype=np.uint8)

        # Solid bone container wall at x = 0
        grid[:, 0] = MAT_BONE
        # Liquid acid pool from y = 10 to 20, x = 1 to 10
        grid[10:20, 1:10] = MAT_ACID

        out = np.zeros((grid_w, grid_h, 3), dtype=np.uint8)
        render_slice_to_surfarray(
            grid, color_var, 0, 0, out, LUT_COLORS, PROP_STATE,
            COLOR_BG_DARK[0], COLOR_BG_DARK[1], COLOR_BG_DARK[2], time_val=0.0
        )

        # Pixel at (x=1, y=9) is AIR, but touches WALL (x=0) and LIQUID BELOW (y=10)
        meniscus_pixel = out[1, 9]

        # Pure cavern background air pixel away from walls and liquids (e.g. x=15, y=5)
        air_pixel = out[15, 5]

        # Meniscus pixel should be blended with acid green (higher green channel than pure background)
        self.assertGreater(meniscus_pixel[1], air_pixel[1] + 20)

    def test_horizontal_cohesion_bridging(self):
        """Single-pixel air gap between two horizontal liquid cells gets bridged by surface tension."""
        grid_w, grid_h = 20, 20
        grid = np.zeros((grid_h, grid_w), dtype=np.uint8)
        color_var = np.zeros((grid_h, grid_w), dtype=np.uint8)

        # Liquid mutagen on left (x=4) and right (x=6), with air gap at x=5
        grid[10, 4] = MAT_MUTAGEN
        grid[10, 5] = MAT_AIR
        grid[10, 6] = MAT_MUTAGEN

        out = np.zeros((grid_w, grid_h, 3), dtype=np.uint8)
        render_slice_to_surfarray(
            grid, color_var, 0, 0, out, LUT_COLORS, PROP_STATE,
            COLOR_BG_DARK[0], COLOR_BG_DARK[1], COLOR_BG_DARK[2], time_val=0.0
        )

        bridged_pixel = out[5, 10]
        pure_air_pixel = out[5, 2]

        # Bridged pixel should have mutagen violet tint (high red and blue channels)
        self.assertGreater(bridged_pixel[0], pure_air_pixel[0] + 30)
        self.assertGreater(bridged_pixel[2], pure_air_pixel[2] + 30)

    def test_renderer_anim_time_and_grid_blit(self):
        """Renderer increments anim_time and blits smoothly."""
        renderer = Renderer(screen_res=(320, 180))
        self.assertEqual(renderer.anim_time, 0.0)

        grid = np.zeros((200, 400), dtype=np.uint8)
        grid[50:80, 50:150] = MAT_ACID
        color_var = np.zeros((200, 400), dtype=np.uint8)

        renderer.render_grid(grid, color_var, cam_x=40, cam_y=40, dt=0.05)
        self.assertAlmostEqual(renderer.anim_time, 0.05)

        # Internal surface should be populated
        color = renderer.sim_surface.get_at((20, 20))
        # (cam_x=40 + 20 = 60, cam_y=40 + 20 = 60), which is in the acid pool!
        self.assertGreater(color.g, color.r)


if __name__ == "__main__":
    unittest.main()
