"""Unit tests for joint physics, cartilage tendons, nerve lanterns, and ceiling tentacles."""

import math
import unittest
import pygame
import pymunk

from py_noita.entities.enemy import Macrophage
from py_noita.physics.joints import (
    CartilageTendon,
    CeilingTentacle,
    NerveLantern,
    SwingingMeatChunk,
)
from py_noita.physics.physics_world import PhysicsWorld
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import (
    MAT_AIR,
    MAT_BLOOD,
    MAT_BONE,
    MAT_FIRE,
    MAT_TISSUE,
)
from py_noita.weapons.projectile import Projectile


class TestJointPhysics(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.grid = SimulationGrid(width=120, height=120)
        self.world = PhysicsWorld(self.grid)
        self.grid.physics_world = self.world

    def tearDown(self):
        pygame.quit()

    def test_cartilage_tendon_holds_and_severs(self):
        """Tendon holds suspended body, and severs when damaged or cut."""
        lantern = NerveLantern(self.world.space, 50.0, 40.0)
        self.world.add_body(lantern)
        tendon = CartilageTendon(self.world.space, 50.0, 20.0, lantern)
        self.world.add_tendon(tendon)

        self.assertFalse(tendon.severed)
        self.assertIn(tendon.joint, self.world.space.constraints)

        # Simulate a few steps: body remains suspended around anchor length
        for _ in range(20):
            self.world.update(1.0 / 60.0, 0, 0, 120, 120)

        self.assertAlmostEqual(lantern.x, 50.0, delta=4.0)
        self.assertAlmostEqual(lantern.y, 40.0, delta=4.0)

        # Shoot or damage tendon
        tendon.take_damage(999.0)
        self.assertTrue(tendon.severed)
        self.assertNotIn(tendon.joint, self.world.space.constraints)

        # Now lantern falls freely under gravity
        prev_y = lantern.y
        for _ in range(15):
            self.world.update(1.0 / 60.0, 0, 0, 120, 120)

        self.assertGreater(lantern.y, prev_y + 10.0, "Detached lantern must fall downward!")

    def test_tendon_hit_detection(self):
        """Tendon check_hit identifies when a projectile or point intersects the strand."""
        lantern = NerveLantern(self.world.space, 60.0, 50.0)
        tendon = CartilageTendon(self.world.space, 60.0, 20.0, lantern)

        # Point along line segment (60, 35) should hit
        self.assertTrue(tendon.check_hit(60.0, 35.0, radius=3.0))
        # Point far away (80, 35) should miss
        self.assertFalse(tendon.check_hit(80.0, 35.0, radius=3.0))

    def test_nerve_lantern_emits_light(self):
        """NerveLantern registers as an active bioluminescent light source."""
        lantern = NerveLantern(self.world.space, 45.0, 30.0, anchor_y=15.0)
        self.world.add_body(lantern)
        if lantern.tendon:
            self.world.add_tendon(lantern.tendon)

        lights = self.world.get_lights()
        self.assertGreaterEqual(len(lights), 1)
        self.assertEqual(lights[0].world_x, 45.0)
        self.assertGreater(lights[0].radius, 40.0)

    def test_nerve_lantern_falls_and_ignites_floor(self):
        """When a NerveLantern is severed and crashes to the solid floor, it detonates fire."""
        # Solid floor at y=80
        self.grid.fill_rect(20, 80, 80, 10, MAT_BONE)

        lantern = NerveLantern(self.world.space, 50.0, 30.0, anchor_y=15.0)
        self.world.add_body(lantern)
        if lantern.tendon:
            self.world.add_tendon(lantern.tendon)

        # Sever tendon to let it drop
        if lantern.tendon:
            lantern.tendon.sever()

        # Step simulation until it hits ground and detonates
        for _ in range(50):
            self.world.update(1.0 / 60.0, 0, 0, 120, 120)
            if lantern.ignited_ground:
                break

        self.assertTrue(lantern.ignited_ground, "Crashing lantern should ignite ground!")
        # Check for fire pixels spawned on the grid
        fire_count = sum(1 for x in range(35, 65) for y in range(65, 85) if self.grid.grid[y, x] == MAT_FIRE)
        self.assertGreater(fire_count, 0, "Floor should catch fire from crashed lantern!")

    def test_swinging_meat_chunk_crushes_enemy(self):
        """SwingingMeatChunk dropped from height deals crushing damage to enemies below."""
        # Solid floor at y=95
        self.grid.fill_rect(20, 95, 80, 10, MAT_BONE)

        chunk = SwingingMeatChunk(self.world.space, 50.0, 25.0, anchor_y=10.0)
        self.world.add_body(chunk)
        if chunk.tendon:
            self.world.add_tendon(chunk.tendon)

        # Enemy standing below
        enemy = Macrophage(50.0, 80.0)
        initial_hp = enemy.hp

        # Sever tendon so heavy chunk crashes down
        if chunk.tendon:
            chunk.tendon.sever()

        for _ in range(40):
            self.world.update(1.0 / 60.0, 0, 0, 120, 120, enemies=[enemy])

        self.assertLess(enemy.hp, initial_hp, "Crashing meat chunk should crush enemy below!")

    def test_ceiling_tentacle_undulation_and_severing(self):
        """CeilingTentacle writhes and can have segments severed."""
        tentacle = CeilingTentacle(self.world, anchor_x=50.0, anchor_y=20.0, num_segments=5)
        self.world.add_tentacle(tentacle)

        self.assertEqual(len(tentacle.segments), 5)
        self.assertEqual(len(tentacle.joints), 5)

        # Step simulation to simulate undulating movement
        initial_tip_x = tentacle.segments[-1].x
        for _ in range(30):
            self.world.update(1.0 / 60.0, 0, 0, 120, 120)

        self.assertTrue(tentacle.alive)

        # Sever segment 2
        seg2 = tentacle.segments[2]
        seg2.take_damage(999.0)

        # Update world
        self.world.update(1.0 / 60.0, 0, 0, 120, 120)

        # The joint for segment 2 should be removed
        self.assertNotIn(tentacle.joints[2], self.world.space.constraints)


if __name__ == "__main__":
    unittest.main()
