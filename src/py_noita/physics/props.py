"""Destructible organic environmental props and physical objects."""

import math
from typing import Optional, Tuple
import pygame
import pymunk

from py_noita.physics.rigid_body import BioRigidBody
from py_noita.simulation.explosion import create_explosion
from py_noita.simulation.materials import (
    MAT_ACID,
    MAT_AIR,
    MAT_BIOGAS,
    MAT_BLOOD,
    MAT_FIRE,
)


class AcidGallbladder(BioRigidBody):
    """Rolling acid gland that bursts violently upon heavy impact or weapon damage."""

    def __init__(self, space: pymunk.Space, x: float, y: float):
        super().__init__(
            space=space,
            x=x,
            y=y,
            shape_type="circle",
            radius=7.0,
            mass=6.0,
            friction=0.35,
            elasticity=0.6,
            color=(80, 235, 35),
            outline_color=(40, 140, 20),
            name="Säure-Gallenblase",
            health=18.0,
            destructible=True,
        )

    def on_break(self, grid, physics_world) -> None:
        """Burst into an acid spray covering the surroundings."""
        ix = int(round(self.x))
        iy = int(round(self.y))
        grid.spray_circle(ix, iy, radius=12, mat=MAT_ACID, density=0.95)


class BiogasCyst(BioRigidBody):
    """Volatile organic gas cyst that triggers a devastating explosion when ruptured or touched by fire."""

    def __init__(self, space: pymunk.Space, x: float, y: float):
        super().__init__(
            space=space,
            x=x,
            y=y,
            shape_type="circle",
            radius=9.0,
            mass=5.0,
            friction=0.5,
            elasticity=0.45,
            color=(235, 135, 30),
            outline_color=(150, 75, 15),
            name="Biogas-Zyste",
            health=15.0,
            destructible=True,
        )

    def on_break(self, grid, physics_world) -> None:
        """Detonate into a high-powered fireball explosion releasing toxic biogas."""
        ix = int(round(self.x))
        iy = int(round(self.y))
        # Release biogas cloud around blast center
        grid.spray_circle(ix, iy, radius=14, mat=MAT_BIOGAS, density=0.8)
        # Detonate major explosion
        create_explosion(
            grid,
            ix,
            iy,
            radius=24,
            power=70.0,
            spawn_fire=True,
            physics_world=physics_world,
        )


class CartilageRaft(BioRigidBody):
    """Buoyant cartilage plank that floats on lakes of blood and digestive acid."""

    def __init__(self, space: pymunk.Space, x: float, y: float, width: float = 32.0):
        super().__init__(
            space=space,
            x=x,
            y=y,
            shape_type="box",
            width=width,
            height=6.0,
            mass=10.0,
            friction=0.85,
            elasticity=0.1,
            color=(185, 175, 150),
            outline_color=(115, 105, 90),
            name="Knorpel-Floß",
            health=120.0,
            destructible=True,
        )
        self.buoyant: bool = True

    def on_break(self, grid, physics_world) -> None:
        """Shatters into bone chips on destruction."""
        ix = int(round(self.x))
        iy = int(round(self.y))
        grid.spray_circle(ix, iy, radius=6, mat=MAT_BLOOD, density=0.5)


class BoneMinecart(BioRigidBody):
    """Heavy osteo-cart that rolls through tunnels and crushes enemies with kinetic force."""

    def __init__(self, space: pymunk.Space, x: float, y: float):
        super().__init__(
            space=space,
            x=x,
            y=y,
            shape_type="box",
            width=22.0,
            height=14.0,
            mass=35.0,
            friction=0.12,
            elasticity=0.25,
            color=(215, 205, 185),
            outline_color=(85, 75, 70),
            name="Knochen-Minenkarren",
            health=250.0,
            destructible=True,
        )

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        """Draw minecart with osteo ribs and wheel hubs."""
        super().draw(surface, cam_x, cam_y)
        if not self.alive:
            return

        sx = int(round(self.x - cam_x))
        sy = int(round(self.y - cam_y))
        angle = self.body.angle

        # Draw two small bone wheel hubs
        wheel_offset = 7.0
        w1_x = sx + int(-wheel_offset * math.cos(angle) - 5.0 * math.sin(angle))
        w1_y = sy + int(-wheel_offset * math.sin(angle) + 5.0 * math.cos(angle))
        w2_x = sx + int(wheel_offset * math.cos(angle) - 5.0 * math.sin(angle))
        w2_y = sy + int(wheel_offset * math.sin(angle) + 5.0 * math.cos(angle))

        pygame.draw.circle(surface, (90, 80, 75), (w1_x, w1_y), 3)
        pygame.draw.circle(surface, (90, 80, 75), (w2_x, w2_y), 3)


class ChitinShield(BioRigidBody):
    """Impenetrable movable chitin slab that players can push to block projectile fire."""

    def __init__(self, space: pymunk.Space, x: float, y: float):
        super().__init__(
            space=space,
            x=x,
            y=y,
            shape_type="box",
            width=8.0,
            height=28.0,
            mass=28.0,
            friction=0.92,
            elasticity=0.05,
            color=(55, 45, 65),
            outline_color=(90, 75, 105),
            name="Chitin-Schutzschild",
            health=220.0,
            destructible=True,
        )
