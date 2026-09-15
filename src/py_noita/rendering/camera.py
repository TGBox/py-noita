"""Smooth follow camera with look-ahead, deadzone, and screen shake."""

import math
from typing import Tuple
import numpy as np

from py_noita.config import WORLD_HEIGHT, WORLD_WIDTH


class Camera:
    """Camera that follows target with smooth interpolation and screen shake."""

    def __init__(self, view_width: int, view_height: int):
        self.view_width = view_width
        self.view_height = view_height
        self.x: float = 0.0
        self.y: float = 0.0
        self.target_x: float = 0.0
        self.target_y: float = 0.0

        # Screen shake trauma (0.0 to 1.0)
        self.trauma: float = 0.0
        self.shake_decay: float = 0.04
        self.max_shake_offset: float = 8.0
        self.shake_scale: float = 1.0

        # Look-ahead weight towards mouse aim
        self.look_ahead_weight: float = 0.25

    def set_viewport_size(self, width: int, height: int) -> None:
        """Update viewport dimensions (e.g. when switching 16:9 vs 21:9)."""
        self.view_width = width
        self.view_height = height

    def center_on(self, focus_x: float, focus_y: float) -> None:
        """Instantly snap camera center onto world coordinates without lerping."""
        dest_x = focus_x - self.view_width / 2.0
        dest_y = focus_y - self.view_height / 2.0
        self.x = max(0.0, min(float(WORLD_WIDTH - self.view_width), dest_x))
        self.y = max(0.0, min(float(WORLD_HEIGHT - self.view_height), dest_y))

    def add_shake(self, amount: float) -> None:
        """Add trauma for screen shake, clamped to 1.0."""
        self.trauma = min(1.0, self.trauma + amount)

    def update(
        self,
        focus_x: float,
        focus_y: float,
        aim_x: float = 0.0,
        aim_y: float = 0.0,
        lerp_speed: float = 0.12,
    ) -> None:
        """Update camera center with look-ahead towards aim point."""
        # Calculate target center including look-ahead
        desired_center_x = focus_x + (aim_x - focus_x) * self.look_ahead_weight
        desired_center_y = focus_y + (aim_y - focus_y) * self.look_ahead_weight

        # Top-left corner
        dest_x = desired_center_x - self.view_width / 2.0
        dest_y = desired_center_y - self.view_height / 2.0

        # Clamp to world boundaries
        dest_x = max(0.0, min(float(WORLD_WIDTH - self.view_width), dest_x))
        dest_y = max(0.0, min(float(WORLD_HEIGHT - self.view_height), dest_y))

        # Smooth interpolation
        self.x += (dest_x - self.x) * lerp_speed
        self.y += (dest_y - self.y) * lerp_speed

        # Decay screen shake trauma
        if self.trauma > 0.0:
            self.trauma = max(0.0, self.trauma - self.shake_decay)

    def get_offset(self) -> Tuple[int, int]:
        """Get integer pixel offset including current screen shake."""
        shake_x = 0.0
        shake_y = 0.0
        if self.trauma > 0.0:
            shake_intensity = self.trauma * self.trauma
            angle = np.random.uniform(0.0, 2.0 * math.pi)
            dist = shake_intensity * self.max_shake_offset * self.shake_scale
            shake_x = math.cos(angle) * dist
            shake_y = math.sin(angle) * dist

        final_x = int(round(self.x + shake_x))
        final_y = int(round(self.y + shake_y))

        # Ensure we stay within world bounds even with shake
        final_x = max(0, min(WORLD_WIDTH - self.view_width, final_x))
        final_y = max(0, min(WORLD_HEIGHT - self.view_height, final_y))

        return final_x, final_y

    def world_to_screen(self, wx: float, wy: float) -> Tuple[int, int]:
        """Convert world coordinates to viewport screen pixel coordinates."""
        cam_x, cam_y = self.get_offset()
        return int(round(wx - cam_x)), int(round(wy - cam_y))

    def screen_to_world(self, sx: float, sy: float) -> Tuple[float, float]:
        """Convert viewport screen pixel coordinates to world coordinates."""
        cam_x, cam_y = self.get_offset()
        return float(sx + cam_x), float(sy + cam_y)
