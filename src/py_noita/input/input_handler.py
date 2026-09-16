"""Input processing for keyboard, mouse, and twin-stick gamepad."""

import math
from typing import Optional, Tuple
import pygame


class InputState:
    """Consolidated input frame state."""
    def __init__(self):
        self.move_x: float = 0.0
        self.hover: bool = False
        self.fast_fall: bool = False

        self.aim_world_x: float = 0.0
        self.aim_world_y: float = 0.0
        self.aim_angle: float = 0.0
        self.sim_mouse_x: int = 0
        self.sim_mouse_y: int = 0
        self.mouse_in_bounds: bool = False

        self.fire_primary: bool = False       # Fire cannula
        self.fire_secondary: bool = False     # Spray liquid gland
        self.suck_liquid: bool = False        # Suck fluid

        self.select_cannula: Optional[int] = None   # 0 to 3
        self.select_gland: Optional[int] = None     # 0 to 3

        self.interact: bool = False
        self.toggle_inventory: bool = False
        self.pause: bool = False
        self.toggle_fullscreen: bool = False
        self.toggle_resolution: bool = False
        self.scroll_delta: int = 0


class InputHandler:
    """Manages keyboard, mouse, and gamepad joystick inputs with configurable bindings."""

    def __init__(self, settings: Optional[object] = None):
        self.settings = settings
        self.joystick: Optional[pygame.joystick.Joystick] = None
        self._init_joysticks()

    def _init_joysticks(self) -> None:
        """Initialize connected gamepads."""
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()

    def process_events(
        self,
        events,
        screen_rect: pygame.Rect,
        cam_x: int,
        cam_y: int,
        sim_view_w: int,
        sim_view_h: int,
        player_cx: float,
        player_cy: float,
        settings: Optional[object] = None,
    ) -> InputState:
        """Process Pygame event queue and polling to produce an InputState."""
        cfg = settings or self.settings
        state = InputState()

        # Keyboard polling
        keys = pygame.key.get_pressed()
        mouse_buttons = pygame.mouse.get_pressed()

        if cfg:
            if cfg.is_action_pressed("move_left", keys, mouse_buttons):
                state.move_x -= 1.0
            if cfg.is_action_pressed("move_right", keys, mouse_buttons):
                state.move_x += 1.0
            if cfg.is_action_pressed("hover", keys, mouse_buttons):
                state.hover = True
            if cfg.is_action_pressed("drop", keys, mouse_buttons):
                state.fast_fall = True
            if cfg.is_action_pressed("fire_cannula", keys, mouse_buttons):
                state.fire_primary = True
            if cfg.is_action_pressed("discharge_gland", keys, mouse_buttons):
                state.fire_secondary = True
            if cfg.is_action_pressed("suck_liquid", keys, mouse_buttons):
                state.suck_liquid = True

            for idx, c_action in enumerate(("cannula_1", "cannula_2", "cannula_3", "cannula_4")):
                if cfg.is_action_pressed(c_action, keys, mouse_buttons):
                    state.select_cannula = idx

            for idx, g_action in enumerate(("gland_1", "gland_2", "gland_3", "gland_4")):
                if cfg.is_action_pressed(g_action, keys, mouse_buttons):
                    state.select_gland = idx
        else:
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                state.move_x -= 1.0
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                state.move_x += 1.0
            if keys[pygame.K_w] or keys[pygame.K_SPACE] or keys[pygame.K_UP]:
                state.hover = True
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                state.fast_fall = True
            if mouse_buttons[0]:
                state.fire_primary = True
            if len(mouse_buttons) > 2 and mouse_buttons[2]:
                state.fire_secondary = True
            if keys[pygame.K_f]:
                state.suck_liquid = True
            if keys[pygame.K_1]:
                state.select_cannula = 0
            elif keys[pygame.K_2]:
                state.select_cannula = 1
            elif keys[pygame.K_3]:
                state.select_cannula = 2
            elif keys[pygame.K_4]:
                state.select_cannula = 3
            if keys[pygame.K_5]:
                state.select_gland = 0
            elif keys[pygame.K_6]:
                state.select_gland = 1
            elif keys[pygame.K_7]:
                state.select_gland = 2
            elif keys[pygame.K_8]:
                state.select_gland = 3

        # Mouse position & World coordinates
        mouse_px, mouse_py = pygame.mouse.get_pos()

        # Map window mouse pixel to simulation world coordinates through dest_rect
        if screen_rect.width > 0 and screen_rect.height > 0:
            rel_x = (mouse_px - screen_rect.left) / screen_rect.width
            rel_y = (mouse_py - screen_rect.top) / screen_rect.height
            sim_x = rel_x * sim_view_w
            sim_y = rel_y * sim_view_h
            state.aim_world_x = cam_x + sim_x
            state.aim_world_y = cam_y + sim_y
            state.aim_angle = math.atan2(state.aim_world_y - player_cy, state.aim_world_x - player_cx)
            state.sim_mouse_x = int(sim_x)
            state.sim_mouse_y = int(sim_y)
            state.mouse_in_bounds = (0.0 <= rel_x <= 1.0 and 0.0 <= rel_y <= 1.0)

        # Gamepad Twin-Stick handling
        if self.joystick is not None:
            deadzone = getattr(cfg, "gamepad_deadzone", 0.15) if cfg else 0.15
            sensitivity = getattr(cfg, "gamepad_sensitivity", 1.0) if cfg else 1.0
            invert_y = getattr(cfg, "gamepad_invert_y", False) if cfg else False
            btn_jump = getattr(cfg, "gamepad_btn_jump", 0) if cfg else 0
            btn_inv = getattr(cfg, "gamepad_btn_inventory", 1) if cfg else 1
            btn_suck = getattr(cfg, "gamepad_btn_suck", 2) if cfg else 2
            btn_inter = getattr(cfg, "gamepad_btn_interact", 3) if cfg else 3

            # Left stick: Movement
            ax_lx = self.joystick.get_axis(0)
            if abs(ax_lx) > deadzone:
                # Normalize and scale
                norm = (abs(ax_lx) - deadzone) / (1.0 - deadzone)
                state.move_x = math.copysign(min(1.0, norm * sensitivity), ax_lx)

            # Hover on Left Stick Up or Jump Button (e.g. Button A)
            ax_ly = self.joystick.get_axis(1)
            jump_pressed = False
            if btn_jump < self.joystick.get_numbuttons():
                jump_pressed = self.joystick.get_button(btn_jump)

            if ax_ly < -0.4 or jump_pressed:
                state.hover = True

            # Right stick: Aiming
            num_axes = self.joystick.get_num_axes()
            rx = self.joystick.get_axis(2) if num_axes > 2 else 0.0
            ry = self.joystick.get_axis(3) if num_axes > 3 else 0.0
            if invert_y:
                ry = -ry

            mag = math.hypot(rx, ry)
            if mag > deadzone:
                state.aim_angle = math.atan2(ry, rx)
                reach = 80.0 * sensitivity
                state.aim_world_x = player_cx + math.cos(state.aim_angle) * reach
                state.aim_world_y = player_cy + math.sin(state.aim_angle) * reach
                state.sim_mouse_x = int(round(state.aim_world_x - cam_x))
                state.sim_mouse_y = int(round(state.aim_world_y - cam_y))
                state.mouse_in_bounds = (0 <= state.sim_mouse_x < sim_view_w and 0 <= state.sim_mouse_y < sim_view_h)

            # Triggers (Right Trigger = Fire, Left Trigger = Spray)
            for axis_idx in range(4, min(6, num_axes)):
                val = self.joystick.get_axis(axis_idx)
                if val > 0.3:
                    if axis_idx % 2 == 1:
                        state.fire_primary = True
                    else:
                        state.fire_secondary = True

        # Process single-shot key events
        for event in events:
            if cfg:
                if cfg.is_action_event("interact", event):
                    state.interact = True
                elif cfg.is_action_event("inventory", event):
                    state.toggle_inventory = True
                elif cfg.is_action_event("pause", event):
                    state.pause = True
            else:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_e:
                        state.interact = True
                    elif event.key in (pygame.K_TAB, pygame.K_i):
                        state.toggle_inventory = True
                    elif event.key == pygame.K_ESCAPE:
                        state.pause = True

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    state.toggle_fullscreen = True
                elif event.key == pygame.K_F1:
                    state.toggle_resolution = True
            elif event.type == pygame.MOUSEWHEEL:
                state.scroll_delta += event.y
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4:  # Wheel up
                    state.scroll_delta += 1
                elif event.button == 5:  # Wheel down
                    state.scroll_delta -= 1
            elif event.type == pygame.JOYBUTTONDOWN:
                if cfg:
                    if event.button == getattr(cfg, "gamepad_btn_inventory", 1):
                        state.toggle_inventory = True
                    elif event.button == getattr(cfg, "gamepad_btn_suck", 2):
                        state.suck_liquid = True
                    elif event.button == getattr(cfg, "gamepad_btn_interact", 3):
                        state.interact = True
                else:
                    if event.button == 1:
                        state.toggle_inventory = True
                    elif event.button == 2:
                        state.suck_liquid = True
                    elif event.button == 3:
                        state.interact = True

        return state
