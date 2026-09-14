"""Tests for Material Transmutation Genes, Midas Enzyme, and Biomass-Gold collection."""

import unittest
import numpy as np

from py_noita.entities.player import Player
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import (
    MAT_ACID,
    MAT_AIR,
    MAT_BLOOD,
    MAT_BONE,
    MAT_GOLD,
    MAT_MUTAGEN,
    MAT_NERVE,
    MAT_TISSUE,
    MAT_WALL_BONE,
)
from py_noita.weapons.cannula import OrganCannula
from py_noita.weapons.deck_evaluator import evaluate_cannula_fire
from py_noita.weapons.gene import GENE_DICT, GeneType


class TestMaterialTransmutations(unittest.TestCase):
    def setUp(self):
        self.grid = SimulationGrid(width=120, height=120)

    def test_transmute_flesh_to_acid(self):
        """Sekret: Fleisch zu Magensäure converts flesh/tissue to MAT_ACID."""
        # Fill a 20x20 area with tissue
        for y in range(40, 60):
            for x in range(40, 60):
                self.grid.set_pixel(x, y, MAT_TISSUE)

        # Confirm tissue is set
        self.assertEqual(self.grid.get_pixel(50, 50), MAT_TISSUE)

        # Transmute circle around (50, 50)
        source_mats = [MAT_TISSUE, MAT_NERVE]
        count = self.grid.transmute_circle(50, 50, radius=8, source_mats=source_mats, target_mat=MAT_ACID)
        self.assertGreater(count, 0)
        self.assertEqual(self.grid.get_pixel(50, 50), MAT_ACID)
        # Boundary outside radius should still be tissue
        self.assertEqual(self.grid.get_pixel(40, 40), MAT_TISSUE)

    def test_transmute_blood_to_mutagen(self):
        """Sekret: Blut zu Mutagen converts blood pools into MAT_MUTAGEN."""
        for y in range(30, 40):
            for x in range(30, 40):
                self.grid.set_pixel(x, y, MAT_BLOOD)

        self.assertEqual(self.grid.get_pixel(35, 35), MAT_BLOOD)
        count = self.grid.transmute_circle(35, 35, radius=5, source_mats=[MAT_BLOOD], target_mat=MAT_MUTAGEN)
        self.assertGreater(count, 0)
        self.assertEqual(self.grid.get_pixel(35, 35), MAT_MUTAGEN)

    def test_sea_of_blood_and_sea_of_acid(self):
        """Sea of Blood and Sea of Acid flood empty air space with liquids."""
        # Empty space at (60, 60)
        self.assertEqual(self.grid.get_pixel(60, 60), MAT_AIR)
        # Sea of Blood converts air
        blood_count = self.grid.transmute_circle(60, 60, radius=10, source_mats=[MAT_AIR], target_mat=MAT_BLOOD)
        self.assertGreater(blood_count, 100)
        self.assertEqual(self.grid.get_pixel(60, 60), MAT_BLOOD)

        # Sea of Acid converts air at (90, 90)
        acid_count = self.grid.transmute_circle(90, 90, radius=10, source_mats=[MAT_AIR], target_mat=MAT_ACID)
        self.assertGreater(acid_count, 100)
        self.assertEqual(self.grid.get_pixel(90, 90), MAT_ACID)

    def test_midas_enzyme_and_unbreakable_walls(self):
        """Midas Enzyme turns organic matter to MAT_GOLD, leaving unbreakable walls intact."""
        self.grid.set_pixel(50, 50, MAT_TISSUE)
        self.grid.set_pixel(51, 50, MAT_BONE)
        self.grid.set_pixel(52, 50, MAT_BLOOD)
        self.grid.set_pixel(53, 50, MAT_WALL_BONE)  # Unbreakable wall

        # None source_mats means all non-air and non-wall materials
        modified = self.grid.transmute_circle(51, 50, radius=6, source_mats=None, target_mat=MAT_GOLD)
        self.assertGreaterEqual(modified, 3)

        self.assertEqual(self.grid.get_pixel(50, 50), MAT_GOLD)
        self.assertEqual(self.grid.get_pixel(51, 50), MAT_GOLD)
        self.assertEqual(self.grid.get_pixel(52, 50), MAT_GOLD)
        # Wall remains untouched
        self.assertEqual(self.grid.get_pixel(53, 50), MAT_WALL_BONE)

    def test_player_collects_biomass_gold(self):
        """Player picking up MAT_GOLD increments biomass_currency and removes pixel."""
        player = Player(x=20.0, y=20.0)
        initial_gold = player.biomass_currency

        # Place gold pixel in player's center body
        cx = int(player.center_x)
        cy = int(player.center_y)
        self.grid.set_pixel(cx, cy, MAT_GOLD)
        self.assertEqual(self.grid.get_pixel(cx, cy), MAT_GOLD)

        # Trigger environmental hazard check
        player._check_environmental_hazards(self.grid)

        self.assertEqual(player.biomass_currency, initial_gold + 1)
        self.assertEqual(self.grid.get_pixel(cx, cy), MAT_AIR)

    def test_wand_cast_transmutation_projectile(self):
        """Firing cannula with TRANSMUTE_FLESH_TO_ACID modifier and BONE_SPIKE creates transmuting projectile."""
        cannula = OrganCannula(
            name="Test Cannula",
            capacity=4,
            cast_delay=0.1,
            recharge_time=0.2,
            biomass_max=200.0,
            biomass_recharge=50.0,
            spread=0.0,
            shuffle=False,
        )
        cannula.slots[0] = GENE_DICT["TRANSMUTE_FLESH_TO_ACID"]
        cannula.slots[1] = GENE_DICT["BONE_SPIKE"]

        projectiles = evaluate_cannula_fire(cannula, origin_x=10.0, origin_y=10.0, base_angle=0.0)
        self.assertEqual(len(projectiles), 1)
        proj = projectiles[0]

        # Verify transmutation properties passed from modifier
        self.assertEqual(proj.transmute_target, MAT_ACID)
        self.assertEqual(proj.transmute_radius, 12)
        self.assertIn(MAT_TISSUE, proj.transmute_source)

        # Simulate impact at (50, 50) where tissue is present
        for y in range(40, 60):
            for x in range(40, 60):
                self.grid.set_pixel(x, y, MAT_TISSUE)
        proj._handle_impact(self.grid, 50, 50)
        self.assertEqual(self.grid.get_pixel(56, 50), MAT_ACID)

    def test_wand_cast_midas_enzyme(self):
        """MIDAS_ENZYME projectile fired from cannula has gold transmutation stats."""
        cannula = OrganCannula(
            name="Midas Cannula",
            capacity=2,
            cast_delay=0.1,
            recharge_time=0.2,
            biomass_max=200.0,
            biomass_recharge=50.0,
            spread=0.0,
            shuffle=False,
        )
        cannula.slots[0] = GENE_DICT["MIDAS_ENZYME"]

        projectiles = evaluate_cannula_fire(cannula, origin_x=20.0, origin_y=20.0, base_angle=0.0)
        self.assertEqual(len(projectiles), 1)
        midas_proj = projectiles[0]

        self.assertEqual(midas_proj.transmute_target, MAT_GOLD)
        self.assertEqual(midas_proj.transmute_radius, 16)
        self.assertIsNone(midas_proj.transmute_source)

        # Impact tissue with Midas projectile
        for y in range(50, 71):
            for x in range(50, 71):
                self.grid.set_pixel(x, y, MAT_TISSUE)
        midas_proj._handle_impact(self.grid, 60, 60)
        self.assertEqual(self.grid.get_pixel(68, 60), MAT_GOLD)


if __name__ == "__main__":
    unittest.main()
