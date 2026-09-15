"""Unit tests for Mid-Run Quicksave and Crash-Recovery (SaveManager)."""

import os
from pathlib import Path
import shutil
import tempfile
import unittest
import numpy as np

from py_noita.rendering.camera import Camera
from py_noita.config import WORLD_HEIGHT, WORLD_WIDTH
from py_noita.entities.enemy import create_enemy
from py_noita.entities.player import Player
from py_noita.perks.perk_definitions import ALL_PERKS
from py_noita.perks.perk_manager import PerkManager
from py_noita.physics.physics_world import PhysicsWorld
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import MAT_ACID, MAT_BLOOD, MAT_BONE, MAT_TISSUE
from py_noita.system.save_manager import SaveManager
from py_noita.weapons.cannula import OrganCannula
from py_noita.weapons.gene import GENE_DICT
from py_noita.world.generator import LootCyst, WorldPortal
from py_noita.world.secrets import DnaTablet, GeneOrb
from py_noita.world.streamer import WorldStreamer


class MockAudio:
    class Music:
        def set_theme(self, biome_idx):
            pass

        def set_combat_intensity(self, intensity):
            pass

    def __init__(self):
        self.music = self.Music()


class MockGame:
    def __init__(self, w=128, h=128, seed=12345):
        self.world_seed = seed
        self.current_biome_index = 2
        self.state = "PLAYING"
        self.kills_this_run = 14
        self.earned_mutagen = 75
        self.has_primordial_genome = True
        self.core_boss_defeated = False
        self.ending_id = 0
        self.is_victory = False

        self.grid = SimulationGrid(w, h)
        self.physics_world = PhysicsWorld(self.grid)
        self.grid.physics_world = self.physics_world

        self.player = Player(45.0, 55.0)
        self.player.vx = 2.5
        self.player.vy = -1.2
        self.player.hp = 82.5
        self.player.max_hp = 120.0
        self.player.biomass_currency = 340
        self.player.orbs_collected = 2
        self.player.active_cannula_index = 1
        self.player.active_gland_index = 0

        c1 = OrganCannula(name="Kanüle 1", capacity=3)
        c2 = OrganCannula(name="Kanüle 2", capacity=2)
        self.player.cannulas = [c1, c2]

        # Equip a gene in player cannula 0
        if "ACID_SPIT" in GENE_DICT:
            self.player.cannulas[0].set_slot(0, GENE_DICT["ACID_SPIT"])

        # Fill first gland with acid
        self.player.glands[0].material_id = MAT_ACID
        self.player.glands[0].current_amount = 90

        self.perk_manager = PerkManager()
        if ALL_PERKS:
            self.perk_manager.add_perk(ALL_PERKS[0], self.player)

        self.enemies = [
            create_enemy("FLESH_WORM", 60.0, 70.0),
            create_enemy("TUMOR_CYST", 80.0, 85.0),
        ]
        self.loot_cysts = [LootCyst(30, 40, "GENE")]
        self.gene_orbs = [GeneOrb(1, 90, 100, "SPLIT_SHOT", "Spalt-Blase", "Verdoppelt Projektile")]
        self.dna_tablets = [DnaTablet(1, 20, 25, "Altes Pergament", "Das Fleisch erinnert sich.")]
        self.exit_portal = WorldPortal(110.0, 115.0)
        self.ascent_portal = None
        self.ascent_return_gateway = None
        self.secret_boss = None

        self.streamer = WorldStreamer(seed=seed)
        self.camera = Camera(w, h)
        self.projectiles = []
        self.explosion_debris = []
        self.audio = MockAudio()


class TestSaveManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.save_manager = SaveManager(save_dir=Path(self.temp_dir))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_and_restore_cycle(self):
        game = MockGame(w=128, h=128, seed=9999)
        # Put some materials into grid
        game.grid.set_material(25, 35, MAT_TISSUE)
        game.grid.set_material(26, 35, MAT_BLOOD)
        game.grid.set_material(27, 35, MAT_BONE)
        game.grid.stain_map[35, 25] = 128

        # Quicksave
        saved = self.save_manager.save_run(game)
        self.assertTrue(saved)
        self.assertTrue(self.save_manager.has_quicksave())

        # Check metadata
        info = self.save_manager.get_quicksave_info()
        self.assertIsNotNone(info)
        self.assertEqual(info["world_seed"], 9999)
        self.assertEqual(info["player_hp"], 82.5)
        self.assertEqual(info["player_max_hp"], 120.0)
        self.assertEqual(info["biomass"], 340)
        self.assertEqual(info["kills"], 14)

        # Create a fresh empty game to restore into
        game2 = MockGame(w=128, h=128, seed=1)
        game2.player.hp = 10.0
        game2.player.biomass_currency = 0

        # Load run
        loaded = self.save_manager.load_run(game2)
        self.assertTrue(loaded)

        # Verify restored fields
        self.assertEqual(game2.world_seed, 9999)
        self.assertEqual(game2.current_biome_index, 2)
        self.assertEqual(game2.kills_this_run, 14)
        self.assertEqual(game2.earned_mutagen, 75)
        self.assertTrue(game2.has_primordial_genome)

        # Verify player
        self.assertAlmostEqual(game2.player.x, 45.0, places=2)
        self.assertAlmostEqual(game2.player.y, 55.0, places=2)
        self.assertAlmostEqual(game2.player.hp, 82.5, places=2)
        self.assertEqual(game2.player.biomass_currency, 340)
        self.assertEqual(game2.player.active_cannula_index, 1)

        # Verify grid preservation
        self.assertEqual(game2.grid.get_material(25, 35), MAT_TISSUE)
        self.assertEqual(game2.grid.get_material(26, 35), MAT_BLOOD)
        self.assertEqual(game2.grid.get_material(27, 35), MAT_BONE)
        self.assertEqual(game2.grid.stain_map[35, 25], 128)

        # Verify cannula slots
        if "ACID_SPIT" in GENE_DICT:
            self.assertIsNotNone(game2.player.cannulas[0].slots[0])
            self.assertEqual(game2.player.cannulas[0].slots[0].id, "ACID_SPIT")

        # Verify gland
        self.assertEqual(game2.player.glands[0].material_id, MAT_ACID)
        self.assertEqual(game2.player.glands[0].current_amount, 90)

        # Verify perks
        if ALL_PERKS:
            self.assertEqual(len(game2.perk_manager.active_perks), 1)
            self.assertEqual(game2.perk_manager.active_perks[0].id, ALL_PERKS[0].id)

        # Verify enemies
        self.assertEqual(len(game2.enemies), 2)
        self.assertEqual(game2.enemies[0].enemy_type, "FLESH_WORM")
        self.assertEqual(game2.enemies[1].enemy_type, "TUMOR_CYST")

        # Verify portal
        self.assertIsNotNone(game2.exit_portal)
        self.assertAlmostEqual(game2.exit_portal.x, 110.0, places=2)

    def test_permadeath_deletion(self):
        game = MockGame()
        self.save_manager.save_run(game)
        self.assertTrue(self.save_manager.has_quicksave())

        self.save_manager.delete_quicksave()
        self.assertFalse(self.save_manager.has_quicksave())
        self.assertIsNone(self.save_manager.get_quicksave_info())


if __name__ == "__main__":
    unittest.main()
