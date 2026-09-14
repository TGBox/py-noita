"""Simulation Grid Manager for Py-Noita."""

import math
from typing import Any, Optional, Set, Tuple
import numpy as np

from py_noita.config import CHUNK_SIZE, WORLD_HEIGHT, WORLD_WIDTH
from py_noita.simulation.materials import (
    MAT_AIR,
    MAT_WALL_BONE,
    PROP_ACID_VULN,
    PROP_DENSITY,
    PROP_DISPERSION,
    PROP_FLAMMABILITY,
    PROP_LIFETIME,
    PROP_STATE,
    STATE_SOLID,
    STATE_EMPTY,
    STATE_LIQUID,
    STATE_GAS,
    STATE_POWDER,
)
from py_noita.simulation.falling_sand import simulate_step


class SimulationGrid:
    """Manages the 2D pixel world grid and executes physics updates."""

    def __init__(self, width: int = WORLD_WIDTH, height: int = WORLD_HEIGHT):
        self.width = width
        self.height = height

        # Grid layers:
        # grid[y, x] = Material ID (uint8)
        self.grid = np.zeros((height, width), dtype=np.uint8)
        # life[y, x] = Remaining tick lifetime for decaying particles (uint16)
        self.life = np.zeros((height, width), dtype=np.uint16)
        # color_var[y, x] = Shading variation index (uint8, 0-3)
        self.color_var = np.random.randint(0, 4, size=(height, width), dtype=np.uint8)

        # Chunk tracking
        self.chunks_x = (width + CHUNK_SIZE - 1) // CHUNK_SIZE
        self.chunks_y = (height + CHUNK_SIZE - 1) // CHUNK_SIZE
        self.active_chunks: Set[Tuple[int, int]] = set()

        self.frame_count: int = 0
        self.total_moved: int = 0
        self.physics_world: Optional[Any] = None

        # Border walls (unbreakable bone boundaries)
        self.init_boundaries()

    def init_boundaries(self) -> None:
        """Create impenetrable boundary walls along the world borders."""
        self.grid[0, :] = MAT_WALL_BONE
        self.grid[-1, :] = MAT_WALL_BONE
        self.grid[:, 0] = MAT_WALL_BONE
        self.grid[:, -1] = MAT_WALL_BONE

    def mark_dirty(self, x: int, y: int, radius: int = 2) -> None:
        """Mark chunks around (x, y) as active."""
        cx0 = max(0, (x - radius) // CHUNK_SIZE)
        cx1 = min(self.chunks_x - 1, (x + radius) // CHUNK_SIZE)
        cy0 = max(0, (y - radius) // CHUNK_SIZE)
        cy1 = min(self.chunks_y - 1, (y + radius) // CHUNK_SIZE)

        for cy in range(cy0, cy1 + 1):
            for cx in range(cx0, cx1 + 1):
                self.active_chunks.add((cx, cy))

    def set_pixel(self, x: int, y: int, mat: int, life_val: int = 0) -> bool:
        """Set a single pixel material with boundary checking."""
        if 1 <= x < self.width - 1 and 1 <= y < self.height - 1:
            self.grid[y, x] = mat
            self.life[y, x] = life_val if life_val > 0 else PROP_LIFETIME[mat]
            self.mark_dirty(x, y)
            return True
        return False

    def get_pixel(self, x: int, y: int) -> int:
        """Get pixel material ID with safe boundary return."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return int(self.grid[y, x])
        return MAT_WALL_BONE

    def is_solid(self, x: int, y: int) -> bool:
        """Check if cell is solid terrain."""
        mat = self.get_pixel(x, y)
        return bool(PROP_STATE[mat] == STATE_SOLID)

    def is_liquid(self, x: int, y: int) -> bool:
        """Check if cell is liquid."""
        mat = self.get_pixel(x, y)
        return bool(PROP_STATE[mat] == STATE_LIQUID)

    def is_empty(self, x: int, y: int) -> bool:
        """Check if cell is air/empty."""
        return self.get_pixel(x, y) == MAT_AIR

    def fill_rect(self, x0: int, y0: int, w: int, h: int, mat: int) -> None:
        """Fill an axis-aligned rectangle with a material."""
        x_start = max(1, x0)
        x_end = min(self.width - 1, x0 + w)
        y_start = max(1, y0)
        y_end = min(self.height - 1, y0 + h)

        if x_start < x_end and y_start < y_end:
            self.grid[y_start:y_end, x_start:x_end] = mat
            self.life[y_start:y_end, x_start:x_end] = PROP_LIFETIME[mat]
            # Mark touched chunks dirty
            cx0 = x_start // CHUNK_SIZE
            cx1 = (x_end - 1) // CHUNK_SIZE
            cy0 = y_start // CHUNK_SIZE
            cy1 = (y_end - 1) // CHUNK_SIZE
            for cy in range(cy0, cy1 + 1):
                for cx in range(cx0, cx1 + 1):
                    self.active_chunks.add((cx, cy))

    def carve_circle(self, cx: int, cy: int, radius: int, fill_mat: int = MAT_AIR) -> int:
        """Carve or place a circle of material. Returns number of modified cells."""
        modified = 0
        r_sq = radius * radius
        x0 = max(1, cx - radius)
        x1 = min(self.width - 2, cx + radius)
        y0 = max(1, cy - radius)
        y1 = min(self.height - 2, cy + radius)

        for y in range(y0, y1 + 1):
            dy_sq = (y - cy) * (y - cy)
            for x in range(x0, x1 + 1):
                if (x - cx) * (x - cx) + dy_sq <= r_sq:
                    cur_mat = self.grid[y, x]
                    if cur_mat != MAT_WALL_BONE and cur_mat != fill_mat:
                        self.grid[y, x] = fill_mat
                        self.life[y, x] = PROP_LIFETIME[fill_mat]
                        modified += 1

        self.mark_dirty(cx, cy, radius + 2)
        return modified

    def spray_circle(self, cx: int, cy: int, radius: int, mat: int, density: float = 0.6) -> int:
        """Spray particles in a circular burst (e.g. for blood or acid splashes)."""
        placed = 0
        r_sq = radius * radius
        x0 = max(1, cx - radius)
        x1 = min(self.width - 2, cx + radius)
        y0 = max(1, cy - radius)
        y1 = min(self.height - 2, cy + radius)

        for y in range(y0, y1 + 1):
            dy_sq = (y - cy) * (y - cy)
            for x in range(x0, x1 + 1):
                if (x - cx) * (x - cx) + dy_sq <= r_sq:
                    if np.random.random() < density:
                        cur = self.grid[y, x]
                        if cur == MAT_AIR or PROP_STATE[cur] in (STATE_GAS, STATE_LIQUID):
                            self.grid[y, x] = mat
                            self.life[y, x] = PROP_LIFETIME[mat]
                            placed += 1

        self.mark_dirty(cx, cy, radius + 2)
        return placed

    def sample_and_consume_liquid(self, x: int, y: int, radius: int = 4) -> Optional[int]:
        """Suck up a liquid pixel from around (x, y) into player gland. Returns material ID."""
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                px, py = x + dx, y + dy
                if 1 <= px < self.width - 1 and 1 <= py < self.height - 1:
                    mat = self.grid[py, px]
                    if PROP_STATE[mat] == STATE_LIQUID:
                        self.grid[py, px] = MAT_AIR
                        self.mark_dirty(px, py, 2)
                        return int(mat)
        return None

    def update(self, cam_x: int, cam_y: int, view_w: int, view_h: int) -> int:
        """Run one frame of simulation on the active viewport area + margins."""
        self.frame_count += 1

        # Simulate around camera view + margin of 48 pixels
        margin = 48
        min_x = max(1, cam_x - margin)
        max_x = min(self.width - 2, cam_x + view_w + margin)
        min_y = max(1, cam_y - margin)
        max_y = min(self.height - 2, cam_y + view_h + margin)

        # Call Numba JIT simulation step
        moved = simulate_step(
            self.grid,
            self.life,
            self.color_var,
            min_x,
            max_x,
            min_y,
            max_y,
            self.frame_count,
            PROP_STATE,
            PROP_DENSITY,
            PROP_FLAMMABILITY,
            PROP_ACID_VULN,
            PROP_DISPERSION,
            PROP_LIFETIME,
        )

        self.total_moved = moved
        return moved
