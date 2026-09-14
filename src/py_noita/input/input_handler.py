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


class InputHandler:
    """Manages keyboard, mouse, and gamepad joystick inputs."""

    def __init__(self):
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
    ) -> InputState:
        """Process Pygame event queue and polling to produce an InputState."""
        state = InputState()

        # Keyboard polling
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            state.move_x -= 1.0
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            state.move_x += 1.0

        if keys[pygame.K_w] or keys[pygame.K_SPACE] or keys[pygame.K_UP]:
            state.hover = True
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            state.fast_fall = True

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

        # Mouse buttons
        mouse_buttons = pygame.mouse.get_pressed()
        if mouse_buttons[0]:  # Left Click
            state.fire_primary = True
        if mouse_buttons[2]:  # Right Click
            state.fire_secondary = True

        if keys[pygame.K_f]:  # Suck liquid
            state.suck_liquid = True

        # Number keys 1-4 (Cannulas) and 5-8 (Glands)
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

        # Gamepad Twin-Stick handling
        if self.joystick is not None:
            # Left stick: Movement
            ax_lx = self.joystick.get_axis(0)
            if abs(ax_lx) > 0.15:
                state.move_x = ax_lx

            # Hover on Left Stick Up or A-button (button 0)
            ax_ly = self.joystick.get_axis(1)
            if ax_ly < -0.4 or self.joystick.get_button(0):
                state.hover = True

            # Right stick: Aiming (axes 2 and 3 or 3 and 4 depending on driver)
            num_axes = self.joystick.get_num_axes()
            rx = self.joystick.get_axis(2) if num_axes > 2 else 0.0
            ry = self.joystick.get_axis(3) if num_axes > 3 else 0.0

            if abs(rx) > 0.25 or abs(ry) > 0.25:
                state.aim_angle = math.atan2(ry, rx)
                state.aim_world_x = player_cx + math.cos(state.aim_angle) * 80.0
                state.aim_world_y = player_cy + math.sin(state.aim_angle) * 80.0

            # Triggers (Right Trigger = Fire, Left Trigger = Spray)
            # Typically axis 4 or 5
            for axis_idx in range(4, min(6, num_axes)):
                val = self.joystick.get_axis(axis_idx)
                if val > 0.3:
                    if axis_idx % 2 == 1:
                        state.fire_primary = True
                    else:
                        state.fire_secondary = True

        # Process single-shot key events
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_e:
                    state.interact = True
                elif event.key in (pygame.K_TAB, pygame.K_i):
                    state.toggle_inventory = True
                elif event.key == pygame.K_ESCAPE:
                    state.pause = True
                elif event.key == pygame.K_F11:
                    state.toggle_fullscreen = True
                elif event.key == pygame.K_F1:
                    state.toggle_resolution = True
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button == 1:  # B button
                    state.toggle_inventory = True
                elif event.button == 2:  # X button
                    state.suck_liquid = True
                elif event.button == 3:  # Y button
                    state.interact = True

        return state
