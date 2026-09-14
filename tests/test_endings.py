"""Unit tests for the three alternative endings, endgame quests, BrainCoreBoss scaling, and portals."""

import os
import unittest
import pygame

# Headless pygame setup for tests
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.font.init()

from py_noita.entities.bosses import BrainCoreBoss
from py_noita.entities.player import Player
from py_noita.main import Game, STATE_GAME_OVER, STATE_PLAYING
from py_noita.simulation.grid import SimulationGrid
from py_noita.ui.game_over import GameOverScreen
from py_noita.world.biome import BIOME_EPIDERMIS, BIOME_PRIMORDIAL_CORE
from py_noita.world.endings import (
    ENDING_COSMIC_METAMORPHOSIS,
    ENDING_HOST_DEATH,
    ENDING_NONE,
    ENDING_SYMBIOSIS,
    ENDINGS,
    AscentReturnGateway,
    SurfaceAscentPortal,
)
from py_noita.world.generator import generate_world_level


class TestEndings(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.font.init()
        self.grid = SimulationGrid(width=200, height=260)
        self.player = Player(x=100.0, y=100.0)


    def test_endings_data_completeness(self):
        """Verify all three alternative endings are properly defined with rich lore."""
        self.assertIn(ENDING_HOST_DEATH, ENDINGS)
        self.assertIn(ENDING_SYMBIOSIS, ENDINGS)
        self.assertIn(ENDING_COSMIC_METAMORPHOSIS, ENDINGS)

        for eid, ending in ENDINGS.items():
            self.assertTrue(len(ending.title) > 0)
            self.assertTrue(len(ending.sub_title) > 0)
            self.assertTrue(len(ending.lore_text) > 20)
            self.assertEqual(len(ending.color), 3)
            self.assertGreater(ending.bonus_mutagen, 0)
            self.assertTrue(len(ending.achievement_unlocked) > 0)

    def test_surface_ascent_portal(self):
        """Test SurfaceAscentPortal proximity detection and drawing."""
        portal = SurfaceAscentPortal(x=100.0, y=24.0)
        self.assertTrue(portal.is_player_inside(100.0, 24.0))
        self.assertTrue(portal.is_player_inside(105.0, 28.0))
        self.assertFalse(portal.is_player_inside(150.0, 100.0))

        portal.update()
        self.assertGreater(portal.anim_time, 0.0)

        surf = pygame.Surface((200, 200))
        font = pygame.font.SysFont("Arial", 10)
        portal.draw(surf, cam_x=0, cam_y=0, font=font)

    def test_ascent_return_gateway(self):
        """Test AscentReturnGateway proximity and drawing."""
        gateway = AscentReturnGateway(x=120.0, y=80.0)
        self.assertTrue(gateway.is_player_inside(120.0, 80.0))
        self.assertFalse(gateway.is_player_inside(200.0, 200.0))

        gateway.update()
        self.assertGreater(gateway.anim_time, 0.0)

        surf = pygame.Surface((200, 200))
        font = pygame.font.SysFont("Arial", 10)
        gateway.draw(surf, cam_x=0, cam_y=0, font=font)

    def test_brain_core_boss_scaling_by_dna_orbs(self):
        """Verify BrainCoreBoss scales max HP and damage based on player's collected DNA Orbs."""
        # 0 Orbs collected
        boss_0 = BrainCoreBoss(100.0, 100.0, orbs_collected=0)
        self.assertEqual(boss_0.hp, 600.0)
        self.assertEqual(boss_0.scaling, 1.0)

        # 5 Orbs collected
        boss_5 = BrainCoreBoss(100.0, 100.0, orbs_collected=5)
        self.assertAlmostEqual(boss_5.hp, 600.0 * (1.0 + 0.18 * 5), places=1)
        self.assertGreater(boss_5.hp, boss_0.hp)

        # 11 Orbs collected (Full completion)
        boss_11 = BrainCoreBoss(100.0, 100.0, orbs_collected=11)
        self.assertAlmostEqual(boss_11.hp, 600.0 * (1.0 + 0.18 * 11), places=1)
        self.assertGreater(boss_11.hp, boss_5.hp)

        # Boss projectile attack generation
        projs, minions = boss_0.update_boss(self.player, self.grid, dt=3.0)
        self.assertGreater(len(projs), 0)
        for p in projs:
            self.assertEqual(p.owner, "ENEMY")
            self.assertGreater(p.damage, 0)

    def test_generator_spawns_core_boss_and_ascent_portal(self):
        """Verify Biome 8 spawns BrainCoreBoss and Biome 1 spawns SurfaceAscentPortal."""
        # Primordial Core Biome (Biome 8)
        _, _, _, _, _, _, core_boss = generate_world_level(
            self.grid, BIOME_PRIMORDIAL_CORE, orbs_collected=7, seed=999
        )
        self.assertIsNotNone(core_boss)
        self.assertIsInstance(core_boss, BrainCoreBoss)
        self.assertEqual(core_boss.orbs_buff, 7)

        # Epidermis Biome (Biome 1)
        self.grid = SimulationGrid(width=200, height=260)
        generate_world_level(self.grid, BIOME_EPIDERMIS, seed=123)
        self.assertIsNotNone(self.grid.ascent_portal)
        self.assertIsInstance(self.grid.ascent_portal, SurfaceAscentPortal)

    def test_game_over_screen_all_endings(self):
        """Test rendering GameOverScreen with all endings and victory states."""
        screen = GameOverScreen()
        surf = pygame.Surface((320, 240))

        # Defeat
        screen.draw(surf, victory=False, depth=4, kills=12, biomass=80, earned_mutagen=10, total_mutagen=50)

        # Ending 1: Host Death
        screen.draw(
            surf, victory=True, depth=8, kills=30, biomass=300, earned_mutagen=120, total_mutagen=180,
            ending_id=ENDING_HOST_DEATH, orbs_collected=3,
        )

        # Ending 2: Symbiosis
        screen.draw(
            surf, victory=True, depth=8, kills=45, biomass=600, earned_mutagen=400, total_mutagen=500,
            ending_id=ENDING_SYMBIOSIS, orbs_collected=11,
        )

        # Ending 3: Cosmic Metamorphosis
        screen.draw(
            surf, victory=True, depth=1, kills=50, biomass=800, earned_mutagen=550, total_mutagen=700,
            ending_id=ENDING_COSMIC_METAMORPHOSIS, orbs_collected=11,
        )

    def test_game_trigger_endings(self):
        """Verify game.trigger_ending transitions state, sets victory flag, and saves mutagen reward."""
        game = Game()
        initial_mutagen = game.codex.mutagen_essence

        # Trigger Ending 1
        game.player = Player(100.0, 100.0)
        game.player.biomass_currency = 150
        game.trigger_ending(ENDING_HOST_DEATH)
        self.assertEqual(game.state, STATE_GAME_OVER)
        self.assertTrue(game.is_victory)
        self.assertEqual(game.ending_id, ENDING_HOST_DEATH)
        self.assertGreater(game.earned_mutagen, 0)
        self.assertGreater(game.codex.mutagen_essence, initial_mutagen)

        # Trigger Ending 3
        mut_before_3 = game.codex.mutagen_essence
        game.trigger_ending(ENDING_COSMIC_METAMORPHOSIS)
        self.assertEqual(game.ending_id, ENDING_COSMIC_METAMORPHOSIS)
        self.assertGreater(game.codex.mutagen_essence, mut_before_3)


if __name__ == "__main__":
    unittest.main()
