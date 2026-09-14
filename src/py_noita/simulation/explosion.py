"""Explosion algorithms, shockwaves, cratering, and debris scattering."""

import math
from typing import Any, List, Optional, Tuple
import numpy as np

from py_noita.simulation.materials import (
    MAT_AIR,
    MAT_ASH,
    MAT_BIOGAS,
    MAT_BONE,
    MAT_BONE_CHIP,
    MAT_FIRE,
    MAT_SMOKE,
    MAT_TISSUE,
    MAT_WALL_BONE,
    PROP_FLAMMABILITY,
    PROP_LIFETIME,
    PROP_STATE,
    STATE_SOLID,
)
from py_noita.simulation.grid import SimulationGrid


class ExplosionDebris:
    """A physics particle flung by an explosion into the grid."""
    def __init__(self, x: float, y: float, vx: float, vy: float, mat: int):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.mat = mat
        self.lifetime = 120

    def update(self, grid: SimulationGrid) -> bool:
        """Step particle physics. Returns False if settled or expired."""
        self.lifetime -= 1
        if self.lifetime <= 0:
            return False

        self.vy += 0.25  # Gravity
        nx = self.x + self.vx
        ny = self.y + self.vy

        ix, iy = int(nx), int(ny)
        if 1 <= ix < grid.width - 1 and 1 <= iy < grid.height - 1:
            if grid.is_solid(ix, iy):
                # Settle on surface as powder
                grid.set_pixel(int(self.x), int(self.y), self.mat)
                return False
            self.x = nx
            self.y = ny
            return True
        return False


def create_explosion(
    grid: SimulationGrid,
    cx: int,
    cy: int,
    radius: int = 14,
    power: float = 40.0,
    spawn_fire: bool = True,
    physics_world: Optional[Any] = None,
) -> Tuple[int, List[ExplosionDebris]]:
    """Create a visceral explosion at (cx, cy).
    Carves out a crater in solid tissue/bone, flings bone chips & ash debris,
    spawns fire/smoke, and returns (damaged_cells_count, list_of_debris).
    """
    pw = physics_world if physics_world is not None else getattr(grid, "physics_world", None)
    if pw is not None:
        pw.apply_explosion(float(cx), float(cy), float(radius), float(power))

    damaged_cells = 0
    debris_list: List[ExplosionDebris] = []
    r_sq = radius * radius

    x0 = max(1, cx - radius)
    x1 = min(grid.width - 2, cx + radius)
    y0 = max(1, cy - radius)
    y1 = min(grid.height - 2, cy + radius)

    # 1. Carve crater and collect debris
    for y in range(y0, y1 + 1):
        dy = y - cy
        dy_sq = dy * dy
        for x in range(x0, x1 + 1):
            dx = x - cx
            dist_sq = dx * dx + dy_sq
            if dist_sq <= r_sq:
                cur_mat = grid.grid[y, x]
                if cur_mat == MAT_WALL_BONE:
                    continue  # Unbreakable outer bone wall

                # If biogas caught in blast: expands explosion radius!
                if cur_mat == MAT_BIOGAS:
                    grid.set_pixel(x, y, MAT_FIRE, life_val=45)
                    damaged_cells += 1
                    continue

                if cur_mat != MAT_AIR:
                    damaged_cells += 1

                    # Chance to fling debris particles on edge of blast
                    dist = math.sqrt(dist_sq)
                    if dist > radius * 0.4 and np.random.random() < 0.25:
                        deb_mat = MAT_BONE_CHIP if cur_mat == MAT_BONE else MAT_ASH
                        angle = math.atan2(dy, dx) + np.random.uniform(-0.3, 0.3)
                        speed = np.random.uniform(2.5, 6.0)
                        debris_list.append(
                            ExplosionDebris(
                                float(x),
                                float(y),
                                math.cos(angle) * speed,
                                math.sin(angle) * speed - 1.5,
                                deb_mat,
                            )
                        )

                    # Interior becomes fire or air
                    if spawn_fire and dist < radius * 0.7 and np.random.random() < 0.5:
                        grid.grid[y, x] = MAT_FIRE
                        grid.life[y, x] = int(PROP_LIFETIME[MAT_FIRE] * np.random.uniform(0.5, 1.2))
                    else:
                        grid.grid[y, x] = MAT_AIR
                        grid.life[y, x] = 0

    # 2. Add ring of smoke and ember fire along perimeter
    perimeter_radius = radius + 2
    for angle_deg in range(0, 360, 15):
        rad = math.radians(angle_deg)
        px = int(cx + math.cos(rad) * perimeter_radius)
        py = int(cy + math.sin(rad) * perimeter_radius)
        if 1 <= px < grid.width - 1 and 1 <= py < grid.height - 1:
            if grid.grid[py, px] == MAT_AIR:
                if np.random.random() < 0.4:
                    grid.set_pixel(px, py, MAT_SMOKE, life_val=np.random.randint(60, 180))

    grid.mark_dirty(cx, cy, radius + 4)

    # 3. Cellular Structural Collapse for unsupported/severed terrain
    if pw is not None:
        from py_noita.physics.collapse import check_and_collapse_terrain

        check_and_collapse_terrain(grid, pw, (cx, cy), radius + 3)

    return damaged_cells, debris_list
