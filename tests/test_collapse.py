"""Unit tests for cellular structural collapse, detached terrain chunks, stalactites, and collapsing bridges."""

import unittest
import pygame
import pymunk

from py_noita.entities.enemy import Macrophage
from py_noita.physics.collapse import (
    CollapsingTerrainChunk,
    build_cartilage_bridge,
    build_stalactite,
    check_and_collapse_terrain,
)
from py_noita.physics.physics_world import PhysicsWorld
from py_noita.simulation.explosion import create_explosion
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import (
    MAT_AIR,
    MAT_BONE,
    MAT_BONE_CHIP,
    MAT_TISSUE,
    MAT_WALL_BONE,
)


class TestStructuralCollapse(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.grid = SimulationGrid(width=120, height=120)
        self.world = PhysicsWorld(self.grid)
        self.grid.physics_world = self.world

    def tearDown(self):
        pygame.quit()

    def test_unanchored_terrain_collapses(self):
        """A freestanding floating block of tissue with no anchor detaches and becomes a rigid body."""
        # Create a 12x12 island of MAT_TISSUE in mid-air
        self.grid.fill_rect(50, 40, 12, 12, MAT_TISSUE)

        # Trigger structural collapse check around (56, 46)
        chunks = check_and_collapse_terrain(self.grid, self.world, (56, 46), search_radius=16)

        self.assertEqual(len(chunks), 1, "Floating terrain must detach as a rigid-body chunk!")
        chunk = chunks[0]
        self.assertIn(chunk, self.world.bodies)
        self.assertGreater(chunk.body.mass, 5.0)

        # Verify pixels on grid were cleared to MAT_AIR
        solid_count = sum(1 for x in range(50, 62) for y in range(40, 52) if self.grid.grid[y, x] == MAT_TISSUE)
        self.assertEqual(solid_count, 0, "Floating pixels must be removed from grid upon collapse!")

    def test_anchored_terrain_does_not_collapse(self):
        """Terrain solidly anchored to bedrock MAT_WALL_BONE remains fixed."""
        # Bedrock at top
        self.grid.fill_rect(40, 10, 30, 4, MAT_WALL_BONE)
        # Hanging tissue connected to bedrock
        self.grid.fill_rect(48, 14, 14, 14, MAT_TISSUE)

        chunks = check_and_collapse_terrain(self.grid, self.world, (55, 20), search_radius=16)
        self.assertEqual(len(chunks), 0, "Terrain connected to bedrock must NOT collapse!")

    def test_severed_stalactite_collapses_and_crushes(self):
        """Severing the base of a ceiling stalactite causes it to fall as an impaling chunk."""
        # Ceiling bedrock
        self.grid.fill_rect(30, 10, 50, 4, MAT_WALL_BONE)

        # Build pointed stalactite hanging from ceiling
        build_stalactite(self.grid, base_x=50, base_y=14, length=24, base_width=10, mat=MAT_BONE)

        # Sever the top base of the stalactite with an explosion at (50, 15)
        create_explosion(self.grid, cx=50, cy=15, radius=6, power=30.0, physics_world=self.world)

        # The lower section of the stalactite should have detached as a CollapsingTerrainChunk
        stalactite_chunks = [b for b in self.world.bodies if isinstance(b, CollapsingTerrainChunk) and b.is_stalactite]
        self.assertGreaterEqual(len(stalactite_chunks), 1, "Severed stalactite must become a falling chunk!")

        chunk = stalactite_chunks[0]

        # Enemy standing below
        enemy = Macrophage(50.0, 80.0)
        initial_hp = enemy.hp

        # Floor at 95
        self.grid.fill_rect(20, 95, 80, 10, MAT_WALL_BONE)

        # Simulate fall
        for _ in range(50):
            self.world.update(1.0 / 60.0, 0, 0, 120, 120, enemies=[enemy])
            if enemy.hp < initial_hp:
                break

        self.assertLess(enemy.hp, initial_hp, "Falling stalactite must inflict crushing/impaling damage!")

    def test_collapsing_cartilage_bridge(self):
        """Blowing up the middle of a bridge causes the unsupported span to collapse."""
        # Two anchor cliffs
        self.grid.fill_rect(10, 40, 20, 30, MAT_WALL_BONE)
        self.grid.fill_rect(80, 40, 20, 30, MAT_WALL_BONE)

        # Bridge spanning the chasm from x=30 to x=80
        build_cartilage_bridge(self.grid, x1=30, x2=80, y=45, thickness=4, mat=MAT_BONE)

        # Verify bridge exists
        bridge_pixels = sum(1 for x in range(35, 75) if self.grid.is_solid(x, 45) or self.grid.is_solid(x, 46))
        self.assertGreater(bridge_pixels, 20)

        # Blast out a section on the left anchor connection at (32, 45)
        create_explosion(self.grid, cx=32, cy=45, radius=8, power=40.0, physics_world=self.world)
        # Blast out the right anchor connection at (78, 45)
        create_explosion(self.grid, cx=78, cy=45, radius=8, power=40.0, physics_world=self.world)

        # The central severed bridge section should now be detached and collapsed into a chunk
        bridge_chunks = [b for b in self.world.bodies if isinstance(b, CollapsingTerrainChunk)]
        self.assertGreaterEqual(len(bridge_chunks), 1, "Severed bridge span must collapse into physics chunks!")


if __name__ == "__main__":
    unittest.main()
