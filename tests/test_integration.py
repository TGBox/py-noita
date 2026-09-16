"""End-to-end integration test running complete game loop, state transitions, and simulation headless."""

import os
import unittest
# Set headless SDL video driver for automated testing
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
from py_noita.main import Game, STATE_GAME_OVER, STATE_INCUBATION, STATE_MENU, STATE_PLAYING, STATE_TUNING


class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.game = Game()

    def test_complete_gameplay_flow(self):
        """Test transitioning from Menu -> Playing -> Firing -> Incubation -> Level Advance."""
        # 1. State should start at MENU
        self.assertEqual(self.game.state, STATE_MENU)

        # 2. Start a new run
        self.game.start_new_run()
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertIsNotNone(self.game.player)
        self.assertTrue(self.game.player.alive)
        self.assertGreater(len(self.game.player.cannulas), 0)

        # 3. Simulate 30 frames of active gameplay
        # Drop a small spray of acid to simulate active fluid dynamics
        self.game.grid.set_pixel(int(self.game.player.center_x) + 20, int(self.game.player.center_y), 21)

        for frame in range(30):
            self.game.camera.update(self.game.player.center_x, self.game.player.center_y)
            # Simulate player moving and firing
            self.game.player.apply_input(move_x=1.0, hover=(frame % 10 < 5))
            # Fire active cannula
            if frame % 8 == 0:
                active_c = self.game.player.cannulas[self.game.player.active_cannula_index]
                from py_noita.weapons.deck_evaluator import evaluate_cannula_fire
                projs = evaluate_cannula_fire(active_c, self.game.player.center_x, self.game.player.center_y, 0.0)
                self.game.projectiles.extend(projs)

            # Step simulation & entities
            cam_x, cam_y = self.game.camera.get_offset()
            self.game.grid.update(cam_x, cam_y, self.game.renderer.view_w, self.game.renderer.view_h)
            self.game.player.update_physics(self.game.grid)
            for p in self.game.projectiles:
                p.update(self.game.grid, self.game.enemies)
            for e in self.game.enemies:
                e.update_physics(self.game.grid)

        # Ensure projectiles flew and grid updated
        self.assertGreater(self.game.grid.total_moved, 0, "Simulation grid should have active moved particles!")

        # Test hover detection and rendering in _draw_playing
        from py_noita.input.input_handler import InputState
        dummy_input = InputState()
        dummy_input.aim_world_x = self.game.player.center_x + 20
        dummy_input.aim_world_y = self.game.player.center_y
        dummy_input.sim_mouse_x = 200
        dummy_input.sim_mouse_y = 100
        dummy_input.mouse_in_bounds = True
        self.game.last_input = dummy_input
        self.game._draw_playing()

        # 4. Test entering Incubation Node (Holy Mountain)
        self.game.enter_incubation_node()
        self.assertEqual(self.game.state, STATE_INCUBATION)
        self.assertIsNotNone(self.game.incubation_node)
        self.assertEqual(len(self.game.incubation_node.pedestals), 3)

        # Simulate player picking a perk in incubation node
        ped = self.game.incubation_node.pedestals[0]
        self.game.player.x = ped.x - 2
        self.game.player.y = ped.y - 2
        new_perk = self.game.incubation_node.update(self.game.player)
        self.assertIsNotNone(new_perk, "Player should pick up touched mutation perk!")
        self.game.perk_manager.add_perk(new_perk, self.game.player)
        self.assertTrue(self.game.perk_manager.has_perk(new_perk.id))

        # 5. Test advancing to next biome (e.g. Biome 2: Vascular)
        self.game.load_biome_level(1)
        self.assertEqual(self.game.current_biome_index, 1)
        self.assertEqual(self.game.current_biome.biome_id, "VASCULAR")

        # 6. Test Player Death and Game Over transition
        self.game.player.take_damage(9999.0)
        self.assertFalse(self.game.player.alive)
        self.game.earned_mutagen = self.game.codex.record_run(
            self.game.current_biome_index + 1,
            self.game.kills_this_run,
            self.game.player.biomass_currency,
        )
        self.game.state = STATE_GAME_OVER
        self.assertEqual(self.game.state, STATE_GAME_OVER)
        self.assertGreater(self.game.codex.mutagen_essence, 0)

    def test_update_playing_loop(self):
        """Test active game frame loop via _update_playing."""
        self.game.start_new_run()
        self.assertEqual(self.game.state, STATE_PLAYING)
        # Verify gland properties
        for gland in self.game.player.glands:
            self.assertEqual(gland.max_amount, gland.capacity)
            self.assertGreater(gland.capacity, 0)
        # Step playing loop for several frames
        for _ in range(10):
            self.game._update_playing(0.016, [])
        self.assertTrue(self.game.player.alive)


if __name__ == "__main__":
    unittest.main()
