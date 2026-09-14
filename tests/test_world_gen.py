"""Unit tests for procedural cavern world generator and incubation node."""

import unittest
import numpy as np

from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import MAT_AIR, MAT_WALL_BONE
from py_noita.world.biome import BIOME_EPIDERMIS, BIOME_GASTRIC
from py_noita.world.generator import generate_world_level
from py_noita.world.incubation_node import IncubationNode


class TestWorldGeneration(unittest.TestCase):
    def setUp(self):
        self.grid = SimulationGrid(width=300, height=400)

    def test_cavern_generation(self):
        """Verify cavern generation carves air, places portal and spawns."""
        spawn_pos, portal, enemies, loot = generate_world_level(self.grid, BIOME_EPIDERMIS)

        # 1. Player spawn position must be air
        sx, sy = int(spawn_pos[0]), int(spawn_pos[1])
        self.assertEqual(self.grid.get_pixel(sx, sy), MAT_AIR, "Player spawn must be in air!")

        # 2. Portal must be created near the bottom
        self.assertGreater(portal.y, 200, "Portal must be in lower half of level!")

        # 3. Enemies and loot cysts must be generated
        self.assertGreater(len(enemies), 0, "No enemy spawn points generated!")
        self.assertGreater(len(loot), 0, "No loot cysts generated!")

        # 4. Air volume must be significant (tunnels carved)
        air_count = np.sum(self.grid.grid == MAT_AIR)
        self.assertGreater(air_count, 10000, "Not enough cavern tunnels carved!")

    def test_incubation_node_structure(self):
        """Verify incubation node structure creates safe room and healing pool."""
        node = IncubationNode(start_x=10, start_y=10, width=120, height=80)
        node.generate_structure(self.grid)

        # Floor must be wall bone
        self.assertEqual(self.grid.get_pixel(60, 85), MAT_WALL_BONE)

        # Perks and shop items must be populated
        self.assertEqual(len(node.pedestals), 3, "Must have exactly 3 mutation perks")
        self.assertGreater(len(node.shop_items), 0, "Shop must contain items")


if __name__ == "__main__":
    unittest.main()
