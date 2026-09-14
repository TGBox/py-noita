"""Unit tests for Procedural Inverse Kinematics, Tentacle Physics, and Amoeboid Squeezing."""

import math
import unittest
import numpy as np
import pygame

from py_noita.entities.enemy import Antibody, ChitinBeetle, Macrophage, ParasiteSpider, create_enemy
from py_noita.entities.player import Player
from py_noita.rendering.ik import (
    AmoeboidDeformation,
    ProceduralLeg,
    ProceduralTentacle,
    solve_2segment_ik,
    solve_chain_fabrik,
)
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import MAT_AIR, MAT_BONE, MAT_TISSUE


class TestProceduralIKAndAnimation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_2segment_ik_solver_geometry_and_reach(self):
        """Analytical 2-segment IK accurately reaches targets within radius and clamps out-of-reach."""
        l1, l2 = 8.0, 6.0
        # Reached target
        target = (9.0, 5.0)
        joint, tip = solve_2segment_ik(0.0, 0.0, target[0], target[1], l1, l2, bend_sign=1.0)

        # Distance from root to joint should equal l1
        dist_root_joint = math.hypot(joint[0], joint[1])
        self.assertAlmostEqual(dist_root_joint, l1, places=3)

        # Distance from joint to tip should equal l2
        dist_joint_tip = math.hypot(tip[0] - joint[0], tip[1] - joint[1])
        self.assertAlmostEqual(dist_joint_tip, l2, places=3)

        # Tip should reach target
        self.assertAlmostEqual(tip[0], target[0], places=2)
        self.assertAlmostEqual(tip[1], target[1], places=2)

        # Opposite bend sign gives mirrored knee
        joint_neg, _ = solve_2segment_ik(0.0, 0.0, target[0], target[1], l1, l2, bend_sign=-1.0)
        self.assertNotEqual(joint, joint_neg)

        # Far target outside radius stretches to max length (l1 + l2)
        far_target = (50.0, 0.0)
        _, far_tip = solve_2segment_ik(0.0, 0.0, far_target[0], far_target[1], l1, l2)
        dist_far = math.hypot(far_tip[0], far_tip[1])
        self.assertAlmostEqual(dist_far, l1 + l2, places=1)

    def test_fabrik_multi_segment_chain_convergence(self):
        """FABRIK chain preserves link lengths and reaches arbitrary target."""
        points = [(0.0, 0.0), (5.0, 0.0), (10.0, 0.0), (15.0, 0.0)]
        lengths = [5.0, 5.0, 5.0]
        target = (8.0, 9.0)

        res = solve_chain_fabrik(points, lengths, target[0], target[1], max_iters=5, tolerance=0.5)
        # Root remains at (0, 0)
        self.assertAlmostEqual(res[0][0], 0.0)
        self.assertAlmostEqual(res[0][1], 0.0)

        # Segment lengths must be preserved
        for i in range(len(lengths)):
            d = math.hypot(res[i + 1][0] - res[i][0], res[i + 1][1] - res[i][1])
            self.assertAlmostEqual(d, lengths[i], places=2)

        # End effector reaches near target
        tip_dist = math.hypot(res[-1][0] - target[0], res[-1][1] - target[1])
        self.assertLess(tip_dist, 1.0)

    def test_player_procedural_tentacles_wall_grip(self):
        """Player tentacles detect nearby solid walls, anchor their tips, and detach when moving away."""
        grid = SimulationGrid(100, 100)
        # Build vertical wall of tissue at x = 40
        grid.grid[20:60, 40] = MAT_TISSUE

        player = Player(46.0, 30.0)  # Close to wall (player.center_x ~ 50, wall at 40)
        self.assertGreater(len(player.tentacles), 0)

        # Update physics
        player.update_physics(grid)

        # At least one left-facing tentacle should find and anchor to the solid wall
        anchored_count = sum(1 for t in player.tentacles if t.anchored)
        self.assertGreaterEqual(anchored_count, 1)

        # Draw player to surface
        surf = pygame.Surface((100, 100))
        player.draw(surf, cam_x=0, cam_y=0)

        # Move player to open air away from wall at 40 and border wall at 99
        player.x = 65.0
        player.update_physics(grid)
        # All tentacles must have detached in open space
        self.assertFalse(any(t.anchored for t in player.tentacles))

    def test_chitin_beetle_and_spider_ik_legs(self):
        """Chitin beetle and parasite spider use articulated legs that step on ground."""
        grid = SimulationGrid(80, 80)
        # Flat bone floor at y = 50
        grid.grid[50:60, :] = MAT_BONE

        beetle = ChitinBeetle(30.0, 40.0)
        self.assertEqual(len(beetle.legs), 4)

        spider = ParasiteSpider(30.0, 40.0)
        self.assertEqual(len(spider.legs), 4)
        self.assertEqual(spider.display_name, "Parasiten-Spinne")

        # Step legs
        beetle.vx = 1.2
        beetle.update_physics(grid)

        # Feet should find footing near floor
        for leg in beetle.legs:
            self.assertGreaterEqual(leg.foot_y, 45.0)

        # Draw to surface without errors
        surf = pygame.Surface((80, 80))
        beetle.draw(surf, cam_x=0, cam_y=0)
        spider.draw(surf, cam_x=0, cam_y=0)

    def test_macrophage_amoeboid_squeezing(self):
        """Macrophage dynamically squishes horizontally when squeezing through a tight crevice."""
        grid = SimulationGrid(80, 80)
        # Place tight vertical crevice with walls at x = 35 and x = 45 (width = 10)
        grid.grid[30:50, 35] = MAT_BONE
        grid.grid[30:50, 45] = MAT_BONE

        # Macrophage placed with center at x = 40 (between walls 35 and 45)
        macrophage = Macrophage(32.0, 35.0)
        self.assertAlmostEqual(macrophage.center_x, 40.0)

        # Update macrophage inside narrow crevice
        for _ in range(10):
            macrophage.update_physics(grid)

        # Squeeze_x must compress (< 0.8) and squeeze_y elongate (> 1.2)
        self.assertLess(macrophage.deformation.squeeze_x, 0.8)
        self.assertGreater(macrophage.deformation.squeeze_y, 1.2)

        # Contour points must generate valid organic polygon
        surf = pygame.Surface((80, 80))
        macrophage.draw(surf, cam_x=0, cam_y=0)

    def test_create_enemy_factory_parasite_spider(self):
        """create_enemy instantiates PARASITE_SPIDER properly."""
        spider = create_enemy("PARASITE_SPIDER", 15.0, 25.0)
        self.assertIsInstance(spider, ParasiteSpider)
        self.assertEqual(spider.enemy_type, "PARASITE_SPIDER")


if __name__ == "__main__":
    unittest.main()
