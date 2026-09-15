"""Settings and Configuration Menu UI for Py-Noita.

Interactive, bio-horror styled settings interface supporting:
- Full keyboard and mouse remapping with live key capture.
- Gamepad calibration (deadzones, stick sensitivity, inverted Y, button mappings).
- Graphics preferences (window mode, resolution, v-sync, screen shake, particle density).
- Multi-track audio mixer (master, music, SFX, ambient volumes with instant live testing).
"""

import math
from typing import Any, List, Optional, Tuple
import pygame

from py_noita.config import (
    COLOR_ACID_GLOW,
    COLOR_BG_DARK,
    COLOR_BLOOD_GLOW,
    COLOR_NERVE_GLOW,
    COLOR_PLAYER_GLOW,
    RES_FULL_HD,
    RES_WINDOWED_1080,
)
from py_noita.system.settings_manager import SettingsManager


TAB_CONTROLS = 0
TAB_GAMEPAD = 1
TAB_GRAPHICS = 2
TAB_AUDIO = 3


class SettingsMenu:
    """Full-screen / overlay settings configuration menu."""

    def __init__(self, settings_manager: SettingsManager):
        self.settings = settings_manager
        self.active_tab: int = TAB_CONTROLS
        self.selected_index: int = 0
        self.scroll_offset: int = 0

        self.rebind_action_key: Optional[str] = None
        self.status_message: str = ""
        self.status_timer: float = 0.0

        # Fonts
        self.title_font = pygame.font.SysFont("Arial", 16, bold=True)
        self.tab_font = pygame.font.SysFont("Arial", 13, bold=True)
        self.label_font = pygame.font.SysFont("Arial", 11, bold=True)
        self.val_font = pygame.font.SysFont("Arial", 11)
        self.help_font = pygame.font.SysFont("Arial", 10)

        # Tab headers
        self.tabs = [
            ("1. TASTENBELEGUNG", TAB_CONTROLS),
            ("2. GAMEPAD", TAB_GAMEPAD),
            ("3. GRAFIK", TAB_GRAPHICS),
            ("4. AUDIO", TAB_AUDIO),
        ]

        # Action list for controls tab
        self.action_keys = list(self.settings.keybindings.keys())

    def update(self, dt: float) -> None:
        """Tick visual status message countdown."""
        if self.status_timer > 0.0:
            self.status_timer -= dt
            if self.status_timer <= 0.0:
                self.status_message = ""

    def handle_event(self, event: pygame.event.Event, audio_manager: Optional[Any] = None) -> bool:
        """Process user input in settings menu. Returns True if menu should close."""
        # 1. If waiting to rebind an action
        if self.rebind_action_key is not None:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.rebind_action_key = None
                    self.status_message = "Neubelegung abgebrochen."
                    self.status_timer = 2.0
                    return False
                self.settings.rebind_action(self.rebind_action_key, event.key)
                action_name = self.settings.get_action_display_name(self.rebind_action_key)
                self.status_message = f"{action_name} neu belegt: {pygame.key.name(event.key).upper()}"
                self.status_timer = 3.0
                self.rebind_action_key = None
                return False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                btn_name = f"MOUSE_{event.button}"
                self.settings.rebind_action(self.rebind_action_key, btn_name)
                action_name = self.settings.get_action_display_name(self.rebind_action_key)
                self.status_message = f"{action_name} neu belegt: {btn_name}"
                self.status_timer = 3.0
                self.rebind_action_key = None
                return False
            return False

        # 2. General Navigation
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.settings.save()
                return True  # Exit settings

            # Tab switching (1-4 or TAB)
            if event.key == pygame.K_1:
                self.active_tab = TAB_CONTROLS
                self.selected_index = 0
                self.scroll_offset = 0
            elif event.key == pygame.K_2:
                self.active_tab = TAB_GAMEPAD
                self.selected_index = 0
            elif event.key == pygame.K_3:
                self.active_tab = TAB_GRAPHICS
                self.selected_index = 0
            elif event.key == pygame.K_4:
                self.active_tab = TAB_AUDIO
                self.selected_index = 0
            elif event.key == pygame.K_TAB:
                self.active_tab = (self.active_tab + 1) % len(self.tabs)
                self.selected_index = 0
                self.scroll_offset = 0

            # Reset defaults
            elif event.key == pygame.K_r:
                self.settings.reset_to_defaults()
                if audio_manager:
                    audio_manager.apply_settings(self.settings)
                self.status_message = "Alle Einstellungen auf Standard zurückgesetzt."
                self.status_timer = 3.0

            # Vertical navigation
            elif event.key in (pygame.K_UP, pygame.K_w):
                self._nav_up()
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._nav_down()

            # Horizontal adjustment (Sliders, Toggles)
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self._adjust_value(-1, audio_manager)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self._adjust_value(1, audio_manager)

            # Enter / Space to activate
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate_selected(audio_manager)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:  # Wheel up
                self._nav_up()
            elif event.button == 5:  # Wheel down
                self._nav_down()

        return False

    def _nav_up(self) -> None:
        if self.selected_index > 0:
            self.selected_index -= 1
            if self.active_tab == TAB_CONTROLS and self.selected_index < self.scroll_offset:
                self.scroll_offset = self.selected_index

    def _nav_down(self) -> None:
        max_idx = self._get_item_count() - 1
        if self.selected_index < max_idx:
            self.selected_index += 1
            if self.active_tab == TAB_CONTROLS and self.selected_index >= self.scroll_offset + 9:
                self.scroll_offset = self.selected_index - 8

    def _get_item_count(self) -> int:
        if self.active_tab == TAB_CONTROLS:
            return len(self.action_keys)
        elif self.active_tab == TAB_GAMEPAD:
            return 7  # Deadzone, Sensitivity, Invert Y, 4 Buttons
        elif self.active_tab == TAB_GRAPHICS:
            return 5  # Mode, Resolution, VSync, Screen Shake, Particle Density
        elif self.active_tab == TAB_AUDIO:
            return 5  # Master, Music, SFX, Ambient, Test Sound
        return 0

    def _adjust_value(self, delta: int, audio_manager: Optional[Any] = None) -> None:
        """Adjust numerical sliders or switch options."""
        if self.active_tab == TAB_GAMEPAD:
            if self.selected_index == 0:  # Deadzone
                self.settings.gamepad_deadzone = round(
                    max(0.02, min(0.45, self.settings.gamepad_deadzone + delta * 0.02)), 2
                )
            elif self.selected_index == 1:  # Sensitivity
                self.settings.gamepad_sensitivity = round(
                    max(0.4, min(3.0, self.settings.gamepad_sensitivity + delta * 0.1)), 1
                )
            elif self.selected_index == 2:  # Invert Y
                self.settings.gamepad_invert_y = not self.settings.gamepad_invert_y
            self.settings.save()

        elif self.active_tab == TAB_GRAPHICS:
            if self.selected_index == 0:  # Window Mode
                modes = ["WINDOWED", "BORDERLESS", "FULLSCREEN"]
                cur_idx = modes.index(self.settings.window_mode) if self.settings.window_mode in modes else 0
                self.settings.window_mode = modes[(cur_idx + delta) % len(modes)]
            elif self.selected_index == 1:  # Resolution
                res_list = [[1280, 720], [1920, 1080], [2560, 1080]]
                cur_idx = 0
                for i, r in enumerate(res_list):
                    if self.settings.resolution == r:
                        cur_idx = i
                self.settings.resolution = res_list[(cur_idx + delta) % len(res_list)]
            elif self.selected_index == 2:  # VSync
                self.settings.vsync = not self.settings.vsync
            elif self.selected_index == 3:  # Screen Shake
                self.settings.screen_shake = round(
                    max(0.0, min(1.0, self.settings.screen_shake + delta * 0.1)), 1
                )
            elif self.selected_index == 4:  # Particle Density
                self.settings.particle_density = round(
                    max(0.25, min(1.0, self.settings.particle_density + delta * 0.15)), 2
                )
            self.settings.save()

        elif self.active_tab == TAB_AUDIO:
            if self.selected_index == 0:  # Master
                self.settings.master_volume = round(
                    max(0.0, min(1.0, self.settings.master_volume + delta * 0.05)), 2
                )
            elif self.selected_index == 1:  # Music
                self.settings.music_volume = round(
                    max(0.0, min(1.0, self.settings.music_volume + delta * 0.05)), 2
                )
            elif self.selected_index == 2:  # SFX
                self.settings.sfx_volume = round(
                    max(0.0, min(1.0, self.settings.sfx_volume + delta * 0.05)), 2
                )
            elif self.selected_index == 3:  # Ambient
                self.settings.ambient_volume = round(
                    max(0.0, min(1.0, self.settings.ambient_volume + delta * 0.05)), 2
                )
            self.settings.save()
            if audio_manager:
                audio_manager.apply_settings(self.settings)

    def _activate_selected(self, audio_manager: Optional[Any] = None) -> None:
        """Activate selected item (Enter / Click)."""
        if self.active_tab == TAB_CONTROLS:
            if 0 <= self.selected_index < len(self.action_keys):
                action = self.action_keys[self.selected_index]
                self.rebind_action_key = action
                self.status_message = "DRÜCKE EINE TASTE ODER MAUSTASTE (ESC = ABBRUCH)..."
                self.status_timer = 999.0

        elif self.active_tab == TAB_GAMEPAD:
            if self.selected_index == 2:
                self.settings.gamepad_invert_y = not self.settings.gamepad_invert_y
                self.settings.save()

        elif self.active_tab == TAB_GRAPHICS:
            if self.selected_index in (0, 1, 2):
                self._adjust_value(1)

        elif self.active_tab == TAB_AUDIO:
            if self.selected_index == 4 and audio_manager:
                # Play test SFX sound
                audio_manager.play("shot_acid", volume=0.9, throttle=0.0)
                self.status_message = "Audio-Test: Organ-Schuss abgespielt."
                self.status_timer = 2.0

    def draw(self, surface: pygame.Surface) -> None:
        """Render the complete settings UI."""
        sw, sh = surface.get_size()

        # 1. Dark semi-transparent biological overlay
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((10, 8, 14, 235))
        surface.blit(overlay, (0, 0))

        # 2. Main Window Box
        box_w = min(560, sw - 40)
        box_h = min(320, sh - 30)
        bx = (sw - box_w) // 2
        by = (sh - box_h) // 2

        # Outer border & organic frame
        pygame.draw.rect(surface, (25, 20, 32), (bx, by, box_w, box_h))
        pygame.draw.rect(surface, COLOR_NERVE_GLOW, (bx, by, box_w, box_h), 2)
        pygame.draw.rect(surface, (70, 20, 35), (bx + 3, by + 3, box_w - 6, box_h - 6), 1)

        # Title Header
        title_surf = self.title_font.render("BIO-SYNTHESE KONFIGURATION & SYSTEM", True, COLOR_PLAYER_GLOW)
        surface.blit(title_surf, (bx + (box_w - title_surf.get_width()) // 2, by + 10))

        # 3. Tab Buttons
        tab_y = by + 36
        tab_w = box_w // len(self.tabs)
        for i, (tab_title, tab_id) in enumerate(self.tabs):
            tx = bx + i * tab_w
            is_active = (self.active_tab == tab_id)
            bg_col = (50, 25, 45) if is_active else (20, 15, 25)
            text_col = COLOR_ACID_GLOW if is_active else (140, 130, 150)
            pygame.draw.rect(surface, bg_col, (tx + 2, tab_y, tab_w - 4, 22))
            if is_active:
                pygame.draw.rect(surface, COLOR_ACID_GLOW, (tx + 2, tab_y, tab_w - 4, 22), 1)

            t_surf = self.tab_font.render(tab_title, True, text_col)
            surface.blit(t_surf, (tx + (tab_w - t_surf.get_width()) // 2, tab_y + 3))

        # 4. Content Area
        content_y = tab_y + 30
        content_h = box_h - 100
        pygame.draw.rect(surface, (15, 12, 18), (bx + 10, content_y, box_w - 20, content_h))
        pygame.draw.rect(surface, (45, 35, 55), (bx + 10, content_y, box_w - 20, content_h), 1)

        if self.active_tab == TAB_CONTROLS:
            self._draw_controls_tab(surface, bx + 16, content_y + 8, box_w - 32, content_h - 16)
        elif self.active_tab == TAB_GAMEPAD:
            self._draw_gamepad_tab(surface, bx + 16, content_y + 8, box_w - 32, content_h - 16)
        elif self.active_tab == TAB_GRAPHICS:
            self._draw_graphics_tab(surface, bx + 16, content_y + 8, box_w - 32, content_h - 16)
        elif self.active_tab == TAB_AUDIO:
            self._draw_audio_tab(surface, bx + 16, content_y + 8, box_w - 32, content_h - 16)

        # 5. Status & Prompt Notice
        if self.rebind_action_key is not None:
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.006))
            prompt_col = (int(255 * pulse), int(220 * pulse), 40)
            p_surf = self.label_font.render(
                f"TASTE DRÜCKEN FÜR: {self.settings.get_action_display_name(self.rebind_action_key).upper()}",
                True,
                prompt_col,
            )
            surface.blit(p_surf, (bx + (box_w - p_surf.get_width()) // 2, by + box_h - 38))
        elif self.status_message:
            s_surf = self.label_font.render(self.status_message, True, COLOR_ACID_GLOW)
            surface.blit(s_surf, (bx + (box_w - s_surf.get_width()) // 2, by + box_h - 38))

        # 6. Bottom Navigation Hint
        help_txt = "[TAB] Tab wechseln  |  [W/S] Auswählen  |  [A/D/ENTER] Ändern  |  [R] Standard  |  [ESC] Speichern & Zurück"
        h_surf = self.help_font.render(help_txt, True, (160, 150, 170))
        surface.blit(h_surf, (bx + (box_w - h_surf.get_width()) // 2, by + box_h - 20))

    def _draw_controls_tab(self, surface: pygame.Surface, x: int, y: int, w: int, h: int) -> None:
        visible_rows = 9
        row_h = 17

        for i in range(visible_rows):
            idx = self.scroll_offset + i
            if idx >= len(self.action_keys):
                break

            action = self.action_keys[idx]
            is_selected = (idx == self.selected_index)
            ry = y + i * row_h

            if is_selected:
                pygame.draw.rect(surface, (60, 30, 50), (x, ry, w, row_h - 2))
                pygame.draw.rect(surface, COLOR_ACID_GLOW, (x, ry, w, row_h - 2), 1)

            label_col = COLOR_ACID_GLOW if is_selected else (210, 200, 220)
            val_col = (255, 240, 160) if is_selected else (170, 180, 200)

            name_surf = self.label_font.render(self.settings.get_action_display_name(action), True, label_col)
            binding_str = self.settings.get_binding_display_str(action)
            val_surf = self.val_font.render(binding_str, True, val_col)

            surface.blit(name_surf, (x + 8, ry + 1))
            surface.blit(val_surf, (x + w - val_surf.get_width() - 8, ry + 1))

        # Scroll indicators
        if self.scroll_offset > 0:
            up_surf = self.help_font.render("^ WEITERE OBEN ^", True, (120, 110, 130))
            surface.blit(up_surf, (x + (w - up_surf.get_width()) // 2, y - 6))
        if self.scroll_offset + visible_rows < len(self.action_keys):
            down_surf = self.help_font.render("v WEITERE UNTEN v", True, (120, 110, 130))
            surface.blit(down_surf, (x + (w - down_surf.get_width()) // 2, y + h - 10))

    def _draw_gamepad_tab(self, surface: pygame.Surface, x: int, y: int, w: int, h: int) -> None:
        items = [
            ("Stick-Deadzone (Totzone)", f"{int(self.settings.gamepad_deadzone * 100)}%", self.settings.gamepad_deadzone / 0.45),
            ("Stick-Empfindlichkeit", f"{int(self.settings.gamepad_sensitivity * 100)}%", (self.settings.gamepad_sensitivity - 0.4) / 2.6),
            ("Y-Achse Invertieren (Flug)", "AKTIVIERT" if self.settings.gamepad_invert_y else "DEAKTIVIERT", None),
            ("Sprung / Schweben", f"Gamepad Taste {self.settings.gamepad_btn_jump} (A)", None),
            ("Inventar / Bio-Kodex", f"Gamepad Taste {self.settings.gamepad_btn_inventory} (B)", None),
            ("Flüssigkeit Aufsaugen", f"Gamepad Taste {self.settings.gamepad_btn_suck} (X)", None),
            ("Interaktion / Portal", f"Gamepad Taste {self.settings.gamepad_btn_interact} (Y)", None),
        ]

        row_h = 21
        for idx, (label, val_str, slider_frac) in enumerate(items):
            is_selected = (idx == self.selected_index)
            ry = y + idx * row_h

            if is_selected:
                pygame.draw.rect(surface, (60, 30, 50), (x, ry, w, row_h - 2))
                pygame.draw.rect(surface, COLOR_ACID_GLOW, (x, ry, w, row_h - 2), 1)

            label_col = COLOR_ACID_GLOW if is_selected else (210, 200, 220)
            val_col = (255, 240, 160) if is_selected else (170, 180, 200)

            name_surf = self.label_font.render(label, True, label_col)
            surface.blit(name_surf, (x + 8, ry + 2))

            if slider_frac is not None:
                # Render mini slider bar
                bar_w = 90
                bar_h = 6
                bx = x + w - 170
                by = ry + 6
                pygame.draw.rect(surface, (40, 30, 45), (bx, by, bar_w, bar_h))
                pygame.draw.rect(surface, (80, 70, 90), (bx, by, bar_w, bar_h), 1)
                fw = int(bar_w * max(0.0, min(1.0, slider_frac)))
                fill_col = COLOR_ACID_GLOW if is_selected else (160, 60, 180)
                pygame.draw.rect(surface, fill_col, (bx, by, fw, bar_h))

            val_surf = self.val_font.render(val_str, True, val_col)
            surface.blit(val_surf, (x + w - val_surf.get_width() - 8, ry + 2))

    def _draw_graphics_tab(self, surface: pygame.Surface, x: int, y: int, w: int, h: int) -> None:
        items = [
            ("Fenstermodus", self.settings.window_mode, None),
            ("Basis-Auflösung", f"{self.settings.resolution[0]} x {self.settings.resolution[1]}", None),
            ("Vertikale Synchronisation (V-Sync)", "EIN" if self.settings.vsync else "AUS", None),
            ("Bildschirm-Wackeln (Screen Shake)", f"{int(self.settings.screen_shake * 100)}%", self.settings.screen_shake),
            ("Partikeldichte (Simulation)", f"{int(self.settings.particle_density * 100)}%", (self.settings.particle_density - 0.25) / 0.75),
        ]

        row_h = 24
        for idx, (label, val_str, slider_frac) in enumerate(items):
            is_selected = (idx == self.selected_index)
            ry = y + idx * row_h

            if is_selected:
                pygame.draw.rect(surface, (60, 30, 50), (x, ry, w, row_h - 2))
                pygame.draw.rect(surface, COLOR_ACID_GLOW, (x, ry, w, row_h - 2), 1)

            label_col = COLOR_ACID_GLOW if is_selected else (210, 200, 220)
            val_col = (255, 240, 160) if is_selected else (170, 180, 200)

            name_surf = self.label_font.render(label, True, label_col)
            surface.blit(name_surf, (x + 8, ry + 3))

            if slider_frac is not None:
                bar_w = 100
                bar_h = 7
                bx = x + w - 180
                by = ry + 7
                pygame.draw.rect(surface, (40, 30, 45), (bx, by, bar_w, bar_h))
                pygame.draw.rect(surface, (80, 70, 90), (bx, by, bar_w, bar_h), 1)
                fw = int(bar_w * max(0.0, min(1.0, slider_frac)))
                fill_col = COLOR_ACID_GLOW if is_selected else (200, 50, 100)
                pygame.draw.rect(surface, fill_col, (bx, by, fw, bar_h))

            val_surf = self.val_font.render(val_str, True, val_col)
            surface.blit(val_surf, (x + w - val_surf.get_width() - 8, ry + 3))

    def _draw_audio_tab(self, surface: pygame.Surface, x: int, y: int, w: int, h: int) -> None:
        items = [
            ("Master-Lautstärke", f"{int(self.settings.master_volume * 100)}%", self.settings.master_volume),
            ("Musik-Lautstärke (Adaptiver Soundtrack)", f"{int(self.settings.music_volume * 100)}%", self.settings.music_volume),
            ("Soundeffekte (SFX-Arsenal)", f"{int(self.settings.sfx_volume * 100)}%", self.settings.sfx_volume),
            ("Umgebungs-Akustik & Hall", f"{int(self.settings.ambient_volume * 100)}%", self.settings.ambient_volume),
            ("Audio-Testton abspielen", "[ENTER / KLICK ZUM TESTEN]", None),
        ]

        row_h = 24
        for idx, (label, val_str, slider_frac) in enumerate(items):
            is_selected = (idx == self.selected_index)
            ry = y + idx * row_h

            if is_selected:
                pygame.draw.rect(surface, (60, 30, 50), (x, ry, w, row_h - 2))
                pygame.draw.rect(surface, COLOR_ACID_GLOW, (x, ry, w, row_h - 2), 1)

            label_col = COLOR_ACID_GLOW if is_selected else (210, 200, 220)
            val_col = (255, 240, 160) if is_selected else (170, 180, 200)

            name_surf = self.label_font.render(label, True, label_col)
            surface.blit(name_surf, (x + 8, ry + 3))

            if slider_frac is not None:
                bar_w = 110
                bar_h = 7
                bx = x + w - 190
                by = ry + 7
                pygame.draw.rect(surface, (40, 30, 45), (bx, by, bar_w, bar_h))
                pygame.draw.rect(surface, (80, 70, 90), (bx, by, bar_w, bar_h), 1)
                fw = int(bar_w * max(0.0, min(1.0, slider_frac)))
                fill_col = COLOR_ACID_GLOW if is_selected else COLOR_NERVE_GLOW
                pygame.draw.rect(surface, fill_col, (bx, by, fw, bar_h))

            val_surf = self.val_font.render(val_str, True, val_col)
            surface.blit(val_surf, (x + w - val_surf.get_width() - 8, ry + 3))
