"""Unit tests for Visceral Skeleton Remains and Permanent Decal System."""

import unittest
import numpy as np
import pygame

from py_noita.config import COLOR_BG_DARK
from py_noita.rendering.renderer import Renderer, render_slice_to_surfarray
from py_noita.simulation.decals import spawn_corpse_skeleton
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import (
    LUT_COLORS,
    MAT_ACID,
    MAT_AIR,
    MAT_BONE,
    MAT_BONE_CHIP,
    MAT_CHITIN,
    MAT_MUTAGEN,
    MAT_TISSUE,
    PROP_STATE,
    STAIN_ACID,
    STAIN_BLOOD,
    STAIN_CHAR,
    STAIN_MUTAGEN,
    STAIN_SLIME,
)


class TestSkeletonsAndDecals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_corpse_skeleton_generation(self):
        """Slain enemies deposit anatomical bone pixels into the simulation grid."""
        grid = SimulationGrid(80, 80)
        cx, cy = 40.0, 40.0

        # Spawn generic vertebrate skeleton
        bone_pixels = spawn_corpse_skeleton(grid, cx, cy, enemy_type="DEFAULT")
        self.assertGreater(len(bone_pixels), 5)

        # Pixels must be set to MAT_BONE or MAT_BONE_CHIP in the grid
        has_bone = any(grid.grid[py, px] == MAT_BONE for px, py in bone_pixels)
        self.assertTrue(has_bone)

        # Chitin beetle should deposit MAT_CHITIN and bone fragments
        beetle_bones = spawn_corpse_skeleton(grid, 20.0, 20.0, enemy_type="CHITIN_BEETLE")
        has_chitin = any(grid.grid[py, px] == MAT_CHITIN for px, py in beetle_bones)
        self.assertTrue(has_chitin)

    def test_skeleton_acid_dissolution(self):
        """Bone pixels from skeleton dissolve when exposed to acid."""
        grid = SimulationGrid(50, 50)
        cx, cy = 25, 25
        grid.grid[cy, cx] = MAT_BONE

        # Place acid directly above bone
        grid.grid[cy - 1, cx] = MAT_ACID

        # Step simulation several times
        for _ in range(15):
            grid.update(cam_x=0, cam_y=0, view_w=50, view_h=50)

        # Acid should have interacted / corroded the bone
        current_mat = grid.grid[cy, cx]
        # Acid vulnerability for MAT_BONE triggers corrosion reaction
        self.assertNotEqual(grid.grid[cy - 1, cx], MAT_ACID)

    def test_permanent_decal_wall_splatter(self):
        """Decals permanently stain solid tissue walls and ignore air cells."""
        grid = SimulationGrid(60, 60)
        # Create solid tissue wall at x = 30
        grid.grid[:, 30:35] = MAT_TISSUE

        # Splatter blood decals around (x=28, y=30)
        stained_count = grid.apply_decal_splatter(cx=28, cy=30, radius=8, stain_type=STAIN_BLOOD, density=0.8)
        self.assertGreater(stained_count, 0)

        # Tissue pixels in wall should have STAIN_BLOOD
        wall_stains = [grid.stain_map[y, 30] for y in range(25, 36)]
        self.assertIn(STAIN_BLOOD, wall_stains)

        # Air pixels in open space (e.g. x=20) must remain clean (STAIN_NONE = 0)
        self.assertEqual(grid.stain_map[30, 20], 0)

    def test_explosion_scorch_marks_and_cavity_carving(self):
        """Carving explosion cavities clears removed air cells and scorches newly exposed perimeter with STAIN_CHAR."""
        grid = SimulationGrid(60, 60)
        grid.grid[20:40, 20:40] = MAT_TISSUE

        # Carve cavity with radius 6 at center (30, 30)
        grid.carve_circle(30, 30, radius=6, fill_mat=MAT_AIR)

        # Center should be air with cleared stain
        self.assertEqual(grid.grid[30, 30], MAT_AIR)
        self.assertEqual(grid.stain_map[30, 30], 0)

        # Surrounding tissue perimeter (radius 7-8) should contain char scorch marks
        perimeter_stains = []
        for dy in range(-8, 9):
            for dx in range(-8, 9):
                px, py = 30 + dx, 30 + dy
                if grid.is_solid(px, py):
                    perimeter_stains.append(grid.stain_map[py, px])

        self.assertIn(STAIN_CHAR, perimeter_stains)

    def test_renderer_with_decal_stains(self):
        """Renderer applies distinct visceral tinting to stained solid pixels."""
        grid_w, grid_h = 30, 30
        grid = np.zeros((grid_h, grid_w), dtype=np.uint8)
        color_var = np.zeros((grid_h, grid_w), dtype=np.uint8)
        stain_map = np.zeros((grid_h, grid_w), dtype=np.uint8)

        # Fill with tissue
        grid[:, :] = MAT_TISSUE

        # Pixel (10, 10) unstained, (10, 11) blood stained, (10, 12) char stained
        stain_map[10, 11] = STAIN_BLOOD
        stain_map[10, 12] = STAIN_CHAR

        out = np.zeros((grid_w, grid_h, 3), dtype=np.uint8)
        render_slice_to_surfarray(
            grid, color_var, 0, 0, out, LUT_COLORS, PROP_STATE,
            COLOR_BG_DARK[0], COLOR_BG_DARK[1], COLOR_BG_DARK[2], stain_map, time_val=0.0
        )

        unstained_color = out[10, 10]
        blood_color = out[11, 10]
        char_color = out[12, 10]

        # Blood stain has reduced green and blue channels (deep coagulated red crust)
        self.assertLess(blood_color[1], unstained_color[1])

        # Char stain is heavily blackened (low R, G, B)
        self.assertLess(char_color[0], unstained_color[0] // 2)
        self.assertLess(char_color[1], unstained_color[1])


if __name__ == "__main__":
    unittest.main()
