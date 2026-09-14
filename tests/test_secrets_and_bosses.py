"""Unit tests for exploration secrets, 11 DNA Gene Orbs, Ancient Lore Tablets, and 3 Secret Bio-Bosses."""

import unittest
import pygame

from py_noita.entities.bosses import (
    GiantHelminth,
    PrimordialPhagocyte,
    SynapticParasite,
    draw_boss_health_bar,
)
from py_noita.entities.player import Player
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import MAT_AIR, MAT_TISSUE
from py_noita.ui.hover_info import get_hover_target
from py_noita.weapons.cannula import OrganCannula
from py_noita.weapons.gene import GENE_DICT
from py_noita.world.biome import (
    BIOME_BILE_LAGOON,
    BIOME_BONE_CATACOMBS,
    BIOME_SPINE_NERVES,
)
from py_noita.world.generator import generate_world_level
from py_noita.world.secrets import (
    ANCIENT_TABLETS_DATA,
    ORBS_DATA,
    DnaTablet,
    GeneOrb,
    spawn_secrets_for_biome,
)


class TestSecretsAndBosses(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.grid = SimulationGrid(width=200, height=260)
        self.player = Player(x=100.0, y=100.0)
        self.player.cannulas.append(
            OrganCannula(name="Test Cannula", capacity=4, cast_delay=0.1, recharge_time=0.5, biomass_max=100.0, biomass_recharge=50.0)
        )

    def test_eleven_gene_orbs_defined(self):
        """Verify exactly 11 distinct Gene Orbs are configured with valid genes."""
        self.assertEqual(len(ORBS_DATA), 11, "Must have exactly 11 hidden DNA Gene Orbs!")
        orb_ids = [o[0] for o in ORBS_DATA]
        self.assertEqual(orb_ids, list(range(11)))

        for oid, biome, gid, name, desc in ORBS_DATA:
            self.assertIn(gid, GENE_DICT, f"Reward gene {gid} for orb {oid} must exist in GENE_DICT!")
            self.assertTrue(len(name) > 0)
            self.assertTrue(len(desc) > 0)

    def test_gene_orb_collection_and_player_buff(self):
        """Verify collecting an orb increments count, buffs player max HP, and awards gene."""
        orb = GeneOrb(0, 100.0, 100.0, "PRIMORDIAL_BEAM", "Ur-Orb", "Test Orb")
        initial_max_hp = self.player.max_hp
        initial_orbs = self.player.orbs_collected

        reward = orb.update(self.player)
        self.assertIsNotNone(reward)
        self.assertEqual(reward.id, "PRIMORDIAL_BEAM")
        self.assertTrue(orb.collected)
        self.assertEqual(self.player.orbs_collected, initial_orbs + 1)
        self.assertEqual(self.player.max_hp, initial_max_hp + 25.0)

        # Cannot collect second time
        second_reward = orb.update(self.player)
        self.assertIsNone(second_reward)

    def test_ancient_dna_tablets(self):
        """Verify 8 ancient lore tablets with atmospheric texts exist."""
        self.assertEqual(len(ANCIENT_TABLETS_DATA), 8, "Must have 8 ancient lore tablets (1 per biome)!")
        for tid, title, text in ANCIENT_TABLETS_DATA:
            self.assertTrue(title.startswith(("I.", "II.", "III.", "IV.", "V.", "VI.", "VII.", "VIII.")))
            self.assertGreater(len(text), 20)

        tablet = DnaTablet(0, 50.0, 50.0, "I. Test Title", "Test Text")
        self.assertTrue(tablet.contains_point(50.0, 50.0))
        self.assertFalse(tablet.contains_point(150.0, 150.0))

    def test_hover_target_secrets(self):
        """Verify hover info detects GeneOrbs and DnaTablets."""
        orb = GeneOrb(1, 40.0, 40.0, "UR_CYTOKINE", "Ur-Gen-Orb II: Hämo-Kern", "Desc")
        tablet = DnaTablet(1, 80.0, 80.0, "II. Der Strom", "Lore Text")

        # Hover over orb
        hover_orb = get_hover_target(
            self.grid,
            enemies=[],
            world_x=40.0,
            world_y=40.0,
            gene_orbs=[orb],
            dna_tablets=[tablet],
        )
        self.assertIsNotNone(hover_orb)
        self.assertEqual(hover_orb.category, "Ur-Geheimnis")
        self.assertEqual(hover_orb.name, "Ur-Gen-Orb II: Hämo-Kern")

        # Hover over tablet
        hover_tab = get_hover_target(
            self.grid,
            enemies=[],
            world_x=80.0,
            world_y=80.0,
            gene_orbs=[orb],
            dna_tablets=[tablet],
        )
        self.assertIsNotNone(hover_tab)
        self.assertEqual(hover_tab.category, "Uralte Lore")
        self.assertEqual(hover_tab.name, "II. Der Strom")

    def test_giant_helminth_boss(self):
        """Verify Giant Helminth has 30 segments, digs terrain, and attacks."""
        boss = GiantHelminth(60.0, 60.0)
        self.assertEqual(len(boss.segments), 30, "Helminth must have 30 body segments!")
        self.assertEqual(boss.hp, 650.0)

        # Fill with tissue
        self.grid.fill_rect(40, 40, 80, 80, MAT_TISSUE)
        boss.target_angle = 0.0
        projs, minions = boss.update_boss(self.player, self.grid, dt=0.016)

        # Head carves tunnel
        hx, hy = int(boss.center_x), int(boss.center_y)
        self.assertEqual(self.grid.get_pixel(hx, hy), MAT_AIR)

    def test_primordial_phagocyte_boss(self):
        """Verify Primordial Phagocyte amoeba titan spawns bile projectiles and macrophage minions."""
        boss = PrimordialPhagocyte(80.0, 80.0)
        self.assertEqual(boss.hp, 520.0)
        boss.attack_timer = 0.0
        boss.bud_timer = 0.0

        projs, minions = boss.update_boss(self.player, self.grid, dt=0.016)
        self.assertGreater(len(projs), 0, "Phagocyte must emit bile projectile wave!")
        self.assertGreater(len(minions), 0, "Phagocyte must bud macrophage minion!")

    def test_synaptic_parasite_boss(self):
        """Verify Synaptic Parasite neuro-sentinel teleports and fires spiral sparks."""
        boss = SynapticParasite(80.0, 80.0)
        self.assertEqual(boss.hp, 420.0)
        initial_pos = (boss.x, boss.y)

        # Trigger teleport
        boss.teleport_timer = 0.0
        boss.attack_timer = 0.0
        projs, _ = boss.update_boss(self.player, self.grid, dt=0.016)

        self.assertNotEqual((boss.x, boss.y), initial_pos, "Parasite should teleport blink!")
        self.assertGreater(len(projs), 0, "Parasite must fire synapse spark burst!")

    def test_secret_bosses_spawn_in_biomes(self):
        """Verify world generator places the 3 secret bosses in their designated biomes."""
        # 1. Helminth in Bone Catacombs
        g1 = SimulationGrid(width=160, height=220)
        *_, boss1 = generate_world_level(g1, BIOME_BONE_CATACOMBS, seed=101)
        self.assertIsNotNone(boss1)
        self.assertIsInstance(boss1, GiantHelminth)

        # 2. Phagocyte in Bile Lagoon
        g2 = SimulationGrid(width=160, height=220)
        *_, boss2 = generate_world_level(g2, BIOME_BILE_LAGOON, seed=102)
        self.assertIsNotNone(boss2)
        self.assertIsInstance(boss2, PrimordialPhagocyte)

        # 3. Synaptic Parasite in Spine & Nerves
        g3 = SimulationGrid(width=160, height=220)
        *_, boss3 = generate_world_level(g3, BIOME_SPINE_NERVES, seed=103)
        self.assertIsNotNone(boss3)
        self.assertIsInstance(boss3, SynapticParasite)

    def test_boss_health_bar_render(self):
        """Verify boss health bar renders cleanly on surface."""
        boss = GiantHelminth(100.0, 100.0)
        surf = pygame.Surface((400, 300))
        font = pygame.font.SysFont("Arial", 12)
        draw_boss_health_bar(surf, boss, font, view_w=400, view_h=300)
        # Should not crash and should draw pixels on the surface
        color_sum = pygame.transform.average_color(surf)
        self.assertGreater(sum(color_sum), 0)


if __name__ == "__main__":
    unittest.main()
