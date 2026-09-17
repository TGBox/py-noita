"""Unit tests for explosion crater carving and orphan solid pixel cleanup."""

import unittest
import numpy as np

from py_noita.simulation.explosion import create_explosion
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import (
    MAT_AIR,
    MAT_ASH,
    MAT_BONE,
    MAT_BONE_CHIP,
    MAT_TISSUE,
    MAT_WALL_BONE,
    PROP_STATE,
    STATE_SOLID,
)


class TestExplosionCleanup(unittest.TestCase):
    def setUp(self):
        self.grid = SimulationGrid(width=80, height=80)
        self.grid.grid.fill(MAT_AIR)

    def test_orphan_floating_solid_cleanup(self):
        """Isolated single solid pixels left in the crater edge are converted to falling powder."""
        cx, cy = 40, 40
        # Fill a block of tissue
        self.grid.fill_rect(30, 30, 20, 20, MAT_TISSUE)

        # Trigger explosion
        create_explosion(self.grid, cx, cy, radius=8, spawn_fire=False)

        # Verify no solitary floating solid pixels (0 or 1 solid neighbor) remain in the blast area
        clean_r = 11
        for y in range(cy - clean_r, cy + clean_r + 1):
            for x in range(cx - clean_r, cx + clean_r + 1):
                mat = self.grid.grid[y, x]
                if mat != MAT_AIR and mat != MAT_WALL_BONE and PROP_STATE[mat] == STATE_SOLID:
                    # Count solid neighbors
                    solid_neighbors = 0
                    for ny in (y - 1, y, y + 1):
                        for nx in (x - 1, x, x + 1):
                            if nx == x and ny == y:
                                continue
                            n_mat = self.grid.grid[ny, nx]
                            if n_mat != MAT_AIR and PROP_STATE[n_mat] == STATE_SOLID:
                                solid_neighbors += 1
                    self.assertGreater(
                        solid_neighbors,
                        1,
                        f"Found orphaned floating solid pixel ({x}, {y}) of type {mat} with only {solid_neighbors} neighbors",
                    )

    def test_bone_orphan_converts_to_bone_chip(self):
        """An isolated bone pixel in the explosion cleanup zone converts to falling powder MAT_BONE_CHIP."""
        cx, cy = 40, 40
        # Place a single isolated bone pixel near the crater edge (r = 7, explosion radius = 5)
        self.grid.set_pixel(40, 47, MAT_BONE)

        create_explosion(self.grid, cx, cy, radius=5, spawn_fire=False)

        mat_after = self.grid.get_pixel(40, 47)
        # It must either be excavated to air or cleaned up into MAT_BONE_CHIP
        self.assertIn(mat_after, (MAT_AIR, MAT_BONE_CHIP))


if __name__ == "__main__":
    unittest.main()
