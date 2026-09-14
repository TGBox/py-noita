"""Unit tests for Wand Wrapping, 250 Projectile Hard-Cap, and Recursive Loop Damping."""

import unittest

from py_noita.weapons.cannula import OrganCannula
from py_noita.weapons.deck_evaluator import (
    MAX_ACTIVE_PROJECTILES,
    evaluate_cannula_fire,
    evaluate_payload,
)
from py_noita.weapons.gene import GENE_DICT, Gene, GeneType
from py_noita.weapons.projectile import Projectile


class TestWandWrappingAndSafety(unittest.TestCase):
    def test_wand_wrapping_with_unspent_multicast(self):
        """Wand wrapping re-calls spells from discard to satisfy unspent multicast at deck end."""
        cannula = OrganCannula(
            name="Wrapping Wand",
            capacity=2,
            cast_delay=0.1,
            recharge_time=0.5,
            biomass_max=200.0,
            biomass_recharge=50.0,
            spread=0.0,
            shuffle=False,
        )
        cannula.slots[0] = GENE_DICT["BONE_SPIKE"]
        cannula.slots[1] = GENE_DICT["MULTI_DOUBLE"]

        # Shot 1: Draws BONE_SPIKE (pointer moves to 1)
        projs1 = evaluate_cannula_fire(cannula, 100.0, 100.0, 0.0)
        self.assertEqual(len(projs1), 1)
        self.assertEqual(projs1[0].damage, GENE_DICT["BONE_SPIKE"].damage)
        self.assertEqual(cannula.deck_pointer, 1)
        self.assertFalse(cannula.is_recharging)

        # Clear cast cooldown to simulate player next click
        cannula.cast_cooldown = 0.0

        # Shot 2: Draws MULTI_DOUBLE at end of deck -> wraps back to 0 -> draws BONE_SPIKE -> recharges
        projs2 = evaluate_cannula_fire(cannula, 100.0, 100.0, 0.0)
        self.assertEqual(len(projs2), 1)
        self.assertEqual(projs2[0].damage, GENE_DICT["BONE_SPIKE"].damage)
        self.assertEqual(cannula.deck_pointer, 0)
        self.assertTrue(cannula.is_recharging)

    def test_wand_wrapping_preserves_modifiers(self):
        """Wrapping draws modifier and projectile together on wrapped multicast."""
        cannula = OrganCannula(
            name="Modifier Wrapping Wand",
            capacity=3,
            cast_delay=0.1,
            recharge_time=0.5,
            biomass_max=200.0,
            biomass_recharge=50.0,
            spread=0.0,
            shuffle=False,
        )
        mod = GENE_DICT["MOD_DAMAGE_BOOST"]
        spike = GENE_DICT["BONE_SPIKE"]
        multi = GENE_DICT["MULTI_DOUBLE"]

        cannula.slots[0] = mod
        cannula.slots[1] = spike
        cannula.slots[2] = multi

        # Shot 1: Draws MOD_DAMAGE_BOOST + BONE_SPIKE (pointer moves to 2)
        projs1 = evaluate_cannula_fire(cannula, 100.0, 100.0, 0.0)
        self.assertEqual(len(projs1), 1)
        expected_damage = spike.damage + mod.damage
        self.assertEqual(projs1[0].damage, expected_damage)
        self.assertEqual(cannula.deck_pointer, 2)
        self.assertFalse(cannula.is_recharging)

        cannula.cast_cooldown = 0.0

        # Shot 2: Draws MULTI_DOUBLE -> wraps -> applies MOD_DAMAGE_BOOST -> casts BONE_SPIKE -> recharges
        projs2 = evaluate_cannula_fire(cannula, 100.0, 100.0, 0.0)
        self.assertEqual(len(projs2), 1)
        self.assertEqual(projs2[0].damage, expected_damage)
        self.assertEqual(cannula.deck_pointer, 0)
        self.assertTrue(cannula.is_recharging)

    def test_projectile_hard_cap_250(self):
        """Hard cap strictly limits active projectiles to 250 even with massive splits."""
        cannula = OrganCannula(
            name="Overkill Wand",
            capacity=6,
            cast_delay=0.1,
            recharge_time=0.1,
            biomass_max=1000.0,
            biomass_recharge=1000.0,
            spread=0.0,
            shuffle=False,
        )
        # 10x multiplier + Hexagon Multicast + Radial 12
        cannula.slots[0] = GENE_DICT["POLYMERASE_X10"]
        cannula.slots[1] = GENE_DICT["POLYMERASE_X10"]
        cannula.slots[2] = GENE_DICT["FORMATION_RADIAL_12"]
        cannula.slots[3] = GENE_DICT["BONE_SPIKE"]

        projs = evaluate_cannula_fire(cannula, 100.0, 100.0, 0.0)
        self.assertLessEqual(len(projs), MAX_ACTIVE_PROJECTILES)
        self.assertEqual(MAX_ACTIVE_PROJECTILES, 250)

    def test_endless_trigger_loop_damping_and_recursion_brake(self):
        """Trigger loops damp lifetime and damage per generation and terminate at depth 8."""
        # Create a self-triggering gene sequence
        trigger_gene = GENE_DICT["TRIGGER_HIT_BONE"]
        
        # Level 0 projectile
        proj0 = Projectile(
            x=100.0,
            y=100.0,
            vx=10.0,
            vy=0.0,
            damage=100.0,
            lifetime=100,
            payload_genes=[trigger_gene],
            trigger_depth=0,
        )

        # Trigger generation 1
        children1 = proj0._trigger_payload(110.0, 100.0)
        self.assertGreater(len(children1), 0)
        c1 = children1[0]
        self.assertEqual(c1.trigger_depth, 1)

        # Trigger generation 2
        c1.payload_genes = [trigger_gene]
        children2 = c1._trigger_payload(120.0, 100.0)
        self.assertGreater(len(children2), 0)
        c2 = children2[0]
        self.assertEqual(c2.trigger_depth, 2)
        # Verify damping: damage and lifetime are reduced
        self.assertLess(c2.damage, c1.damage)
        self.assertLess(c2.lifetime, c1.lifetime)

        # Advance to depth 7
        curr = c2
        for d in range(3, 8):
            curr.payload_genes = [trigger_gene]
            next_children = curr._trigger_payload(100.0 + d * 10, 100.0)
            self.assertGreater(len(next_children), 0)
            curr = next_children[0]
            self.assertEqual(curr.trigger_depth, d)

        # Child spawned at depth 8
        curr.payload_genes = [trigger_gene]
        c8_list = curr._trigger_payload(200.0, 100.0)
        self.assertEqual(len(c8_list), 1)
        c8 = c8_list[0]
        self.assertEqual(c8.trigger_depth, 8)

        # Calling _trigger_payload on depth 8 projectile triggers the recursion brake (0 spawned)
        c8.payload_genes = [trigger_gene]
        children_at_brake = c8._trigger_payload(210.0, 100.0)
        self.assertEqual(len(children_at_brake), 0)


if __name__ == "__main__":
    unittest.main()
