"""Core rendering engine: Pixel grid blitting, dynamic scaling, and aspect management."""

from typing import Tuple
import pygame
import numpy as np
from numba import njit

from py_noita.config import (
    COLOR_BG_DARK,
    PIXEL_SCALE,
    RES_FULL_HD,
    RES_ULTRAWIDE,
    VIEWPORT_SIM_HEIGHT,
    VIEWPORT_SIM_WIDTH_16_9,
    VIEWPORT_SIM_WIDTH_21_9,
)
from py_noita.simulation.materials import LUT_COLORS, MAT_AIR, PROP_GLOW


@njit(fastmath=True)
def render_slice_to_surfarray(
    grid: np.ndarray,
    color_var: np.ndarray,
    cam_x: int,
    cam_y: int,
    out_surfarray: np.ndarray,
    lut_colors: np.ndarray,
    bg_r: int,
    bg_g: int,
    bg_b: int,
) -> None:
    """Fast Numba kernel that writes the visible world slice directly into
    out_surfarray (view_w, view_h, 3) for Pygame surfarray blit.
    """
    view_w = out_surfarray.shape[0]
    view_h = out_surfarray.shape[1]
    grid_h = grid.shape[0]
    grid_w = grid.shape[1]

    for sx in range(view_w):
        gx = cam_x + sx
        for sy in range(view_h):
            gy = cam_y + sy
            if 0 <= gx < grid_w and 0 <= gy < grid_h:
                mat = grid[gy, gx]
                if mat == MAT_AIR:
                    # Subtle visceral cavern background dither
                    dither = ((gx ^ gy) & 3) * 2
                    out_surfarray[sx, sy, 0] = bg_r + dither
                    out_surfarray[sx, sy, 1] = bg_g + dither
                    out_surfarray[sx, sy, 2] = bg_b + dither
                else:
                    base_r = lut_colors[mat, 0]
                    base_g = lut_colors[mat, 1]
                    base_b = lut_colors[mat, 2]

                    # Organic variation from color_var (0 to 3)
                    var = color_var[gy, gx]
                    offset = -6 if var == 0 else (-2 if var == 1 else (4 if var == 2 else 8))

                    r = max(0, min(255, base_r + offset))
                    g = max(0, min(255, base_g + offset))
                    b = max(0, min(255, base_b + offset))

                    out_surfarray[sx, sy, 0] = r
                    out_surfarray[sx, sy, 1] = g
                    out_surfarray[sx, sy, 2] = b
            else:
                out_surfarray[sx, sy, 0] = 30
                out_surfarray[sx, sy, 1] = 25
                out_surfarray[sx, sy, 2] = 35


class Renderer:
    """Manages internal simulation buffer and scales to target display."""

    def __init__(self, screen_res: Tuple[int, int] = RES_FULL_HD):
        self.screen_res = screen_res
        self.is_ultrawide = (screen_res[0] / screen_res[1]) > 2.0

        # Calculate simulation viewport dimensions
        self.view_w = VIEWPORT_SIM_WIDTH_21_9 if self.is_ultrawide else VIEWPORT_SIM_WIDTH_16_9
        self.view_h = VIEWPORT_SIM_HEIGHT

        # Internal low-res surfaces
        self.sim_surface = pygame.Surface((self.view_w, self.view_h))
        # NumPy buffer for pygame.surfarray (width, height, 3)
        self.surfarray_buffer = np.zeros((self.view_w, self.view_h, 3), dtype=np.uint8)

        # Dest rect for letterbox / scaling
        self.dest_rect = pygame.Rect(0, 0, screen_res[0], screen_res[1])
        self.update_dest_rect(screen_res)

    def set_resolution(self, screen_res: Tuple[int, int]) -> None:
        """Switch between 1920x1080 (16:9), 2560x1080 (21:9 Ultrawide), or custom."""
        self.screen_res = screen_res
        self.is_ultrawide = (screen_res[0] / screen_res[1]) > 2.0
        self.view_w = VIEWPORT_SIM_WIDTH_21_9 if self.is_ultrawide else VIEWPORT_SIM_WIDTH_16_9
        self.view_h = VIEWPORT_SIM_HEIGHT

        self.sim_surface = pygame.Surface((self.view_w, self.view_h))
        self.surfarray_buffer = np.zeros((self.view_w, self.view_h, 3), dtype=np.uint8)
        self.update_dest_rect(screen_res)

    def update_dest_rect(self, screen_res: Tuple[int, int]) -> None:
        """Calculate scaled destination rectangle preserving pixel aspect ratio."""
        target_w, target_h = screen_res
        aspect_sim = self.view_w / self.view_h
        aspect_screen = target_w / target_h

        if abs(aspect_sim - aspect_screen) < 0.05:
            # Exact match (e.g. 1920x1080 for 16:9, or 2560x1080 for 21:9)
            self.dest_rect = pygame.Rect(0, 0, target_w, target_h)
        elif aspect_screen > aspect_sim:
            # Pillarbox (black bars on sides)
            scaled_w = int(target_h * aspect_sim)
            offset_x = (target_w - scaled_w) // 2
            self.dest_rect = pygame.Rect(offset_x, 0, scaled_w, target_h)
        else:
            # Letterbox (black bars on top/bottom)
            scaled_h = int(target_w / aspect_sim)
            offset_y = (target_h - scaled_h) // 2
            self.dest_rect = pygame.Rect(0, offset_y, target_w, scaled_h)

    def render_grid(self, grid: np.ndarray, color_var: np.ndarray, cam_x: int, cam_y: int) -> None:
        """Blit simulation grid pixels to the internal sim_surface."""
        render_slice_to_surfarray(
            grid,
            color_var,
            cam_x,
            cam_y,
            self.surfarray_buffer,
            LUT_COLORS,
            COLOR_BG_DARK[0],
            COLOR_BG_DARK[1],
            COLOR_BG_DARK[2],
        )
        pygame.surfarray.blit_array(self.sim_surface, self.surfarray_buffer)

    def present(self, screen: pygame.Surface) -> None:
        """Scale internal simulation surface up to the display window."""
        if self.dest_rect.size == self.screen_res:
            pygame.transform.scale(self.sim_surface, self.screen_res, screen)
        else:
            screen.fill((0, 0, 0))  # Clear black bars
            scaled = pygame.transform.scale(self.sim_surface, (self.dest_rect.width, self.dest_rect.height))
            screen.blit(scaled, self.dest_rect.topleft)
