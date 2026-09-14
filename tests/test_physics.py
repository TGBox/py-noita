"""Unit tests for Pymunk 2D rigid-body physics coupled with the pixel grid."""

import math
import unittest
import pygame
import pymunk

from py_noita.physics.physics_world import PhysicsWorld
from py_noita.physics.rigid_body import BioRigidBody
from py_noita.simulation.explosion import create_explosion
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import (
    MAT_AIR,
    MAT_BLOOD,
    MAT_TISSUE,
    MAT_WATER,
)
from py_noita.ui.hover_info import get_hover_target


class TestPhysicsEngine(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.grid = SimulationGrid(width=120, height=120)
        self.world = PhysicsWorld(self.grid)
        self.grid.physics_world = self.world

    def tearDown(self):
        pygame.quit()

    def test_rigid_body_creation_and_removal(self):
        """Test creating box, circle, and poly rigid bodies."""
        box = BioRigidBody(self.world.space, 40.0, 40.0, shape_type="box", width=12.0, height=12.0, name="Knochenkiste")
        circle = BioRigidBody(self.world.space, 60.0, 40.0, shape_type="circle", radius=6.0, name="Knorpelkugel")

        self.world.add_body(box)
        self.world.add_body(circle)
        self.assertEqual(len(self.world.bodies), 2)

        self.assertTrue(box.contains_point(40.0, 40.0))
        self.assertFalse(box.contains_point(10.0, 10.0))
        self.assertTrue(circle.contains_point(60.0, 40.0))

        self.world.remove_body(box)
        self.assertEqual(len(self.world.bodies), 1)

    def test_terrain_collision_coupling(self):
        """Rigid body falling onto solid terrain floor should collide and stop sinking."""
        # Create solid floor at y=80..90
        for x in range(20, 80):
            for y in range(80, 90):
                self.grid.set_pixel(x, y, MAT_TISSUE)

        body = BioRigidBody(self.world.space, 50.0, 70.0, shape_type="box", width=10.0, height=10.0, mass=5.0)
        self.world.add_body(body)

        # Step physics for 30 frames
        for _ in range(30):
            self.world.update(1.0 / 60.0, cam_x=0, cam_y=0, view_w=120, view_h=120)

        # Body should rest near y=74 (half-height 5 + floor 80 - margin), not fall through to y=100
        self.assertLess(body.y, 82.0)
        self.assertGreater(body.y, 65.0)

    def test_explosion_impulse_and_torque(self):
        """Pixel explosion applies impulse, torque, and damage to rigid bodies."""
        body = BioRigidBody(self.world.space, 50.0, 50.0, shape_type="box", width=12.0, height=12.0, mass=8.0, health=100.0)
        self.world.add_body(body)

        # Detonate explosion slightly below and to the left at (42, 58)
        create_explosion(self.grid, cx=42, cy=58, radius=16, power=45.0)

        # Body should have received positive vx (flung right) and negative vy (flung up)
        vx, vy = body.velocity
        self.assertGreater(vx, 5.0, "Explosion should push body to the right")
        self.assertLess(vy, -5.0, "Explosion should fling body upwards")
        self.assertNotEqual(body.body.angular_velocity, 0.0, "Explosion should impart rotational torque")
        self.assertLess(body.health, 100.0, "Explosion should damage rigid body")

    def test_loose_pixel_displacement(self):
        """Rigid body moving through liquid displaces fluid cells."""
        # Place water pool
        for x in range(45, 55):
            for y in range(45, 55):
                self.grid.set_pixel(x, y, MAT_WATER)

        initial_water_count = sum(1 for x in range(45, 55) for y in range(45, 55) if self.grid.grid[y, x] == MAT_WATER)
        self.assertEqual(initial_water_count, 100)

        body = BioRigidBody(self.world.space, 50.0, 50.0, shape_type="circle", radius=6.0, mass=10.0)
        body.body.velocity = (20.0, 0.0)
        self.world.add_body(body)

        self.world.update(1.0 / 60.0, cam_x=0, cam_y=0, view_w=120, view_h=120)

        # Some water pixels within the circle should have been displaced
        water_at_center = self.grid.grid[50, 50]
        self.assertEqual(water_at_center, MAT_AIR, "Fluid at rigid body center should be displaced to air")

    def test_crushing_soft_tissue(self):
        """Fast rigid body impact crushes soft tissue into blood."""
        self.grid.set_pixel(50, 50, MAT_TISSUE)

        body = BioRigidBody(self.world.space, 50.0, 50.0, shape_type="box", width=8.0, height=8.0, mass=20.0)
        body.body.velocity = (0.0, 25.0)  # High vertical speed
        self.world.add_body(body)

        self.world.update(1.0 / 60.0, cam_x=0, cam_y=0, view_w=120, view_h=120)

        self.assertEqual(self.grid.grid[50, 50], MAT_BLOOD, "Crushed tissue should convert to blood")

    def test_rigid_body_hover_inspection(self):
        """Hovering over rigid body returns object inspection tooltip."""
        body = BioRigidBody(self.world.space, 60.0, 60.0, shape_type="box", width=16.0, height=16.0, name="Chitin-Schild", health=80.0)
        self.world.add_body(body)

        target = get_hover_target(self.grid, [], 60.0, 60.0, rigid_bodies=self.world.bodies)
        self.assertIsNotNone(target)
        self.assertEqual(target.target_type, "OBJECT")
        self.assertEqual(target.name, "Chitin-Schild")
        self.assertEqual(target.current_hp, 80.0)


if __name__ == "__main__":
    unittest.main()
