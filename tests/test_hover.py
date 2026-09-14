"""Unit tests for hover target inspection and tooltip display."""

import unittest
import pygame

from py_noita.entities.enemy import Antibody, FleshWorm, Granulocyte, Macrophage
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import (
    MAT_ACID,
    MAT_AIR,
    MAT_BLOOD,
    MAT_BONE,
    MAT_TISSUE,
    MAT_WATER,
)
from py_noita.ui.hover_info import HoverTarget, get_hover_target
from py_noita.ui.hud import HUD


class TestHoverInfo(unittest.TestCase):
    """Tests for Noita-style hover information detection."""

    def setUp(self):
        pygame.init()
        self.grid = SimulationGrid(width=100, height=100)

    def tearDown(self):
        pygame.quit()

    def test_hover_air_returns_none(self):
        """Hovering over empty air should return None."""
        self.grid.set_pixel(10, 10, MAT_AIR)
        target = get_hover_target(self.grid, [], 10.0, 10.0)
        self.assertIsNone(target)

    def test_hover_out_of_bounds_returns_none(self):
        """Hovering outside the grid should return None without throwing."""
        self.assertIsNone(get_hover_target(self.grid, [], -5.0, 10.0))
        self.assertIsNone(get_hover_target(self.grid, [], 150.0, 10.0))
        self.assertIsNone(get_hover_target(self.grid, [], 10.0, -2.0))
        self.assertIsNone(get_hover_target(self.grid, [], 10.0, 200.0))

    def test_hover_liquids(self):
        """Hovering over liquid pixels displays liquid name and category."""
        # Blood
        self.grid.set_pixel(20, 20, MAT_BLOOD)
        t_blood = get_hover_target(self.grid, [], 20.0, 20.0)
        self.assertIsNotNone(t_blood)
        self.assertEqual(t_blood.target_type, "MATERIAL")
        self.assertEqual(t_blood.name, "Blut")
        self.assertEqual(t_blood.category, "Flüssigkeit")

        # Acid
        self.grid.set_pixel(25, 25, MAT_ACID)
        t_acid = get_hover_target(self.grid, [], 25.0, 25.0)
        self.assertIsNotNone(t_acid)
        self.assertEqual(t_acid.name, "Säure")
        self.assertEqual(t_acid.category, "Flüssigkeit")

        # Water
        self.grid.set_pixel(30, 30, MAT_WATER)
        t_water = get_hover_target(self.grid, [], 30.0, 30.0)
        self.assertIsNotNone(t_water)
        self.assertEqual(t_water.name, "Wasser")
        self.assertEqual(t_water.category, "Flüssigkeit")

    def test_hover_solids(self):
        """Hovering over solid pixels displays material name and category."""
        self.grid.set_pixel(40, 40, MAT_TISSUE)
        t_tissue = get_hover_target(self.grid, [], 40.0, 40.0)
        self.assertIsNotNone(t_tissue)
        self.assertEqual(t_tissue.name, "Gewebe")
        self.assertEqual(t_tissue.category, "Feststoff")

        self.grid.set_pixel(45, 45, MAT_BONE)
        t_bone = get_hover_target(self.grid, [], 45.0, 45.0)
        self.assertIsNotNone(t_bone)
        self.assertEqual(t_bone.name, "Knochen")
        self.assertEqual(t_bone.category, "Feststoff")

    def test_hover_enemies(self):
        """Hovering over enemies returns enemy info and current HP."""
        macro = Macrophage(50.0, 50.0)
        anti = Antibody(70.0, 70.0)
        gran = Granulocyte(15.0, 80.0)

        # Macrophage
        t1 = get_hover_target(self.grid, [macro, anti], 52.0, 52.0)
        self.assertIsNotNone(t1)
        self.assertEqual(t1.target_type, "ENEMY")
        self.assertEqual(t1.name, "Makrophage")
        self.assertEqual(t1.category, "Gegner")
        self.assertEqual(t1.current_hp, 45.0)
        self.assertEqual(t1.max_hp, 45.0)

        # Antibody
        t2 = get_hover_target(self.grid, [macro, anti], 72.0, 72.0)
        self.assertIsNotNone(t2)
        self.assertEqual(t2.name, "Antikörper")

        # Granulocyte
        t3 = get_hover_target(self.grid, [gran], 18.0, 82.0)
        self.assertIsNotNone(t3)
        self.assertEqual(t3.name, "Granulozyt")

    def test_hover_fleshworm_segments(self):
        """Hovering over any segment of a FleshWorm identifies the enemy."""
        worm = FleshWorm(50.0, 50.0, num_segments=5)
        # Position segments distinctly
        for i, seg in enumerate(worm.segments):
            seg.x = 50.0 - i * 8.0
            seg.y = 50.0

        # Hover over tail segment (segment 4 is around x=18, y=50)
        tail_x = worm.segments[4].x
        tail_y = worm.segments[4].y
        t_worm = get_hover_target(self.grid, [worm], tail_x, tail_y)
        self.assertIsNotNone(t_worm)
        self.assertEqual(t_worm.target_type, "ENEMY")
        self.assertEqual(t_worm.name, "Fleischwurm")

    def test_enemy_priority_over_liquid_and_dead_enemy_ignored(self):
        """Living enemy takes priority over liquid beneath; dead enemy is ignored."""
        macro = Macrophage(20.0, 20.0)
        self.grid.set_pixel(22, 22, MAT_BLOOD)

        # While alive: Enemy returned
        t_alive = get_hover_target(self.grid, [macro], 22.0, 22.0)
        self.assertEqual(t_alive.target_type, "ENEMY")
        self.assertEqual(t_alive.name, "Makrophage")

        # When dead: Blood beneath returned
        macro.alive = False
        t_dead = get_hover_target(self.grid, [macro], 22.0, 22.0)
        self.assertEqual(t_dead.target_type, "MATERIAL")
        self.assertEqual(t_dead.name, "Blut")

    def test_hud_draw_hover_tooltip_render(self):
        """Ensure HUD draws both enemy and material tooltips onto surface without errors."""
        hud = HUD()
        surface = pygame.Surface((480, 270))

        # Enemy target
        target_enemy = HoverTarget(
            target_type="ENEMY",
            name="Makrophage",
            category="Gegner",
            color=(210, 200, 110),
            current_hp=30.0,
            max_hp=45.0,
        )
        hud._draw_hover_tooltip(surface, target_enemy, mx=50, my=50)

        # Clamping near bottom-right screen edge
        hud._draw_hover_tooltip(surface, target_enemy, mx=475, my=265)

        # Material target
        target_mat = HoverTarget(
            target_type="MATERIAL",
            name="Säure",
            category="Flüssigkeit",
            color=(65, 245, 30),
        )
        hud._draw_hover_tooltip(surface, target_mat, mx=100, my=100)
        hud._draw_hover_tooltip(surface, target_mat, mx=470, my=260)


if __name__ == "__main__":
    unittest.main()
