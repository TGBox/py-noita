"""Active living projectiles with pixel collision, chemical trails, and triggers."""

import math
from typing import Any, List, Optional, Tuple
import numpy as np
import pygame
import pymunk

from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import (
    MAT_ACID,
    MAT_AIR,
    MAT_BLOOD,
    MAT_BONE_CHIP,
    MAT_FIRE,
    MAT_MUTAGEN,
    MAT_SPORES,
    MAT_TISSUE,
    MAT_WALL_BONE,
    PROP_STATE,
    STATE_SOLID,
)
from py_noita.simulation.explosion import create_explosion


class Projectile:
    """An in-flight projectile fired from an Organ-Cannula."""

    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        damage: float = 15.0,
        lifetime: int = 60,
        radius: float = 2.0,
        color: Tuple[int, int, int] = (240, 230, 200),
        piercing: bool = False,
        homing: bool = False,
        trail_material: int = MAT_AIR,
        impact_material: int = MAT_AIR,
        impact_material_count: int = 0,
        explosion_radius: int = 0,
        payload_genes: Optional[List] = None,
        owner: str = "PLAYER",
    ):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.lifetime = lifetime
        self.radius = radius
        self.color = color
        self.piercing = piercing
        self.homing = homing
        self.trail_material = trail_material
        self.impact_material = impact_material
        self.impact_material_count = impact_material_count
        self.explosion_radius = explosion_radius
        self.payload_genes = payload_genes or []
        self.owner = owner
        self.alive: bool = True

        # Penetration health for piercing
        self.pierce_health = 3 if piercing else 0

    def update(
        self,
        grid: SimulationGrid,
        targets: Optional[List] = None,
    ) -> List["Projectile"]:
        """Advance projectile physics, test collisions against terrain and targets.
        Returns newly spawned triggered child projectiles (if any).
        """
        if not self.alive:
            return []

        self.lifetime -= 1
        if self.lifetime <= 0:
            self.alive = False
            return self._trigger_payload(self.x, self.y)

        # Homing towards nearest target
        if self.homing and targets:
            nearest = None
            min_dist_sq = 140.0 * 140.0
            for t in targets:
                if t.alive:
                    dx = t.center_x - self.x
                    dy = t.center_y - self.y
                    d_sq = dx * dx + dy * dy
                    if d_sq < min_dist_sq:
                        min_dist_sq = d_sq
                        nearest = (dx, dy)

            if nearest:
                angle_to = math.atan2(nearest[1], nearest[0])
                cur_speed = math.hypot(self.vx, self.vy)
                cur_angle = math.atan2(self.vy, self.vx)
                diff = (angle_to - cur_angle + math.pi) % (2 * math.pi) - math.pi
                new_angle = cur_angle + max(-0.12, min(0.12, diff))
                self.vx = math.cos(new_angle) * cur_speed
                self.vy = math.sin(new_angle) * cur_speed

        # Sub-stepping for pixel-perfect collision without tunnelling
        speed = math.hypot(self.vx, self.vy)
        steps = max(1, int(math.ceil(speed / 2.0)))
        dx = self.vx / steps
        dy = self.vy / steps

        spawned_children: List[Projectile] = []

        for _ in range(steps):
            nx = self.x + dx
            ny = self.y + dy

            # Trail emission
            if self.trail_material != MAT_AIR and np.random.random() < 0.4:
                ix, iy = int(self.x), int(self.y)
                if 1 <= ix < grid.width - 1 and 1 <= iy < grid.height - 1:
                    if grid.is_empty(ix, iy):
                        grid.set_pixel(ix, iy, self.trail_material)

            # 1. Target collision (Enemies or Player)
            if targets:
                for target in targets:
                    if target.alive:
                        dist = math.hypot(nx - target.center_x, ny - target.center_y)
                        if dist <= self.radius + target.width / 2.0:
                            target.take_damage(self.damage, "PROJECTILE")
                            spawned_children.extend(self._trigger_payload(nx, ny))
                            self._handle_impact(grid, int(nx), int(ny))
                            if not self.piercing or self.pierce_health <= 0:
                                self.alive = False
                                return spawned_children
                            self.pierce_health -= 1

            # 1b. Rigid body / Prop collision
            pw = getattr(grid, "physics_world", None)
            if pw and pw.bodies:
                for b in pw.bodies:
                    if b.alive and b.contains_point(nx, ny):
                        b.take_damage(self.damage)
                        b.body.apply_impulse_at_world_point(
                            pymunk.Vec2d(self.vx * self.damage * 0.4, self.vy * self.damage * 0.4),
                            (nx, ny),
                        )
                        self._handle_impact(grid, int(nx), int(ny))
                        spawned_children.extend(self._trigger_payload(nx, ny))
                        if not self.piercing or self.pierce_health <= 0:
                            self.alive = False
                            return spawned_children
                        self.pierce_health -= 1

            # 2. Terrain collision
            ix, iy = int(nx), int(ny)
            if 0 <= ix < grid.width and 0 <= iy < grid.height:
                if grid.is_solid(ix, iy):
                    # Solid impact!
                    self._handle_impact(grid, ix, iy)
                    spawned_children.extend(self._trigger_payload(nx, ny))

                    if self.piercing and self.pierce_health > 0:
                        grid.carve_circle(ix, iy, int(self.radius) + 1, MAT_AIR)
                        self.pierce_health -= 1
                    else:
                        self.alive = False
                        return spawned_children

            self.x = nx
            self.y = ny

        return spawned_children

    def _handle_impact(self, grid: SimulationGrid, ix: int, iy: int) -> None:
        """Handle impact effects (crater, acid spray, explosion)."""
        if self.explosion_radius > 0:
            create_explosion(grid, ix, iy, radius=self.explosion_radius, power=self.damage)
        else:
            # Small impact dent
            grid.carve_circle(ix, iy, max(1, int(self.radius)), MAT_AIR)

        # Spray impact material (e.g. Acid, Blood, Mutagen, Fire)
        if self.impact_material != MAT_AIR and self.impact_material_count > 0:
            grid.spray_circle(ix, iy, radius=4, mat=self.impact_material, density=0.7)

    def _trigger_payload(self, hit_x: float, hit_y: float) -> List["Projectile"]:
        """Instantiate payload child projectiles if triggered."""
        if not self.payload_genes:
            return []

        # Evaluate payload genes into new projectiles at hit coordinates
        from py_noita.weapons.deck_evaluator import evaluate_payload
        return evaluate_payload(self.payload_genes, hit_x, hit_y, math.atan2(self.vy, self.vx), self.owner)

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        """Draw projectile with directional shape and glow."""
        if not self.alive:
            return

        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)

        # Viewport check
        if -10 <= sx <= surface.get_width() + 10 and -10 <= sy <= surface.get_height() + 10:
            # Draw elongated bullet line in velocity direction
            speed = math.hypot(self.vx, self.vy)
            tail_len = max(2.0, speed * 0.75)
            tail_x = sx - (self.vx / max(0.1, speed)) * tail_len
            tail_y = sy - (self.vy / max(0.1, speed)) * tail_len

            pygame.draw.line(surface, self.color, (int(tail_x), int(tail_y)), (sx, sy), max(1, int(self.radius)))
            pygame.draw.circle(surface, (255, 255, 255), (sx, sy), max(1, int(self.radius * 0.6)))
