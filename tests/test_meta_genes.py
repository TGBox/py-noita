"""Unit tests for Meta-Genes & Replication Catalysts: Polymerase Duplicators, RNA Loop, Ribosome Catalyst, Ur-Code Alpha/Omega."""

import os
import unittest
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.font.init()

from py_noita.entities.player import Player
from py_noita.weapons.cannula import OrganCannula
from py_noita.weapons.deck_evaluator import evaluate_cannula_fire
from py_noita.weapons.gene import GENE_DICT, GeneType


class TestMetaGenes(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.font.init()
        self.player = Player(x=100.0, y=100.0)

    def test_polymerase_x2_duplicates_projectile(self):
        """Polymerase x2 duplicates subsequent projectile."""
        cannula = OrganCannula(name="Poly2", capacity=4, cast_delay=0.1, recharge_time=0.5, biomass_max=200.0, biomass_recharge=100.0)
        cannula.add_gene(GENE_DICT["POLYMERASE_X2"])
        cannula.add_gene(GENE_DICT["BONE_SPIKE"])

        projs = evaluate_cannula_fire(cannula, 100.0, 100.0, 0.0, shooter=self.player)
        self.assertEqual(len(projs), 2, "Polymerase x2 must duplicate projectile into 2 projectiles!")

    def test_polymerase_x3_duplicates_modifier(self):
        """Polymerase x3 triplicates subsequent modifier on a projectile."""
        cannula = OrganCannula(name="Poly3", capacity=4, cast_delay=0.1, recharge_time=0.5, biomass_max=200.0, biomass_recharge=100.0)
        cannula.add_gene(GENE_DICT["POLYMERASE_X3"])
        cannula.add_gene(GENE_DICT["MOD_DAMAGE_BOOST"])  # +18 damage
        cannula.add_gene(GENE_DICT["BONE_SPIKE"])        # 15 base damage

        projs = evaluate_cannula_fire(cannula, 100.0, 100.0, 0.0, shooter=self.player)
        self.assertEqual(len(projs), 1)
        expected_damage = 15.0 + (18.0 * 3)  # 69.0
        self.assertEqual(projs[0].damage, expected_damage, "Modifier must be applied 3 times!")

    def test_polymerase_x10_mass_replication(self):
        """Polymerase x10 produces 10 copies of the target projectile."""
        cannula = OrganCannula(name="Poly10", capacity=4, cast_delay=0.1, recharge_time=0.5, biomass_max=300.0, biomass_recharge=100.0)
        cannula.add_gene(GENE_DICT["POLYMERASE_X10"])
        cannula.add_gene(GENE_DICT["RIBOSOME_BEAD"])

        projs = evaluate_cannula_fire(cannula, 100.0, 100.0, 0.0, shooter=self.player)
        self.assertEqual(len(projs), 10, "Polymerase x10 must emit 10 projectile instances!")

    def test_polymerase_recursion_brake(self):
        """Chaining multiple Polymerase duplicators activates recursion brake."""
        cannula = OrganCannula(name="Brake", capacity=6, cast_delay=0.1, recharge_time=0.5, biomass_max=500.0, biomass_recharge=100.0)
        cannula.add_gene(GENE_DICT["POLYMERASE_X2"])
        cannula.add_gene(GENE_DICT["POLYMERASE_X3"])
        cannula.add_gene(GENE_DICT["POLYMERASE_X4"])
        cannula.add_gene(GENE_DICT["POLYMERASE_X10"])
        cannula.add_gene(GENE_DICT["BONE_SPIKE"])

        # Should execute safely without freeze or massive uncontrolled allocation
        projs = evaluate_cannula_fire(cannula, 100.0, 100.0, 0.0, shooter=self.player)
        self.assertGreater(len(projs), 0)
        self.assertLessEqual(len(projs), 250, "Recursion brake must prevent exceeding safety bounds!")

    def test_ur_code_alpha_copies_first_gene(self):
        """Ur-Code Alpha copies the first gene in the cannula."""
        cannula = OrganCannula(name="Alpha", capacity=4, cast_delay=0.1, recharge_time=0.5, biomass_max=200.0, biomass_recharge=100.0)
        cannula.add_gene(GENE_DICT["CYTOKINE_LASER"])
        cannula.add_gene(GENE_DICT["UR_CODE_ALPHA"])

        # First cast fires Cytokine Laser
        projs1 = evaluate_cannula_fire(cannula, 100.0, 100.0, 0.0, shooter=self.player)
        self.assertEqual(len(projs1), 1)

        # Reset cooldown for next cast
        cannula.cast_cooldown = 0.0
        cannula.recharge_cooldown = 0.0

        # Second cast is Ur-Code Alpha, which replicates the first gene (Cytokine Laser)
        projs2 = evaluate_cannula_fire(cannula, 100.0, 100.0, 0.0, shooter=self.player)
        self.assertEqual(len(projs2), 1)
        self.assertEqual(projs2[0].damage, GENE_DICT["CYTOKINE_LASER"].damage)

    def test_ur_code_omega_copies_last_gene(self):
        """Ur-Code Omega copies the last gene in the cannula."""
        cannula = OrganCannula(name="Omega", capacity=4, cast_delay=0.1, recharge_time=0.5, biomass_max=200.0, biomass_recharge=100.0)
        cannula.add_gene(GENE_DICT["UR_CODE_OMEGA"])
        cannula.add_gene(GENE_DICT["ACID_GLOBULE"])

        projs = evaluate_cannula_fire(cannula, 100.0, 100.0, 0.0, shooter=self.player)
        self.assertEqual(len(projs), 1)
        self.assertEqual(projs[0].damage, GENE_DICT["ACID_GLOBULE"].damage)

    def test_circular_rna_loop(self):
        """Circular RNA Loop re-triggers the head gene."""
        cannula = OrganCannula(name="Loop", capacity=4, cast_delay=0.1, recharge_time=0.5, biomass_max=200.0, biomass_recharge=100.0)
        cannula.add_gene(GENE_DICT["PLASMA_TENDRIL"])
        cannula.add_gene(GENE_DICT["CIRCULAR_RNA_LOOP"])

        projs1 = evaluate_cannula_fire(cannula, 100.0, 100.0, 0.0, shooter=self.player)
        self.assertEqual(len(projs1), 1)

        # Reset cooldown for next cast
        cannula.cast_cooldown = 0.0
        cannula.recharge_cooldown = 0.0

        projs2 = evaluate_cannula_fire(cannula, 100.0, 100.0, 0.0, shooter=self.player)
        self.assertEqual(len(projs2), 1)
        self.assertEqual(projs2[0].pattern, "HELIX_A")


    def test_ribosome_catalyst_life_drain_when_empty_biomass(self):
        """Ribosome Catalyst casts without biomass by drawing HP when empty."""
        cannula = OrganCannula(name="Ribosome", capacity=4, cast_delay=0.1, recharge_time=0.5, biomass_max=0.0, biomass_recharge=0.0)
        cannula.current_biomass = 0.0
        cannula.add_gene(GENE_DICT["RIBOSOME_CATALYST"])
        cannula.add_gene(GENE_DICT["BONE_SPIKE"])

        initial_hp = self.player.hp
        projs = evaluate_cannula_fire(cannula, 100.0, 100.0, 0.0, shooter=self.player)
        self.assertEqual(len(projs), 1)
        self.assertLess(self.player.hp, initial_hp, "HP should be drained when casting with 0 biomass!")


if __name__ == "__main__":
    unittest.main()
