"""Unit tests for SettingsManager, Key Remapping, Gamepad Calibration, and SettingsMenu."""

from pathlib import Path
import shutil
import tempfile
import unittest
import pygame

from py_noita.audio.audio_manager import AudioManager
from py_noita.input.input_handler import InputHandler, InputState
from py_noita.rendering.camera import Camera
from py_noita.rendering.particles import ParticleSystem
from py_noita.system.settings_manager import SettingsManager
from py_noita.ui.settings_menu import (
    SettingsMenu,
    TAB_AUDIO,
    TAB_CONTROLS,
    TAB_GAMEPAD,
    TAB_GRAPHICS,
)


class TestSettingsManager(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.filepath = Path(self.temp_dir) / "settings.json"
        self.settings = SettingsManager(filepath=self.filepath)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_default_values(self):
        self.assertEqual(self.settings.window_mode, "WINDOWED")
        self.assertEqual(self.settings.resolution, [1280, 720])
        self.assertTrue(self.settings.vsync)
        self.assertEqual(self.settings.screen_shake, 1.0)
        self.assertEqual(self.settings.particle_density, 1.0)
        self.assertEqual(self.settings.master_volume, 0.8)
        self.assertEqual(self.settings.music_volume, 0.7)
        self.assertEqual(self.settings.sfx_volume, 0.8)
        self.assertEqual(self.settings.ambient_volume, 0.7)
        self.assertEqual(self.settings.gamepad_deadzone, 0.15)
        self.assertEqual(self.settings.gamepad_sensitivity, 1.0)
        self.assertFalse(self.settings.gamepad_invert_y)

    def test_rebind_and_serialization(self):
        # Rebind move_left to K_q
        self.settings.rebind_action("move_left", pygame.K_q)
        self.assertEqual(self.settings.keybindings["move_left"], [pygame.K_q])
        self.assertIn("Q", self.settings.get_binding_display_str("move_left"))

        # Rebind fire_cannula to MOUSE_3
        self.settings.rebind_action("fire_cannula", "MOUSE_3")
        self.assertEqual(self.settings.keybindings["fire_cannula"], ["MOUSE_3"])
        self.assertIn("Maus Rechts", self.settings.get_binding_display_str("fire_cannula"))

        # Modify audio & graphics
        self.settings.master_volume = 0.5
        self.settings.screen_shake = 0.4
        self.settings.gamepad_deadzone = 0.22
        self.settings.gamepad_invert_y = True
        self.settings.save()

        # Reload in a new manager
        loaded = SettingsManager(filepath=self.filepath)
        self.assertEqual(loaded.keybindings["move_left"], [pygame.K_q])
        self.assertEqual(loaded.keybindings["fire_cannula"], ["MOUSE_3"])
        self.assertAlmostEqual(loaded.master_volume, 0.5, places=2)
        self.assertAlmostEqual(loaded.screen_shake, 0.4, places=2)
        self.assertAlmostEqual(loaded.gamepad_deadzone, 0.22, places=2)
        self.assertTrue(loaded.gamepad_invert_y)

    def test_reset_to_defaults(self):
        self.settings.rebind_action("move_left", pygame.K_j)
        self.settings.master_volume = 0.1
        self.settings.reset_to_defaults()

        self.assertIn(pygame.K_a, self.settings.keybindings["move_left"])
        self.assertAlmostEqual(self.settings.master_volume, 0.8, places=2)

    def test_input_handler_integration(self):
        handler = InputHandler(settings=self.settings)

        # Mock keypresses
        keys = [False] * 512
        # Press K_a (default move_left)
        keys[pygame.K_a] = True
        mouse = (False, False, False)

        self.assertTrue(self.settings.is_action_pressed("move_left", keys, mouse))
        self.assertFalse(self.settings.is_action_pressed("move_right", keys, mouse))

        # Rebind to K_z
        self.settings.rebind_action("move_left", pygame.K_z)
        self.assertFalse(self.settings.is_action_pressed("move_left", keys, mouse))
        keys[pygame.K_z] = True
        self.assertTrue(self.settings.is_action_pressed("move_left", keys, mouse))

    def test_audio_and_rendering_integration(self):
        audio = AudioManager()
        self.settings.master_volume = 0.6
        self.settings.music_volume = 0.5
        self.settings.sfx_volume = 0.9
        self.settings.ambient_volume = 0.4
        audio.apply_settings(self.settings)

        self.assertAlmostEqual(audio.master_volume, 0.6, places=2)
        self.assertAlmostEqual(audio.music_volume, 0.5, places=2)
        self.assertAlmostEqual(audio.sfx_volume, 0.9, places=2)
        self.assertAlmostEqual(audio.ambient_volume, 0.4, places=2)
        if hasattr(audio, "music") and audio.music:
            self.assertAlmostEqual(audio.music.master_music_volume, 0.3, places=2)

        # Camera shake scale
        camera = Camera(480, 270)
        camera.shake_scale = self.settings.screen_shake
        self.assertAlmostEqual(camera.shake_scale, 1.0, places=2)

        # Particle density
        particles = ParticleSystem()
        particles.density = self.settings.particle_density
        self.assertAlmostEqual(particles.density, 1.0, places=2)

    def test_settings_menu_navigation(self):
        menu = SettingsMenu(self.settings)
        self.assertEqual(menu.active_tab, TAB_CONTROLS)

        # Switch to tab 2 (Gamepad)
        event_tab2 = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2)
        menu.handle_event(event_tab2)
        self.assertEqual(menu.active_tab, TAB_GAMEPAD)

        # Switch to tab 3 (Graphics)
        event_tab3 = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_3)
        menu.handle_event(event_tab3)
        self.assertEqual(menu.active_tab, TAB_GRAPHICS)

        # Adjust window mode
        cur_mode = self.settings.window_mode
        event_right = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
        menu.handle_event(event_right)
        self.assertNotEqual(self.settings.window_mode, cur_mode)

        # Switch to tab 4 (Audio)
        event_tab4 = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_4)
        menu.handle_event(event_tab4)
        self.assertEqual(menu.active_tab, TAB_AUDIO)

        # Adjust master volume slider
        orig_vol = self.settings.master_volume
        event_left = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT)
        menu.handle_event(event_left)
        self.assertAlmostEqual(self.settings.master_volume, orig_vol - 0.05, places=2)

        # Test Rebind flow
        menu.active_tab = TAB_CONTROLS
        menu.selected_index = 0  # move_left
        event_enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        menu.handle_event(event_enter)
        self.assertEqual(menu.rebind_action_key, "move_left")

        # Press 'X' key to bind
        event_x = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_x)
        menu.handle_event(event_x)
        self.assertIsNone(menu.rebind_action_key)
        self.assertEqual(self.settings.keybindings["move_left"], [pygame.K_x])

        # Test ESC to exit menu
        event_esc = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        exit_menu = menu.handle_event(event_esc)
        self.assertTrue(exit_menu)


if __name__ == "__main__":
    unittest.main()
