"""Unit tests for ancient DNA lore tablet interaction, rewards, and codex persistence."""

import os
import tempfile
import unittest
import pygame

from py_noita.entities.player import Player
from py_noita.ui.codex import BioCodex
from py_noita.world.secrets import ANCIENT_TABLETS_DATA, DnaTablet


class TestLoreInteraction(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.codex_file = os.path.join(self.tmp_dir.name, "test_bio_codex.json")
        self.codex = BioCodex(filepath=self.codex_file)
        self.player = Player(x=100.0, y=100.0)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_dna_tablet_attributes(self):
        """DnaTablet provides title, lore text, and rewards (+50 biomass, +20 mutagen)."""
        tid, title, text = ANCIENT_TABLETS_DATA[0]
        tablet = DnaTablet(tid, 100.0, 100.0, title, text)
        self.assertEqual(tablet.bonus_biomass, 50)
        self.assertEqual(tablet.bonus_mutagen, 20)
        self.assertEqual(tablet.lore_text, text)
        self.assertTrue(tablet.alive)

    def test_lore_tablet_interaction_flow(self):
        """Interacting with tablet consumes it, awards currency, and unlocks codex entry."""
        tid, title, text = ANCIENT_TABLETS_DATA[1]
        tablet = DnaTablet(tid, 100.0, 100.0, title, text)
        tablet.is_near_player = True

        init_biomass = self.player.biomass_currency
        init_mutagen = self.codex.mutagen_essence

        # Simulate interaction logic from main.py
        tablet.alive = False
        self.player.biomass_currency += tablet.bonus_biomass
        self.codex.mutagen_essence += tablet.bonus_mutagen
        self.codex.unlock_lore_tablet(tablet.tablet_id)
        self.codex.save_codex()

        # Check rewards
        self.assertEqual(self.player.biomass_currency, init_biomass + 50)
        self.assertEqual(self.codex.mutagen_essence, init_mutagen + 20)
        self.assertIn(tablet.tablet_id, self.codex.unlocked_lore_tablets)

        # Reload codex from disk to verify persistence
        new_codex = BioCodex(filepath=self.codex_file)
        self.assertIn(tablet.tablet_id, new_codex.unlocked_lore_tablets)
        self.assertEqual(new_codex.mutagen_essence, init_mutagen + 20)


if __name__ == "__main__":
    unittest.main()
