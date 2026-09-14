"""Unit tests for organic destructible props: AcidGallbladder, BiogasCyst, CartilageRaft, BoneMinecart, ChitinShield."""

import math
import unittest
import pygame
import pymunk

from py_noita.entities.enemy import Macrophage
from py_noita.physics.physics_world import PhysicsWorld
from py_noita.physics.props import (
    AcidGallbladder,
    BiogasCyst,
    BoneMinecart,
    CartilageRaft,
    ChitinShield,
)
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import (
    MAT_ACID,
    MAT_AIR,
    MAT_BIOGAS,
    MAT_FIRE,
    MAT_WATER,
)
from py_noita.world.biome import BIOME_EPIDERMIS
from py_noita.world.generator import spawn_biome_props


class TestOrganicProps(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.grid = SimulationGrid(width=120, height=120)
        self.world = PhysicsWorld(self.grid)
        self.grid.physics_world = self.world

    def tearDown(self):
        pygame.quit()

    def test_acid_gallbladder_bursts_acid(self):
        """AcidGallbladder upon destruction sprays acid into the grid."""
        gall = AcidGallbladder(self.world.space, 50.0, 50.0)
        self.world.add_body(gall)

        # Destroy it
        gall.take_damage(999.0)
        self.assertFalse(gall.alive)

        # Update world to process destruction
        self.world.update(1.0 / 60.0, 0, 0, 120, 120)

        # Verify acid was sprayed
        acid_count = sum(1 for x in range(45, 56) for y in range(45, 56) if self.grid.grid[y, x] == MAT_ACID)
        self.assertGreater(acid_count, 10, "Broken gallbladder should spray acid!")

    def test_biogas_cyst_explodes_on_fire(self):
        """BiogasCyst touching fire detonates in a major explosion."""
        cyst = BiogasCyst(self.world.space, 60.0, 60.0)
        self.world.add_body(cyst)

        # Place fire pixel inside cyst boundary
        self.grid.set_pixel(60, 60, MAT_FIRE)

        # Update physics
        self.world.update(1.0 / 60.0, 0, 0, 120, 120)

        # Cyst should be destroyed from fire
        self.assertFalse(cyst.alive)

    def test_cartilage_raft_buoyancy(self):
        """CartilageRaft floats on liquid with buoyancy force."""
        raft = CartilageRaft(self.world.space, 50.0, 50.0, width=24.0)
        self.world.add_body(raft)

        # Fill liquid pool below
        for x in range(35, 65):
            for y in range(48, 65):
                self.grid.set_pixel(x, y, MAT_WATER)

        # Step physics
        self.world.update(1.0 / 60.0, 0, 0, 120, 120)

        # Raft should have experienced buoyancy and not sink directly through
        self.assertLess(raft.y, 55.0)

    def test_bone_minecart_crushes_enemy(self):
        """Fast moving minecart inflicts kinetic crush damage on enemies."""
        cart = BoneMinecart(self.world.space, 40.0, 50.0)
        cart.body.velocity = (15.0, 0.0)  # High speed
        self.world.add_body(cart)

        enemy = Macrophage(44.0, 48.0)
        initial_hp = enemy.hp

        self.world.update(1.0 / 60.0, 0, 0, 120, 120, enemies=[enemy])

        self.assertLess(enemy.hp, initial_hp, "Moving cart should crush enemy on impact!")

    def test_chitin_shield_blocks_and_durable(self):
        """Chitin shield has high durability and blocks points."""
        shield = ChitinShield(self.world.space, 50.0, 50.0)
        self.world.add_body(shield)

        self.assertTrue(shield.contains_point(50.0, 50.0))
        self.assertEqual(shield.health, 220.0)
        shield.take_damage(40.0)
        self.assertEqual(shield.health, 180.0)
        self.assertTrue(shield.alive)

    def test_spawn_biome_props(self):
        """Verify spawn_biome_props adds various props into physics world."""
        # Carve cavern and liquid pool
        self.grid.fill_rect(20, 20, 80, 80, MAT_AIR)
        self.grid.fill_rect(20, 95, 80, 10, 1)  # Solid floor
        self.grid.fill_rect(40, 90, 20, 5, MAT_WATER)  # Liquid pool

        initial_count = len(self.world.bodies)
        spawn_biome_props(self.world, self.grid, BIOME_EPIDERMIS, count=6)
        self.assertGreater(len(self.world.bodies), initial_count, "Props should be spawned into physics world")


if __name__ == "__main__":
    unittest.main()
