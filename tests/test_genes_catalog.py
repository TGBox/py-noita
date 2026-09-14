"""Unit tests for the 120+ Gene Catalog, Triggers, Timers, Modifiers, and Formations."""

import math
import os
import unittest
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.font.init()

from py_noita.entities.enemy import Enemy
from py_noita.entities.player import Player
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import MAT_ACID, MAT_AIR, MAT_BLOOD
from py_noita.weapons.cannula import OrganCannula
from py_noita.weapons.deck_evaluator import CastState, evaluate_cannula_fire, evaluate_payload
from py_noita.weapons.gene import GENE_DICT, GENE_LIBRARY, Gene, GeneType
from py_noita.weapons.projectile import Projectile


class TestGenesCatalog(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.font.init()
        self.grid = SimulationGrid(width=200, height=200)
        self.player = Player(x=100.0, y=100.0)

    def test_total_gene_count_exceeds_120(self):
        """Verify the catalog contains at least 120 unique cards."""
        self.assertGreaterEqual(len(GENE_LIBRARY), 120, "Catalog must have at least 120 unique genes!")
        unique_ids = set(g.id for g in GENE_LIBRARY)
        self.assertEqual(len(unique_ids), len(GENE_LIBRARY), "Every gene ID must be strictly unique!")
        self.assertEqual(len(GENE_DICT), len(GENE_LIBRARY))

    def test_gene_category_distribution(self):
        """Verify that all 4 required sub-categories satisfy the milestone specifications."""
        projectiles = [g for g in GENE_LIBRARY if g.gene_type == GeneType.PROJECTILE]
        triggers = [g for g in GENE_LIBRARY if g.gene_type == GeneType.TRIGGER]
        modifiers = [g for g in GENE_LIBRARY if g.gene_type == GeneType.MODIFIER]
        multicasts = [g for g in GENE_LIBRARY if g.gene_type == GeneType.MULTICAST]

        # Specifications: 40+ projectiles, 25+ triggers/timers, 30+ modifiers, 15+ formations/multicasts
        self.assertGreaterEqual(len(projectiles), 40, f"Expected >= 40 projectiles, got {len(projectiles)}")
        self.assertGreaterEqual(len(triggers), 25, f"Expected >= 25 triggers/timers, got {len(triggers)}")
        self.assertGreaterEqual(len(modifiers), 30, f"Expected >= 30 modifiers, got {len(modifiers)}")
        self.assertGreaterEqual(len(multicasts), 15, f"Expected >= 15 formations/multicasts, got {len(multicasts)}")

    def test_key_projectiles_exist(self):
        """Verify explicit projectile requirements from the todo list exist and have valid stats."""
        required_projectiles = [
            "CARTILAGE_BUCKSHOT",
            "PLASMA_TENDRIL",
            "CYTOKINE_LASER",
            "SPORE_MINE",
            "BONE_BOOMERANG",
            "SLIME_ORB",
        ]
        for gid in required_projectiles:
            self.assertIn(gid, GENE_DICT, f"Missing required projectile {gid}!")
            gene = GENE_DICT[gid]
            self.assertEqual(gene.gene_type, GeneType.PROJECTILE)
            self.assertGreater(gene.damage, 0)
            self.assertGreater(gene.speed, 0)
            self.assertGreater(gene.lifetime, 0)

    def test_key_triggers_and_timers(self):
        """Verify impact, timer, proximity, and penetration trigger types."""
        # Impact triggers
        for trig_id in ["TRIGGER_HIT_ACID", "TRIGGER_HIT_BILE", "TRIGGER_HIT_NERVE"]:
            self.assertIn(trig_id, GENE_DICT)
            self.assertEqual(GENE_DICT[trig_id].trigger_type, "IMPACT")

        # Timer triggers
        for timer_id in ["TIMER_MICRO_BURST", "TIMER_SHORT_CYST", "TIMER_MED_BURST", "TIMER_LONG_FUSE"]:
            self.assertIn(timer_id, GENE_DICT)
            self.assertEqual(GENE_DICT[timer_id].trigger_type, "TIMER")
            self.assertGreater(GENE_DICT[timer_id].lifetime, 0)

        # Proximity triggers
        for prox_id in ["TRIGGER_PROX_SENSE", "TRIGGER_PROX_BLOOD", "TRIGGER_PROX_NERVE"]:
            self.assertIn(prox_id, GENE_DICT)
            self.assertEqual(GENE_DICT[prox_id].trigger_type, "PROXIMITY")
            self.assertGreater(GENE_DICT[prox_id].proximity_radius, 0)

        # Penetration triggers
        for pen_id in ["TRIGGER_PENETRATION_BONE", "TRIGGER_PENETRATION_FLESH", "TRIGGER_PENETRATION_DOUBLE"]:
            self.assertIn(pen_id, GENE_DICT)
            self.assertEqual(GENE_DICT[pen_id].trigger_type, "PENETRATION")
            self.assertTrue(GENE_DICT[pen_id].piercing)

    def test_key_modifiers(self):
        """Verify required modifier genes (Homing, DoT, Acid infusion, Critical, Recoil damping)."""
        required_mods = [
            "MOD_HOMING_STRONG",
            "MOD_NECROSIS_DOT",
            "MOD_ACID_INFUSION",
            "MOD_CRITICAL_CELL_DEATH",
            "MOD_RECOIL_DAMPING",
        ]
        for mid in required_mods:
            self.assertIn(mid, GENE_DICT)
            self.assertEqual(GENE_DICT[mid].gene_type, GeneType.MODIFIER)

    def test_key_formations(self):
        """Verify formations: Double Helix, Fan, Radial, Orbital."""
        required_formations = [
            "FORMATION_DOUBLE_HELIX",
            "FORMATION_FAN_3",
            "FORMATION_FAN_5",
            "FORMATION_RADIAL_8",
            "FORMATION_RADIAL_12",
            "FORMATION_ORBITAL_2",
            "FORMATION_ORBITAL_4",
        ]
        for fid in required_formations:
            self.assertIn(fid, GENE_DICT)
            self.assertEqual(GENE_DICT[fid].gene_type, GeneType.MULTICAST)
            self.assertNotEqual(GENE_DICT[fid].formation_type, "NONE")

    def test_double_helix_formation_execution(self):
        """Firing a cannula with Double Helix produces 2 intertwined wave projectiles."""
        cannula = OrganCannula(
            name="Helix Cannula", capacity=4, cast_delay=0.1, recharge_time=0.5,
            biomass_max=100.0, biomass_recharge=50.0,
        )
        cannula.add_gene(GENE_DICT["FORMATION_DOUBLE_HELIX"])
        cannula.add_gene(GENE_DICT["PLASMA_TENDRIL"])

        projs = evaluate_cannula_fire(cannula, 100.0, 100.0, 0.0, shooter=self.player)
        self.assertEqual(len(projs), 2)
        self.assertEqual(projs[0].pattern, "HELIX_A")
        self.assertEqual(projs[1].pattern, "HELIX_B")

    def test_radial_burst_formation_execution(self):
        """Firing a cannula with Radial Ausbruch 8 produces 8 projectiles."""
        cannula = OrganCannula(
            name="Radial Cannula", capacity=4, cast_delay=0.1, recharge_time=0.5,
            biomass_max=200.0, biomass_recharge=100.0,
        )
        cannula.add_gene(GENE_DICT["FORMATION_RADIAL_8"])
        cannula.add_gene(GENE_DICT["BONE_SPIKE"])

        projs = evaluate_cannula_fire(cannula, 100.0, 100.0, 0.0, shooter=self.player)
        self.assertEqual(len(projs), 8)
        angles = [math.atan2(p.vy, p.vx) for p in projs]
        # Verify 8 distinct directions are covered
        self.assertEqual(len(set(round(a, 2) for a in angles)), 8)

    def test_fan_formation_execution(self):
        """Firing a cannula with Fan 3 produces 3 projectiles in a spread fan."""
        cannula = OrganCannula(
            name="Fan Cannula", capacity=4, cast_delay=0.1, recharge_time=0.5,
            biomass_max=100.0, biomass_recharge=50.0,
        )
        cannula.add_gene(GENE_DICT["FORMATION_FAN_3"])
        cannula.add_gene(GENE_DICT["CYTOKINE_LASER"])

        projs = evaluate_cannula_fire(cannula, 100.0, 100.0, 0.0, shooter=self.player)
        self.assertEqual(len(projs), 3)

    def test_orbital_formation_execution(self):
        """Firing Orbital 2 produces 2 rotating shield projectiles."""
        cannula = OrganCannula(
            name="Orbital Cannula", capacity=4, cast_delay=0.1, recharge_time=0.5,
            biomass_max=100.0, biomass_recharge=50.0,
        )
        cannula.add_gene(GENE_DICT["FORMATION_ORBITAL_2"])
        cannula.add_gene(GENE_DICT["CHITIN_SHARD"])

        projs = evaluate_cannula_fire(cannula, 100.0, 100.0, 0.0, shooter=self.player)
        self.assertEqual(len(projs), 2)
        for p in projs:
            self.assertEqual(p.pattern, "ORBIT")
            self.assertIsNotNone(p.shooter)

    def test_proximity_trigger_detonation(self):
        """Verify proximity trigger explodes when target enters proximity radius."""
        dummy_enemy = Enemy(x=115.0, y=100.0, enemy_type="TEST", hp=50.0, width=12, height=12)
        proj = Projectile(
            x=100.0, y=100.0, vx=1.0, vy=0.0,
            proximity_radius=28.0,
            payload_genes=[GENE_DICT["ACID_GLOBULE"]],
        )


        children = proj.update(self.grid, targets=[dummy_enemy])
        self.assertFalse(proj.alive, "Projectile should detonate upon target proximity!")
        self.assertGreater(len(children), 0, "Payload must be spawned on proximity trigger!")


if __name__ == "__main__":
    unittest.main()
