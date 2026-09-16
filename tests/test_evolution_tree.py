"""Unit tests for the Bio-Laboratory and Evolution Mutation Tree UI."""

import os
import tempfile
import unittest
from pathlib import Path
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.font.init()

from py_noita.ui.codex import BioCodex
from py_noita.ui.evolution_tree import ALL_TREE_NODES, EvolutionTreeUI


class TestEvolutionTree(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.codex_file = Path(self.temp_dir) / "test_bio_codex.json"
        self.codex = BioCodex(filepath=str(self.codex_file))
        self.tree = EvolutionTreeUI(self.codex)

    def test_tree_structure_and_nodes(self):
        """Verify the tree has root, acid branch, synaptic branch, and meta/orb branch."""
        self.assertGreaterEqual(len(self.tree.nodes), 8)
        root = self.tree.get_node_by_id("NODE_ROOT_PARASITE")
        self.assertIsNotNone(root)
        self.assertEqual(root.cost, 0)
        self.assertTrue(self.tree.is_node_unlocked(root))

        # Check acid branch
        acid = self.tree.get_node_by_id("NODE_ACID_SYNTH")
        self.assertIsNotNone(acid)
        self.assertEqual(acid.cost, 80)
        self.assertIn("NODE_ROOT_PARASITE", acid.parents)

        # Check synaptic branch
        synaptic = self.tree.get_node_by_id("NODE_SYNAPTIC_LEECH")
        self.assertIsNotNone(synaptic)
        self.assertEqual(synaptic.cost, 150)
        self.assertIn("NODE_ROOT_PARASITE", synaptic.parents)

        # Check meta branch
        orb = self.tree.get_node_by_id("NODE_PRIMORDIAL_NUCLEUS")
        self.assertIsNotNone(orb)
        self.assertIn("NODE_MUTAGEN_HARVESTER", orb.parents)

    def test_node_locking_and_purchasing(self):
        """Verify unlock prerequisites, balance checks, and persistent storage."""
        acid_node = self.tree.get_node_by_id("NODE_ACID_SYNTH")
        corrosive_node = self.tree.get_node_by_id("NODE_CORROSIVE_METABOLISM")

        # 1. Initially player has 0 mutagen -> cannot unlock acid node
        self.codex.mutagen_essence = 0
        self.assertFalse(self.tree.can_unlock_node(acid_node))

        # Corrosive node has parent locked -> cannot unlock even with lots of mutagen
        self.codex.mutagen_essence = 500
        self.assertFalse(self.tree.can_unlock_node(corrosive_node))
        self.assertFalse(self.tree.are_parents_unlocked(corrosive_node))

        # 2. Acid node parent (ROOT) is unlocked -> can unlock with 80+ mutagen
        self.assertTrue(self.tree.are_parents_unlocked(acid_node))
        self.assertTrue(self.tree.can_unlock_node(acid_node))

        # 3. Select acid node and purchase via [RETURN]
        for i, n in enumerate(self.tree.nodes):
            if n.node_id == "NODE_ACID_SYNTH":
                self.tree.selected_node_index = i
                break

        event_enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        self.tree.handle_event(event_enter, 640, 360)

        # Acid node is now unlocked and mutagen deducted
        self.assertTrue(self.tree.is_node_unlocked(acid_node))
        self.assertEqual(self.codex.mutagen_essence, 500 - 80)
        self.assertIn("STRAIN_ACID_SYNTH", self.codex.unlocked_strains)

        # 4. Now corrosive node parent is unlocked -> can unlock corrosive node
        self.assertTrue(self.tree.are_parents_unlocked(corrosive_node))
        self.assertTrue(self.tree.can_unlock_node(corrosive_node))

        # 5. Persistent reload from disk
        loaded_codex = BioCodex(filepath=str(self.codex_file))
        self.assertIn("NODE_ACID_SYNTH", loaded_codex.unlocked_tree_nodes)
        self.assertIn("STRAIN_ACID_SYNTH", loaded_codex.unlocked_strains)
        self.assertEqual(loaded_codex.mutagen_essence, 420)

    def test_navigation_and_rendering(self):
        """Verify directional navigation and rendering of the tree canvas."""
        surf = pygame.Surface((640, 360))
        self.tree.draw(surf)

        # Test navigation keys
        initial_idx = self.tree.selected_node_index
        event_down = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN)
        self.tree.handle_event(event_down, 640, 360)
        # Should navigate to a node lower in Y
        new_node = self.tree.nodes[self.tree.selected_node_index]
        self.assertGreater(new_node.pos[1], 100)

        # Test ESC to exit back to menu
        event_esc = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        exit_tree = self.tree.handle_event(event_esc, 640, 360)
        self.assertTrue(exit_tree)


if __name__ == "__main__":
    unittest.main()
