"""Unit tests for Organ-Cannula wand deck evaluation, modifiers, and triggers."""

import unittest
from py_noita.simulation.grid import SimulationGrid
from py_noita.weapons.cannula import OrganCannula
from py_noita.weapons.gene import GENE_DICT, Gene, GeneType
from py_noita.weapons.deck_evaluator import evaluate_cannula_fire


class TestDeckEvaluator(unittest.TestCase):
    def setUp(self):
        self.cannula = OrganCannula(
            name="Test-Kanüle",
            capacity=6,
            cast_delay=0.1,
            recharge_time=0.4,
            biomass_max=150.0,
            biomass_recharge=50.0,
            spread=2.0,
            shuffle=False,
        )

    def test_single_projectile_cast(self):
        """Test basic single projectile casting and biomass deduction."""
        spike = GENE_DICT["BONE_SPIKE"]
        self.cannula.add_gene(spike)

        initial_biomass = self.cannula.current_biomass
        projs = evaluate_cannula_fire(self.cannula, 100.0, 100.0, 0.0)

        self.assertEqual(len(projs), 1)
        self.assertEqual(projs[0].damage, spike.damage)
        self.assertEqual(self.cannula.current_biomass, initial_biomass - spike.biomass_cost)
        self.assertTrue(self.cannula.is_recharging)  # Reached end of 1-card deck

    def test_modifier_application(self):
        """Test that modifier genes enhance subsequent projectiles."""
        mod_burn = GENE_DICT["MOD_NECROTIC_BURN"]
        spike = GENE_DICT["BONE_SPIKE"]

        self.cannula.add_gene(mod_burn)
        self.cannula.add_gene(spike)

        projs = evaluate_cannula_fire(self.cannula, 100.0, 100.0, 0.0)
        self.assertEqual(len(projs), 1)
        # Damage should be spike.damage + mod_burn.damage
        self.assertEqual(projs[0].damage, spike.damage + mod_burn.damage)
        self.assertEqual(projs[0].impact_material, mod_burn.impact_material)

    def test_multicast(self):
        """Test multicast evaluates multiple projectiles in one burst."""
        multi_double = GENE_DICT["MULTI_DOUBLE"]
        spike = GENE_DICT["BONE_SPIKE"]
        needle = GENE_DICT["BILE_NEEDLE"]

        self.cannula.add_gene(multi_double)
        self.cannula.add_gene(spike)
        self.cannula.add_gene(needle)

        projs = evaluate_cannula_fire(self.cannula, 100.0, 100.0, 0.0)
        self.assertEqual(len(projs), 2)
        damages = [p.damage for p in projs]
        self.assertIn(spike.damage, damages)
        self.assertIn(needle.damage, damages)

    def test_trigger_payload_execution(self):
        """Test trigger gene bundles subsequent gene and fires it on impact."""
        trigger_bone = GENE_DICT["TRIGGER_HIT_BONE"]
        acid = GENE_DICT["ACID_GLOBULE"]

        self.cannula.add_gene(trigger_bone)
        self.cannula.add_gene(acid)

        projs = evaluate_cannula_fire(self.cannula, 100.0, 100.0, 0.0)
        self.assertEqual(len(projs), 1)
        trigger_proj = projs[0]
        self.assertEqual(len(trigger_proj.payload_genes), 1)
        self.assertEqual(trigger_proj.payload_genes[0].id, "ACID_GLOBULE")

        # Simulate projectile hitting terrain in a grid
        grid = SimulationGrid(100, 100)
        # Create solid wall at x=60
        grid.fill_rect(60, 0, 10, 100, 1)  # MAT_TISSUE

        # Position projectile moving towards wall
        trigger_proj.x = 55.0
        trigger_proj.y = 50.0
        trigger_proj.vx = 8.0
        trigger_proj.vy = 0.0

        children = trigger_proj.update(grid)
        self.assertFalse(trigger_proj.alive, "Trigger projectile should die on impact")
        self.assertEqual(len(children), 1, "Payload gene should spawn child projectile on impact")
        self.assertEqual(children[0].damage, acid.damage)


if __name__ == "__main__":
    unittest.main()
