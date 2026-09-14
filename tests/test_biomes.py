"""Unit tests for the 8 organ biomes, side paths, low-gravity, and new enemy types."""

import unittest
from py_noita.config import GRAVITY
from py_noita.entities.ai import update_enemy_ai
from py_noita.entities.enemy import (
    ChitinBeetle,
    SporePod,
    SynapticSentry,
    create_enemy,
)
from py_noita.entities.player import Player
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import MAT_AIR, MAT_BILE, MAT_PUS
from py_noita.world.biome import (
    ALL_BIOMES,
    BIOME_BILE_LAGOON,
    BIOME_BONE_CATACOMBS,
    BIOME_EPIDERMIS,
    BIOME_GASTRIC,
    BIOME_INFECTED_LUNG,
    BIOME_PRIMORDIAL_CORE,
    BIOME_SPINE_NERVES,
    BIOME_VASCULAR,
)
from py_noita.world.generator import generate_world_level
from py_noita.world.incubation_node import IncubationNode


class TestEightOrganBiomes(unittest.TestCase):
    def setUp(self):
        self.grid = SimulationGrid(width=200, height=260)
        self.player = Player(x=100.0, y=100.0)

    def test_all_eight_biomes_defined(self):
        """Verify all 8 biomes exist with valid attributes."""
        self.assertEqual(len(ALL_BIOMES), 8, "Must define exactly 8 organ biomes!")
        biome_ids = [b.biome_id for b in ALL_BIOMES]
        expected_ids = [
            "EPIDERMIS",
            "VASCULAR",
            "GASTRIC",
            "BILE_LAGOON",
            "INFECTED_LUNG",
            "BONE_CATACOMBS",
            "SPINE_NERVES",
            "PRIMORDIAL_CORE",
        ]
        self.assertEqual(biome_ids, expected_ids)

    def test_side_path_and_gravity_attributes(self):
        """Verify Bile Lagoon is marked as side path and Infected Lung has reduced gravity."""
        self.assertTrue(BIOME_BILE_LAGOON.is_side_path)
        self.assertFalse(BIOME_EPIDERMIS.is_side_path)
        self.assertAlmostEqual(BIOME_INFECTED_LUNG.gravity_multiplier, 0.68, places=2)
        self.assertEqual(BIOME_INFECTED_LUNG.generation_style, "LUNG")
        self.assertEqual(BIOME_BILE_LAGOON.generation_style, "LAGOON")
        self.assertEqual(BIOME_BONE_CATACOMBS.generation_style, "LABYRINTH")
        self.assertEqual(BIOME_SPINE_NERVES.generation_style, "SPINE")
        self.assertEqual(BIOME_PRIMORDIAL_CORE.generation_style, "CORE")

    def test_player_low_gravity_physics(self):
        """Verify player falls slower in low gravity biome (Infected Lung)."""
        player_normal = Player(x=50.0, y=50.0)
        player_low_g = Player(x=50.0, y=50.0)

        # Step physics in empty air
        player_normal.update_physics(self.grid, gravity_multiplier=1.0)
        player_low_g.update_physics(self.grid, gravity_multiplier=0.68)

        self.assertAlmostEqual(player_normal.vy, GRAVITY, places=3)
        self.assertAlmostEqual(player_low_g.vy, GRAVITY * 0.68, places=3)
        self.assertLess(player_low_g.vy, player_normal.vy)

    def test_new_enemy_types_instantiation(self):
        """Verify ChitinBeetle, SporePod, and SynapticSentry instantiate and operate."""
        beetle = create_enemy("CHITIN_BEETLE", 50.0, 50.0)
        self.assertIsInstance(beetle, ChitinBeetle)
        # Test chitin armor reduces incoming damage
        initial_hp = beetle.hp
        beetle.take_damage(20.0)
        expected_damage = 20.0 * 0.6
        self.assertAlmostEqual(beetle.hp, initial_hp - expected_damage, places=2)

        spore_pod = create_enemy("SPORE_POD", 50.0, 50.0)
        self.assertIsInstance(spore_pod, SporePod)

        sentry = create_enemy("SYNAPTIC_SENTRY", 50.0, 50.0)
        self.assertIsInstance(sentry, SynapticSentry)

    def test_new_enemy_ai_behavior(self):
        """Verify SporePod and SynapticSentry attack routines in AI."""
        # SporePod attacks
        spore_pod = SporePod(80.0, 80.0)
        spore_pod.attack_cooldown = 0.0
        projs, minions = update_enemy_ai(spore_pod, self.player, self.grid, dt=0.016)
        self.assertGreater(len(projs), 0, "SporePod should release seeking spore projectiles!")

        # SynapticSentry attacks
        sentry = SynapticSentry(80.0, 80.0)
        sentry.attack_cooldown = 0.0
        projs, minions = update_enemy_ai(sentry, self.player, self.grid, dt=0.016)
        self.assertGreater(len(projs), 0, "SynapticSentry should fire electric spark bolt!")
        self.assertEqual(projs[0].owner, "ENEMY")

    def test_incubation_node_side_portal(self):
        """Verify side portal functions in IncubationNode."""
        node = IncubationNode(
            start_x=10,
            start_y=10,
            width=140,
            height=100,
            has_side_path=True,
            side_biome_id="BILE_LAGOON",
            side_biome_name="Gallen-Lagune",
        )
        node.generate_structure(self.grid)

        # Place player away from portal
        self.player.x = 100.0
        self.player.y = 80.0
        self.assertFalse(node.is_player_in_side_portal(self.player))

        # Move player to side portal position
        spx, spy = node.side_portal_pos
        self.player.x = float(spx - self.player.width / 2)
        self.player.y = float(spy - self.player.height / 2)
        self.assertTrue(node.is_player_in_side_portal(self.player))

    def test_procedural_generation_all_eight_biomes(self):
        """Verify level generator runs cleanly without errors for all 8 biomes."""
        for b in ALL_BIOMES:
            g = SimulationGrid(width=160, height=200)
            spawn_pos, portal, enemies, loot, *secrets = generate_world_level(g, b, seed=42)
            self.assertIsNotNone(spawn_pos)
            self.assertIsNotNone(portal)
            self.assertGreater(len(enemies), 0)


if __name__ == "__main__":
    unittest.main()
