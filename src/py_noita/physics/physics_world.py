"""Physics World: Manages Pymunk 2D rigid-body dynamics coupled with the Numba pixel simulation grid."""

import math
from typing import List, Optional, Tuple
import numpy as np
import pygame
import pymunk

from py_noita.physics.rigid_body import BioRigidBody
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import (
    MAT_AIR,
    MAT_BLOOD,
    MAT_FIRE,
    MAT_TISSUE,
    PROP_STATE,
    STATE_LIQUID,
    STATE_POWDER,
    STATE_SOLID,
)


class PhysicsWorld:
    """Couples Pymunk rigid body physics with the falling sand pixel grid."""

    def __init__(self, grid: SimulationGrid, gravity: float = 480.0):
        self.grid = grid
        self.space = pymunk.Space()
        self.space.gravity = (0.0, gravity)
        self.space.damping = 0.96

        self.bodies: List[BioRigidBody] = []

    def add_body(self, body: BioRigidBody) -> BioRigidBody:
        """Register a rigid body into the simulation."""
        self.bodies.append(body)
        return body

    def remove_body(self, body: BioRigidBody) -> None:
        """Remove a body from the space and registry."""
        if body in self.bodies:
            self.bodies.remove(body)
        if body.shape in self.space.shapes:
            self.space.remove(body.shape)
        if body.body in self.space.bodies:
            self.space.remove(body.body)

    def apply_explosion(
        self,
        cx: float,
        cy: float,
        radius: float = 16.0,
        power: float = 40.0,
    ) -> None:
        """Apply explosion shockwave impulse, torque, and damage to rigid bodies."""
        max_dist = radius * 2.8
        for b in self.bodies:
            if not b.alive:
                continue

            dx = b.x - cx
            dy = b.y - cy
            dist = math.hypot(dx, dy)
            if dist <= max_dist:
                dist_safe = max(2.0, dist)
                falloff = max(0.1, 1.0 - (dist / max_dist))
                dir_x = dx / dist_safe
                dir_y = dy / dist_safe

                # Flings bodies away and upward
                impulse_mag = power * 32.0 * falloff
                impulse_x = dir_x * impulse_mag
                impulse_y = (dir_y - 0.35) * impulse_mag

                # World point offset creates natural torque/spin
                contact_pt = pymunk.Vec2d(cx, cy)
                b.body.apply_impulse_at_world_point(pymunk.Vec2d(impulse_x, impulse_y), contact_pt)

                # Damage prop
                dmg = power * falloff * 0.9
                b.take_damage(dmg)

    def update(
        self,
        dt: float,
        cam_x: int,
        cam_y: int,
        view_w: int,
        view_h: int,
    ) -> None:
        """Simulate rigid body step and couple with the pixel grid."""
        # 1. Step Pymunk physics
        # Multiple sub-steps for high stability
        sub_steps = 2
        sub_dt = dt / sub_steps
        for _ in range(sub_steps):
            self._pre_physics_terrain_collision()
            self.space.step(sub_dt)

        # 2. Pixel displacement and crushing
        self._displace_and_crush_pixels()

        # 3. Handle destroyed bodies
        surviving = []
        for b in self.bodies:
            if not b.alive:
                b.on_break(self.grid, self)
                if b.shape in self.space.shapes:
                    self.space.remove(b.shape)
                if b.body in self.space.bodies:
                    self.space.remove(b.body)
            else:
                surviving.append(b)
        self.bodies = surviving

    def _pre_physics_terrain_collision(self) -> None:
        """Detect overlaps between rigid bodies and solid terrain pixels,
        applying contact reaction impulses.
        """
        for b in self.bodies:
            if not b.alive:
                continue

            pos = b.body.position
            vx, vy = b.body.velocity

            # Sample perimeter points around body shape
            sample_points = []
            if b.shape_type == "circle":
                r = b.radius
                for angle_deg in range(0, 360, 45):
                    rad = math.radians(angle_deg)
                    sample_points.append(
                        (pos.x + math.cos(rad) * r, pos.y + math.sin(rad) * r, math.cos(rad), math.sin(rad))
                    )
            else:
                # Polygon vertices and edge centers
                verts = b.shape.get_vertices() if hasattr(b.shape, "get_vertices") else []
                angle = b.body.angle
                world_verts = [v.rotated(angle) + pos for v in verts]
                n_verts = len(world_verts)
                for i in range(n_verts):
                    p1 = world_verts[i]
                    p2 = world_verts[(i + 1) % n_verts]
                    sample_points.append((p1.x, p1.y, (p1.x - pos.x) / max(1.0, b.width), (p1.y - pos.y) / max(1.0, b.height)))
                    # Midpoint
                    mx = (p1.x + p2.x) * 0.5
                    my = (p1.y + p2.y) * 0.5
                    sample_points.append((mx, my, (mx - pos.x) / max(1.0, b.width), (my - pos.y) / max(1.0, b.height)))

            # Check solid penetration
            penetrations = 0
            push_x, push_y = 0.0, 0.0
            for px, py, nx, ny in sample_points:
                ix = int(px)
                iy = int(py)
                if 0 <= ix < self.grid.width and 0 <= iy < self.grid.height:
                    if self.grid.is_solid(ix, iy):
                        penetrations += 1
                        push_x -= nx
                        push_y -= ny

            if penetrations > 0:
                # Normalize push vector
                mag = math.hypot(push_x, push_y)
                if mag > 0.001:
                    push_x /= mag
                    push_y /= mag
                else:
                    push_y = -1.0  # Default push upward

                # Restitution and friction
                rebound = 0.3
                vel_along_normal = vx * push_x + vy * push_y

                if vel_along_normal < 0:
                    # Velocity towards solid: reflect and dampen
                    new_vx = vx - (1.0 + rebound) * vel_along_normal * push_x
                    new_vy = vy - (1.0 + rebound) * vel_along_normal * push_y
                    # Apply friction along tangent
                    tangent_x = -push_y
                    tangent_y = push_x
                    vel_tangent = new_vx * tangent_x + new_vy * tangent_y
                    friction_factor = 0.85
                    b.body.velocity = (
                        new_vx - vel_tangent * (1.0 - friction_factor) * tangent_x,
                        new_vy - vel_tangent * (1.0 - friction_factor) * tangent_y,
                    )
                    b.body.angular_velocity *= 0.88

                # Position separation to prevent sinking
                sep_dist = min(2.5, penetrations * 0.6)
                b.body.position = (pos.x + push_x * sep_dist, pos.y + push_y * sep_dist)

    def _displace_and_crush_pixels(self) -> None:
        """Displace liquids and powders that overlap rigid bodies, and crush soft tissue."""
        for b in self.bodies:
            if not b.alive:
                continue

            pos = b.body.position
            vx, vy = b.body.velocity
            speed = math.hypot(vx, vy)

            # Bounding box of body
            half_w = int(b.width * 0.6 if b.shape_type != "circle" else b.radius) + 1
            half_h = int(b.height * 0.6 if b.shape_type != "circle" else b.radius) + 1

            bx0 = max(1, int(pos.x - half_w))
            bx1 = min(self.grid.width - 2, int(pos.x + half_w))
            by0 = max(1, int(pos.y - half_h))
            by1 = min(self.grid.height - 2, int(pos.y + half_h))

            # Sample overlapping cells
            for y in range(by0, by1 + 1):
                for x in range(bx0, bx1 + 1):
                    if b.contains_point(float(x), float(y)):
                        mat = int(self.grid.grid[y, x])
                        if mat == MAT_AIR:
                            continue

                        state = PROP_STATE[mat]

                        # Crushing soft tissue at high impact
                        if mat == MAT_TISSUE and speed > 4.5:
                            # Crush into blood
                            self.grid.set_pixel(x, y, MAT_BLOOD)
                            b.take_damage(0.08)
                            continue

                        # Displace liquids and powders
                        if state in (STATE_LIQUID, STATE_POWDER):
                            out_x = 1 if (x > pos.x or (x == pos.x and vx >= 0)) else -1
                            displaced = False
                            # Search outwards and upwards for empty neighbor
                            for d in range(1, half_w + 4):
                                for ddx, ddy in [
                                    (0, -d),
                                    (out_x * d, -d),
                                    (out_x * d, 0),
                                    (-out_x * d, -d),
                                    (out_x * d, d),
                                ]:
                                    tx = x + ddx
                                    ty = y + ddy
                                    if 1 <= tx < self.grid.width - 1 and 1 <= ty < self.grid.height - 1:
                                        if not b.contains_point(float(tx), float(ty)) and self.grid.is_empty(tx, ty):
                                            self.grid.grid[ty, tx] = mat
                                            self.grid.life[ty, tx] = self.grid.life[y, x]
                                            self.grid.grid[y, x] = MAT_AIR
                                            self.grid.mark_dirty(tx, ty)
                                            self.grid.mark_dirty(x, y)
                                            displaced = True
                                            break
                                if displaced:
                                    break
                            if not displaced:
                                ty = max(1, int(pos.y - half_h - 1))
                                if not b.contains_point(float(x), float(ty)) and self.grid.is_empty(x, ty):
                                    self.grid.grid[ty, x] = mat
                                    self.grid.life[ty, x] = self.grid.life[y, x]
                                    self.grid.grid[y, x] = MAT_AIR
                                    self.grid.mark_dirty(x, ty)
                                    self.grid.mark_dirty(x, y)

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        """Render all active rigid bodies."""
        for b in self.bodies:
            b.draw(surface, cam_x, cam_y)
