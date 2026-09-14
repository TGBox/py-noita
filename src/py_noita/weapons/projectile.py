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
        trigger_type: str = "NONE",
        proximity_radius: float = 0.0,
        penetration_trigger: bool = False,
        pattern: str = "NORMAL",
        bounce: int = 0,
        vampiric: bool = False,
        gravity: float = 0.0,
        slow_effect: bool = False,
        shooter: Optional[Any] = None,
        orbit_dist: float = 35.0,
        orbit_angle: float = 0.0,
        transmute_source: Optional[List[int]] = None,
        transmute_target: int = MAT_AIR,
        transmute_radius: int = 0,
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
        self.transmute_source = transmute_source
        self.transmute_target = transmute_target
        self.transmute_radius = transmute_radius

        self.trigger_type = trigger_type
        self.proximity_radius = proximity_radius
        self.penetration_trigger = penetration_trigger
        self.pattern = pattern
        self.bounce = bounce
        self.vampiric = vampiric
        self.gravity = gravity
        self.slow_effect = slow_effect
        self.shooter = shooter
        self.orbit_dist = orbit_dist
        self.orbit_angle = orbit_angle
        self.initial_lifetime = lifetime
        self.initial_vx = vx
        self.initial_vy = vy
        self.anim_time: float = 0.0

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

        self.anim_time += 1.0
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.alive = False
            if self.transmute_radius > 0:
                self._handle_impact(grid, int(self.x), int(self.y))
            return self._trigger_payload(self.x, self.y)

        # Gravity effect
        if self.gravity != 0.0:
            self.vy += self.gravity

        # Proximity Trigger check
        if self.proximity_radius > 0.0 and targets:
            for t in targets:
                if getattr(t, "alive", False):
                    p_dist = math.hypot(self.x - t.center_x, self.y - t.center_y)
                    if p_dist <= self.proximity_radius:
                        self.alive = False
                        return self._trigger_payload(self.x, self.y)

        # Movement patterns: Boomerang, Helix, Orbital
        if self.pattern == "BOOMERANG":
            if self.lifetime < self.initial_lifetime * 0.65:
                speed = math.hypot(self.initial_vx, self.initial_vy)
                if speed > 0.01:
                    self.vx -= (self.initial_vx / speed) * 0.45
                    self.vy -= (self.initial_vy / speed) * 0.45
        elif self.pattern in ("HELIX_A", "HELIX_B"):
            cur_speed = math.hypot(self.vx, self.vy)
            if cur_speed > 0.01:
                cur_ang = math.atan2(self.vy, self.vx)
                perp_ang = cur_ang + math.pi / 2.0
                sign = 1.0 if self.pattern == "HELIX_A" else -1.0
                wave_v = math.cos(self.anim_time * 0.3) * 2.0 * sign
                self.x += math.cos(perp_ang) * wave_v
                self.y += math.sin(perp_ang) * wave_v
        elif self.pattern == "ORBIT" and self.shooter is not None:
            self.orbit_angle += 0.09
            self.x = self.shooter.center_x + math.cos(self.orbit_angle) * self.orbit_dist
            self.y = self.shooter.center_y + math.sin(self.orbit_angle) * self.orbit_dist

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
                            if self.vampiric and self.owner == "PLAYER" and self.shooter is not None:
                                if hasattr(self.shooter, "hp") and hasattr(self.shooter, "max_hp"):
                                    self.shooter.hp = min(self.shooter.max_hp, self.shooter.hp + 1.0)
                            if self.slow_effect:
                                if hasattr(target, "vx"):
                                    target.vx *= 0.5
                                if hasattr(target, "vy"):
                                    target.vy *= 0.5
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

            # 1c. Tendon / Joint collision
            if pw and getattr(pw, "tendons", None):
                for tendon in pw.tendons:
                    if not tendon.severed and tendon.check_hit(nx, ny, radius=self.radius + 3.0):
                        tendon.take_damage(self.damage)
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
                    if self.bounce > 0:
                        self.bounce -= 1
                        self.vx = -self.vx * 0.85
                        self.vy = -self.vy * 0.85
                        self.x += self.vx
                        self.y += self.vy
                        self._handle_impact(grid, ix, iy)
                        if self.penetration_trigger:
                            spawned_children.extend(self._trigger_payload(nx, ny))
                        continue

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
        """Handle impact effects (crater, acid spray, explosion, transmutation)."""
        if self.explosion_radius > 0:
            create_explosion(grid, ix, iy, radius=self.explosion_radius, power=self.damage)
        else:
            # Small impact dent
            grid.carve_circle(ix, iy, max(1, int(self.radius)), MAT_AIR)

        # Material Transmutation effect (if configured)
        if self.transmute_radius > 0 and self.transmute_target != MAT_AIR:
            grid.transmute_circle(ix, iy, self.transmute_radius, self.transmute_source, self.transmute_target)

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
