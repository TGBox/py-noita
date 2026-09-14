"""Cellular structural collapse and terrain fragmentation mechanics."""

from collections import deque
import math
import random
from typing import Any, List, Optional, Set, Tuple
import numpy as np
import pygame
import pymunk

from py_noita.physics.rigid_body import BioRigidBody
from py_noita.simulation.materials import (
    LUT_COLORS,
    MAT_AIR,
    MAT_BLOOD,
    MAT_BONE,
    MAT_BONE_CHIP,
    MAT_CHITIN,
    MAT_FIRE,
    MAT_NERVE,
    MAT_TENTACLE_FLESH,
    MAT_TISSUE,
    MAT_WALL_BONE,
    PROP_STATE,
    STATE_SOLID,
)


class CollapsingTerrainChunk(BioRigidBody):
    """A cluster of detached terrain pixels that broke loose from the cavern.
    Simulated as a Pymunk rigid body with pixel-accurate raster rendering,
    kinetic crushing of entities, and shattering on impact.
    """

    def __init__(
        self,
        space: pymunk.Space,
        cx: float,
        cy: float,
        pixel_data: List[Tuple[int, int, int]],  # (rel_x, rel_y, mat_id)
        width: float,
        height: float,
        dominant_mat: int = MAT_BONE,
        is_stalactite: bool = False,
    ):
        mass = max(4.0, len(pixel_data) * 0.45)
        shape_type = "circle" if (abs(width - height) < 3.0 and width < 12.0) else "box"
        radius = max(width, height) * 0.5

        super().__init__(
            space=space,
            x=cx,
            y=cy,
            shape_type=shape_type,
            width=max(4.0, width),
            height=max(4.0, height),
            radius=radius,
            mass=mass,
            friction=0.65,
            elasticity=0.15,
            color=(190, 180, 160),
            name="Decken-Stalaktit" if is_stalactite else "Terrain-Trümmer",
            health=30.0 + len(pixel_data) * 0.2,
            destructible=True,
        )
        self.pixel_data = pixel_data
        self.dominant_mat = dominant_mat
        self.is_stalactite = is_stalactite
        self.has_shattered = False

        # Pre-render raster sprite for fast drawing
        w_int = max(2, int(math.ceil(width)))
        h_int = max(2, int(math.ceil(height)))
        self.sprite = pygame.Surface((w_int + 2, h_int + 2), pygame.SRCALPHA)
        half_w = width * 0.5
        half_h = height * 0.5
        for rx, ry, mat in pixel_data:
            px = int(rx + half_w)
            py = int(ry + half_h)
            if 0 <= px <= w_int + 1 and 0 <= py <= h_int + 1:
                col = tuple(int(c) for c in LUT_COLORS[mat])
                self.sprite.set_at((px, py), (*col, 255))

    def on_break(self, grid, physics_world) -> None:
        """Shatter and crumble into loose debris and dust on ground impact."""
        if self.has_shattered:
            return
        self.has_shattered = True

        ix = int(round(self.x))
        iy = int(round(self.y))

        # Deposit or spray debris
        if self.dominant_mat == MAT_BONE or self.is_stalactite:
            grid.spray_circle(
                ix,
                iy,
                radius=max(3, int(self.radius * 0.7)),
                mat=MAT_BONE_CHIP,
                density=0.8,
            )
            grid.spray_circle(
                ix,
                iy,
                radius=max(2, int(self.radius * 0.4)),
                mat=MAT_BLOOD,
                density=0.3,
            )
        else:
            grid.spray_circle(
                ix,
                iy,
                radius=max(3, int(self.radius * 0.7)),
                mat=MAT_TISSUE,
                density=0.7,
            )
            grid.spray_circle(
                ix,
                iy,
                radius=max(2, int(self.radius * 0.5)),
                mat=MAT_BLOOD,
                density=0.6,
            )

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        """Render rotated terrain chunk sprite."""
        if not self.alive or self.has_shattered:
            return

        sx = int(round(self.x - cam_x))
        sy = int(round(self.y - cam_y))

        # Rotate sprite
        angle_deg = -math.degrees(self.body.angle)
        rotated = pygame.transform.rotate(self.sprite, angle_deg)
        rect = rotated.get_rect(center=(sx, sy))
        surface.blit(rotated, rect)


