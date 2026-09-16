"""Core rendering engine: Pixel grid blitting, dynamic scaling, and aspect management."""

import math
from typing import Optional, Tuple
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
from py_noita.rendering.shaders import ShaderPostProcessor
from py_noita.simulation.materials import (
    LUT_COLORS,
    MAT_ACID,
    MAT_AIR,
    MAT_BILE,
    MAT_BLOOD,
    MAT_LYMPH,
    MAT_MUTAGEN,
    MAT_PUS,
    MAT_WATER,
    PROP_GLOW,
    PROP_STATE,
    STATE_EMPTY,
    STATE_LIQUID,
    STATE_SOLID,
)


@njit(fastmath=True)
def render_slice_to_surfarray(
    grid: np.ndarray,
    color_var: np.ndarray,
    cam_x: int,
    cam_y: int,
    out_surfarray: np.ndarray,
    lut_colors: np.ndarray,
    prop_state: np.ndarray,
    bg_r: int,
    bg_g: int,
    bg_b: int,
    stain_map: np.ndarray,
    time_val: float = 0.0,
) -> None:
    """Fast Numba kernel that writes the visible world slice directly into
    out_surfarray (view_w, view_h, 3) for Pygame surfarray blit, featuring:
    - Viscous capillary menisci climbing up solid container walls
    - Metaball-style subpixel fluid edge antialiasing and cohesion bridging
    - Dynamic specular wave gleam on blood, acid, bile, and mutagen surfaces
    - Viscous fluid body smoothing to eliminate graininess in liquid pools
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
                st = prop_state[mat]

                if mat == MAT_AIR or st == STATE_EMPTY:
                    # Subtle visceral cavern background dither
                    dither = ((gx ^ gy) & 3) * 2
                    r = bg_r + dither
                    g = bg_g + dither
                    b = bg_b + dither

                    # 1. Viscous Meniscus Effect at solid boundary walls
                    # Fluid climbing up solid walls due to capillary action / surface tension
                    has_liquid_below = False
                    below_mat = MAT_AIR
                    if gy + 1 < grid_h:
                        below_mat = grid[gy + 1, gx]
                        if prop_state[below_mat] == STATE_LIQUID:
                            has_liquid_below = True

                    if has_liquid_below:
                        # Check if touching solid wall to the left or right
                        is_wall_left = (gx > 0 and prop_state[grid[gy, gx - 1]] == STATE_SOLID)
                        is_wall_right = (gx < grid_w - 1 and prop_state[grid[gy, gx + 1]] == STATE_SOLID)

                        if is_wall_left or is_wall_right:
                            # Meniscus capillary climb: blend liquid below onto wall contact
                            lr = lut_colors[below_mat, 0]
                            lg = lut_colors[below_mat, 1]
                            lb = lut_colors[below_mat, 2]
                            r = int(r * 0.45 + lr * 0.55)
                            g = int(g * 0.45 + lg * 0.55)
                            b = int(b * 0.45 + lb * 0.55)
                        else:
                            # Subpixel antialiasing on curved liquid free surface (metaball boundary)
                            diag_l = (gx > 0 and prop_state[grid[gy + 1, gx - 1]] == STATE_LIQUID)
                            diag_r = (gx < grid_w - 1 and prop_state[grid[gy + 1, gx + 1]] == STATE_LIQUID)
                            if diag_l and diag_r:
                                lr = lut_colors[below_mat, 0]
                                lg = lut_colors[below_mat, 1]
                                lb = lut_colors[below_mat, 2]
                                r = int(r * 0.75 + lr * 0.25)
                                g = int(g * 0.75 + lg * 0.25)
                                b = int(b * 0.75 + lb * 0.25)
                    else:
                        # 2. Horizontal Cohesion Bridging (single-cell air gaps between liquids)
                        if 0 < gx < grid_w - 1:
                            l_mat = grid[gy, gx - 1]
                            r_mat = grid[gy, gx + 1]
                            if prop_state[l_mat] == STATE_LIQUID and prop_state[r_mat] == STATE_LIQUID:
                                lr = lut_colors[l_mat, 0]
                                lg = lut_colors[l_mat, 1]
                                lb = lut_colors[l_mat, 2]
                                r = int(r * 0.35 + lr * 0.65)
                                g = int(g * 0.35 + lg * 0.65)
                                b = int(b * 0.35 + lb * 0.65)

                    out_surfarray[sx, sy, 0] = max(0, min(255, r))
                    out_surfarray[sx, sy, 1] = max(0, min(255, g))
                    out_surfarray[sx, sy, 2] = max(0, min(255, b))

                elif st == STATE_LIQUID:
                    base_r = lut_colors[mat, 0]
                    base_g = lut_colors[mat, 1]
                    base_b = lut_colors[mat, 2]

                    # Organic variation from color_var (0 to 3)
                    var = color_var[gy, gx]
                    offset = -4 if var == 0 else (-1 if var == 1 else (3 if var == 2 else 6))
                    r = base_r + offset
                    g = base_g + offset
                    b = base_b + offset

                    # Fluid Body Smoothing: smooth out noise inside large liquid pools
                    if 0 < gy < grid_h - 1 and 0 < gx < grid_w - 1:
                        if (
                            prop_state[grid[gy - 1, gx]] == STATE_LIQUID
                            and prop_state[grid[gy + 1, gx]] == STATE_LIQUID
                            and prop_state[grid[gy, gx - 1]] == STATE_LIQUID
                            and prop_state[grid[gy, gx + 1]] == STATE_LIQUID
                        ):
                            r = int(r * 0.75 + base_r * 0.25)
                            g = int(g * 0.75 + base_g * 0.25)
                            b = int(b * 0.75 + base_b * 0.25)

                    # Dynamic Specular Wave Highlights on Liquid Free Surface
                    is_surface = (gy == 0 or grid[gy - 1, gx] == MAT_AIR or prop_state[grid[gy - 1, gx]] == STATE_EMPTY)
                    if is_surface:
                        phase1 = gx * 0.38 + time_val * 4.2
                        phase2 = gx * 0.95 - time_val * 2.7
                        w1 = 0.5 + 0.5 * math.sin(phase1)
                        w2 = 0.5 + 0.5 * math.sin(phase2)
                        spec = (w1 * 0.7 + w2 * 0.3) ** 4

                        if mat == MAT_BLOOD:
                            # Arterial ruby crest gleam
                            r += int(spec * 85.0)
                            g += int(spec * 30.0)
                            b += int(spec * 40.0)
                        elif mat == MAT_ACID:
                            # Caustic electric green / cyan glow
                            r += int(spec * 65.0)
                            g += int(spec * 130.0)
                            b += int(spec * 85.0)
                        elif mat == MAT_MUTAGEN:
                            # Prismatic ultraviolet shimmer
                            r += int(spec * 90.0)
                            g += int(spec * 50.0)
                            b += int(spec * 140.0)
                        elif mat == MAT_BILE or mat == MAT_PUS:
                            # Viscous golden oily sheen
                            r += int(spec * 85.0)
                            g += int(spec * 85.0)
                            b += int(spec * 25.0)
                        else:
                            # Water / Lymph crystalline highlight
                            r += int(spec * 75.0)
                            g += int(spec * 95.0)
                            b += int(spec * 120.0)

                    out_surfarray[sx, sy, 0] = max(0, min(255, r))
                    out_surfarray[sx, sy, 1] = max(0, min(255, g))
                    out_surfarray[sx, sy, 2] = max(0, min(255, b))

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

                    # Permanent visceral decals (blood crust, slime, mutagen, acid etch, char/soot)
                    stain = stain_map[gy, gx]
                    if stain == 1:  # STAIN_BLOOD: arterial coagulated red
                        r = min(255, int(r * 0.55 + 95))
                        g = int(g * 0.25)
                        b = int(b * 0.30)
                    elif stain == 2:  # STAIN_SLIME: yellowish pus / bile sheen
                        r = min(255, int(r * 0.65 + 65))
                        g = min(255, int(r * 0.70 + 75))
                        b = int(b * 0.20)
                    elif stain == 3:  # STAIN_MUTAGEN: glowing violet mutagen residue
                        r = min(255, int(r * 0.55 + 85))
                        g = int(g * 0.20)
                        b = min(255, int(r * 0.65 + 115))
                    elif stain == 4:  # STAIN_ACID: caustic corrosive etch
                        r = int(r * 0.35 + 20)
                        g = min(255, int(g * 0.75 + 90))
                        b = int(b * 0.35 + 20)
                    elif stain == 5:  # STAIN_CHAR: charred carbon soot mark
                        r = int(r * 0.15 + 8)
                        g = int(g * 0.15 + 6)
                        b = int(b * 0.15 + 8)

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
        self.is_ultrawide = (screen_res[0] / max(1, screen_res[1])) > 2.0
        self.zoom_factor: str = "STANDARD"
        self.integer_scaling: bool = False
        self.filter_mode: str = "CRISP"  # "CRISP" or "SMOOTH"
        self.anim_time: float = 0.0

        # Viewport dimensions and buffers
        self.view_w = VIEWPORT_SIM_WIDTH_16_9
        self.view_h = VIEWPORT_SIM_HEIGHT
        self.sim_surface = pygame.Surface((self.view_w, self.view_h))
        self.surfarray_buffer = np.zeros((self.view_w, self.view_h, 3), dtype=np.uint8)
        self.post_processor = ShaderPostProcessor(self.view_w, self.view_h)
        self.dest_rect = pygame.Rect(0, 0, screen_res[0], screen_res[1])

        self.update_dest_rect(screen_res)

    def apply_graphics_options(self, integer_scaling: bool = False, filter_mode: str = "CRISP", camera_zoom: str = "STANDARD") -> None:
        """Apply integer scaling, pixel texture filtering, and zoom viewport sizing."""
        self.integer_scaling = integer_scaling
        self.filter_mode = filter_mode
        self.zoom_factor = camera_zoom
        self.update_dest_rect(self.screen_res)

    def set_resolution(self, screen_res: Tuple[int, int]) -> None:
        """Update display resolution and dynamically adapt viewport to eliminate black borders."""
        self.update_dest_rect(screen_res)

    def update_dest_rect(self, screen_res: Tuple[int, int]) -> None:
        """Calculate dynamic Noita-style simulation viewport dimensions and scaled destination rectangle."""
        target_w = max(320, screen_res[0])
        target_h = max(240, screen_res[1])
        self.screen_res = (target_w, target_h)
        self.is_ultrawide = (target_w / target_h) > 2.0

        # Scale divisor based on screen height and zoom setting (Noita dynamic resolution)
        # Standard: ~360p height
        # Weit: ~450p height (sees more cavern)
        # Nah: ~270p height (closer view)
        base_h = 270 if self.zoom_factor == "NAH" else (450 if self.zoom_factor == "WEIT" else 360)
        scale = max(1, target_h // base_h)

        new_view_w = max(320, target_w // scale)
        new_view_h = max(180, target_h // scale)

        # Update buffers if viewport size changed
        if new_view_w != self.view_w or new_view_h != self.view_h:
            self.view_w = new_view_w
            self.view_h = new_view_h
            self.sim_surface = pygame.Surface((self.view_w, self.view_h))
            self.surfarray_buffer = np.zeros((self.view_w, self.view_h, 3), dtype=np.uint8)
            ps_mode = getattr(self.post_processor, "photosensitivity_mode", False)
            self.post_processor = ShaderPostProcessor(self.view_w, self.view_h)
            self.post_processor.photosensitivity_mode = ps_mode

        if self.integer_scaling:
            scaled_w = self.view_w * scale
            scaled_h = self.view_h * scale
            offset_x = (target_w - scaled_w) // 2
            offset_y = (target_h - scaled_h) // 2
            self.dest_rect = pygame.Rect(offset_x, offset_y, scaled_w, scaled_h)
        else:
            # Format fill: covers 100% of window/screen without letterbox/pillarbox
            self.dest_rect = pygame.Rect(0, 0, target_w, target_h)

    def render_grid(
        self,
        grid: np.ndarray,
        color_var: np.ndarray,
        cam_x: int,
        cam_y: int,
        stain_map: Optional[np.ndarray] = None,
        dt: float = 0.016,
    ) -> None:
        """Blit simulation grid pixels to the internal sim_surface with fluid smoothing, surface wave gleams, and permanent decals."""
        self.anim_time += dt
        stains = stain_map if stain_map is not None else np.zeros((grid.shape[0], grid.shape[1]), dtype=np.uint8)
        render_slice_to_surfarray(
            grid,
            color_var,
            cam_x,
            cam_y,
            self.surfarray_buffer,
            LUT_COLORS,
            PROP_STATE,
            COLOR_BG_DARK[0],
            COLOR_BG_DARK[1],
            COLOR_BG_DARK[2],
            stains,
            self.anim_time,
        )
        pygame.surfarray.blit_array(self.sim_surface, self.surfarray_buffer)

    def get_processed_world_surface(self) -> pygame.Surface:
        """Apply post-processing shaders to sim_surface and return composited world surface."""
        return self.post_processor.apply_post_processing(self.sim_surface)

    def present(self, screen: pygame.Surface, surface_to_present: Optional[pygame.Surface] = None) -> None:
        """Scale render surface up to the display window with aspect preservation."""
        render_surf = surface_to_present if surface_to_present is not None else self.post_processor.apply_post_processing(self.sim_surface)

        actual_size = screen.get_size()
        if actual_size != self.screen_res:
            self.update_dest_rect(actual_size)
            self.screen_res = actual_size

        if self.filter_mode == "SMOOTH":
            scaled = pygame.transform.smoothscale(render_surf, (self.dest_rect.width, self.dest_rect.height))
        else:
            scaled = pygame.transform.scale(render_surf, (self.dest_rect.width, self.dest_rect.height))

        if self.dest_rect.size == actual_size and self.dest_rect.topleft == (0, 0):
            screen.blit(scaled, (0, 0))
        else:
            screen.fill((0, 0, 0))  # Clear black bars
            screen.blit(scaled, self.dest_rect.topleft)
