"""Unit tests for enemy entities, AI routines, and flesh worm terrain digging."""

import unittest
from py_noita.entities.enemy import (
    Antibody,
    FleshWorm,
    Granulocyte,
    Macrophage,
    TumorCyst,
    create_enemy,
)
from py_noita.entities.ai import update_enemy_ai
from py_noita.entities.player import Player
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import MAT_AIR, MAT_TISSUE


class TestEnemies(unittest.TestCase):
    def setUp(self):
        self.grid = SimulationGrid(width=150, height=150)
        self.player = Player(x=75.0, y=75.0)

    def test_enemy_damage_and_death(self):
        """Verify enemy takes damage and dies when HP reaches 0."""
        macro = Macrophage(50.0, 50.0)
        initial_hp = macro.hp
        macro.take_damage(20.0)
        self.assertEqual(macro.hp, initial_hp - 20.0)
        self.assertTrue(macro.alive)

        macro.take_damage(100.0)
        self.assertEqual(macro.hp, 0.0)
        self.assertFalse(macro.alive)

    def test_antibody_ai_fires_projectile(self):
        """Verify antibody spots player and shoots a cytokine dart."""
        antibody = Antibody(60.0, 60.0)
        antibody.attack_cooldown = 0.0  # Ready to fire

        projs, _ = update_enemy_ai(antibody, self.player, self.grid, dt=0.016)
        self.assertEqual(len(projs), 1, "Antibody should fire projectile at player!")
        self.assertEqual(projs[0].owner, "ENEMY")

    def test_flesh_worm_carves_terrain(self):
        """Verify flesh worm carves tunnels through solid tissue as it moves."""
        # Fill area with solid tissue
        self.grid.fill_rect(20, 20, 100, 100, MAT_TISSUE)

        worm = FleshWorm(30.0, 50.0, num_segments=4)
        worm.target_angle = 0.0  # Move right

        # Advance worm 20 steps
        for _ in range(20):
            update_enemy_ai(worm, self.player, self.grid, dt=0.016)

        # Worm should have carved air pixels at its position
        wx, wy = int(worm.center_x), int(worm.center_y)
        self.assertEqual(self.grid.get_pixel(wx, wy), MAT_AIR, "Worm head must carve tunnels!")


if __name__ == "__main__":
    unittest.main()