def check_and_collapse_terrain(
    grid: SimulationGrid,
    physics_world: Any,
    center: Tuple[int, int],
    search_radius: int,
    max_cluster_size: int = 400,
) -> List[CollapsingTerrainChunk]:
    """Scan perimeter of recently carved/destroyed terrain at center.
    Any connected solid component that is completely disconnected from
    MAT_WALL_BONE or world boundary anchors is detached and spawned as a
    physical falling rigid-body chunk.
    """
    if physics_world is None:
        return []

    cx, cy = center
    w = grid.width
    h = grid.height

    # Bounding box of search area
    x0 = max(2, cx - search_radius - 2)
    x1 = min(w - 3, cx + search_radius + 2)
    y0 = max(2, cy - search_radius - 2)
    y1 = min(h - 3, cy + search_radius + 2)

    visited: Set[Tuple[int, int]] = set()
    collapsed_chunks: List[CollapsingTerrainChunk] = []

    # Check candidates on perimeter
    candidates = []
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if (x - cx) * (x - cx) + (y - cy) * (y - cy) <= (search_radius + 2) * (
                search_radius + 2
            ):
                mat = grid.grid[y, x]
                if (
                    mat != MAT_AIR
                    and mat != MAT_WALL_BONE
                    and PROP_STATE[mat] == STATE_SOLID
                ):
                    candidates.append((x, y))

    for start_x, start_y in candidates:
        if (start_x, start_y) in visited:
            continue

        # BFS to find connected component
        queue = deque([(start_x, start_y)])
        visited.add((start_x, start_y))
        component: List[Tuple[int, int, int]] = []
        is_anchored = False

        while queue:
            qx, qy = queue.popleft()
            q_mat = int(grid.grid[qy, qx])
            component.append((qx, qy, q_mat))

            # Exceeded max floating cluster size => safely anchored to large cavern mass
            if len(component) > max_cluster_size:
                is_anchored = True
                while queue:
                    dqx, dqy = queue.popleft()
                    for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        dnx, dny = dqx + ddx, dqy + ddy
                        if 0 <= dnx < w and 0 <= dny < h and (dnx, dny) not in visited:
                            if grid.grid[dny, dnx] != MAT_AIR and PROP_STATE[grid.grid[dny, dnx]] == STATE_SOLID:
                                visited.add((dnx, dny))
                break

            # Boundary anchor check
            if qx <= 3 or qx >= w - 4 or qy <= 3 or qy >= h - 4:
                is_anchored = True

            # Neighbors (8-connectivity)
            for ddx, ddy in (
                (1, 0),
                (-1, 0),
                (0, 1),
                (0, -1),
                (1, 1),
                (-1, 1),
                (1, -1),
                (-1, -1),
            ):
                nx = qx + ddx
                ny = qy + ddy
                if 0 <= nx < w and 0 <= ny < h:
                    n_mat = int(grid.grid[ny, nx])
                    if n_mat == MAT_WALL_BONE:
                        is_anchored = True
                    elif n_mat != MAT_AIR and PROP_STATE[n_mat] == STATE_SOLID:
                        if (nx, ny) not in visited:
                            visited.add((nx, ny))
                            queue.append((nx, ny))

        if is_anchored:
            continue

        # Found an unanchored cluster!
        if len(component) >= 5:
            # Calculate center of mass and bounding box
            sum_x = sum(p[0] for p in component)
            sum_y = sum(p[1] for p in component)
            comp_len = len(component)
            chunk_cx = sum_x / comp_len
            chunk_cy = sum_y / comp_len

            min_x = min(p[0] for p in component)
            max_x = max(p[0] for p in component)
            min_y = min(p[1] for p in component)
            max_y = max(p[1] for p in component)

            chunk_w = float(max_x - min_x + 1)
            chunk_h = float(max_y - min_y + 1)

            # Determine dominant material and whether it's a stalactite
            mat_counts = {}
            for _, _, m in component:
                mat_counts[m] = mat_counts.get(m, 0) + 1
            dominant = max(mat_counts, key=mat_counts.get)
            is_stalactite = (chunk_h > chunk_w * 1.6) and (dominant == MAT_BONE)

            # Build relative pixel data
            pixel_data = [
                (int(round(px - chunk_cx)), int(round(py - chunk_cy)), m)
                for px, py, m in component
            ]

            # Clear pixels from grid to MAT_AIR
            for px, py, _ in component:
                grid.grid[py, px] = MAT_AIR
                grid.life[py, px] = 0
                grid.mark_dirty(px, py)

            # Instantiate rigid body chunk
            chunk = CollapsingTerrainChunk(
                space=physics_world.space,
                cx=chunk_cx,
                cy=chunk_cy,
                pixel_data=pixel_data,
                width=chunk_w,
                height=chunk_h,
                dominant_mat=dominant,
                is_stalactite=is_stalactite,
            )
            # Give slight randomized tilt impulse
            chunk.body.velocity = (
                random.uniform(-8.0, 8.0),
                random.uniform(5.0, 20.0),
            )
            chunk.body.angular_velocity = random.uniform(-1.2, 1.2)

            physics_world.add_body(chunk)
            collapsed_chunks.append(chunk)

    return collapsed_chunks


def build_stalactite(
    grid: SimulationGrid,
    base_x: int,
    base_y: int,
    length: int = 20,
    base_width: int = 8,
    mat: int = MAT_BONE,
) -> None:
    """Generate a pointed osteo-stalactite hanging from the cavern ceiling."""
    half_w = base_width // 2
    for dy in range(length):
        y = base_y + dy
        if y >= grid.height - 1:
            break
        t = dy / length
        cur_w = max(1, int(round(half_w * (1.0 - t))))
        for dx in range(-cur_w, cur_w + 1):
            x = base_x + dx
            if 1 <= x < grid.width - 1:
                grid.set_pixel(x, y, mat)


def build_cartilage_bridge(
    grid: SimulationGrid,
    x1: int,
    x2: int,
    y: int,
    thickness: int = 4,
    mat: int = MAT_BONE,
) -> None:
    """Build a horizontal or arched cartilage bridge across a cavern gap."""
    span = abs(x2 - x1)
    if span <= 0:
        return
    min_x = min(x1, x2)
    max_x = max(x1, x2)

    for x in range(min_x, max_x + 1):
        t = (x - min_x) / span
        arch_offset = int(math.sin(t * math.pi) * 2.0)
        cur_y = y + arch_offset
        for dy in range(thickness):
            by = cur_y + dy
            if 0 <= by < grid.height and 0 <= x < grid.width:
                grid.set_pixel(x, by, mat)
