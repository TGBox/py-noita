"""Rigid body definitions for physical props and environmental objects."""

import math
from typing import List, Optional, Tuple
import pygame
import pymunk


class BioRigidBody:
    """Rigid body entity simulated by Pymunk and coupled with the falling sand grid."""

    def __init__(
        self,
        space: pymunk.Space,
        x: float,
        y: float,
        shape_type: str = "box",
        width: float = 16.0,
        height: float = 16.0,
        radius: float = 8.0,
        vertices: Optional[List[Tuple[float, float]]] = None,
        mass: float = 10.0,
        friction: float = 0.7,
        elasticity: float = 0.25,
        color: Tuple[int, int, int] = (190, 180, 165),
        outline_color: Tuple[int, int, int] = (90, 80, 75),
        name: str = "Knochenblock",
        health: float = 50.0,
        destructible: bool = True,
    ):
        self.shape_type = shape_type
        self.width = width
        self.height = height
        self.radius = radius
        self.color = color
        self.outline_color = outline_color
        self.name = name
        self.health = health
        self.max_health = health
        self.destructible = destructible
        self.alive: bool = True

        # Calculate moment of inertia
        if shape_type == "circle":
            moment = pymunk.moment_for_circle(mass, 0, radius)
            self.body = pymunk.Body(mass, moment)
            self.shape = pymunk.Circle(self.body, radius)
        elif shape_type == "poly" and vertices:
            moment = pymunk.moment_for_poly(mass, vertices)
            self.body = pymunk.Body(mass, moment)
            self.shape = pymunk.Poly(self.body, vertices)
        else:  # box
            moment = pymunk.moment_for_box(mass, (width, height))
            self.body = pymunk.Body(mass, moment)
            self.shape = pymunk.Poly.create_box(self.body, (width, height))

        self.body.position = (x, y)
        self.shape.friction = friction
        self.shape.elasticity = elasticity
        self.shape.collision_type = 1  # 1 = rigid prop

        # Reference back to this instance
        self.shape.user_data = self
        self.body.user_data = self

        space.add(self.body, self.shape)

    @property
    def x(self) -> float:
        return self.body.position.x

    @property
    def y(self) -> float:
        return self.body.position.y

    @property
    def angle(self) -> float:
        return self.body.angle

    @property
    def velocity(self) -> Tuple[float, float]:
        return self.body.velocity.x, self.body.velocity.y

    def contains_point(self, wx: float, wy: float) -> bool:
        """Point-in-shape test in world space."""
        point = pymunk.Vec2d(wx, wy)
        query = self.shape.point_query(point)
        return query.distance <= 0.0

    def take_damage(self, amount: float) -> None:
        """Apply structural damage."""
        if not self.destructible or not self.alive:
            return
        self.health -= amount
        if self.health <= 0.0:
            self.health = 0.0
            self.alive = False

    def on_break(self, grid, physics_world) -> None:
        """Callback invoked when object is destroyed."""
        pass

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        """Render rotated rigid body shape onto simulation viewport."""
        if not self.alive:
            return

        pos = self.body.position
        sx = int(round(pos.x - cam_x))
        sy = int(round(pos.y - cam_y))
        angle = self.body.angle

        if self.shape_type == "circle":
            r = int(self.radius)
            pygame.draw.circle(surface, self.color, (sx, sy), r)
            pygame.draw.circle(surface, self.outline_color, (sx, sy), r, 1)
            # Draw orientation line
            line_x = sx + int(math.cos(angle) * (r - 1))
            line_y = sy + int(math.sin(angle) * (r - 1))
            pygame.draw.line(surface, self.outline_color, (sx, sy), (line_x, line_y), 1)
        else:
            # Render polygon / box vertices
            raw_verts = self.shape.get_vertices() if hasattr(self.shape, "get_vertices") else []
            if raw_verts:
                screen_verts = []
                for v in raw_verts:
                    wv = v.rotated(angle) + pos
                    screen_verts.append((int(round(wv.x - cam_x)), int(round(wv.y - cam_y))))
                if len(screen_verts) >= 3:
                    pygame.draw.polygon(surface, self.color, screen_verts)
                    pygame.draw.polygon(surface, self.outline_color, screen_verts, 1)
