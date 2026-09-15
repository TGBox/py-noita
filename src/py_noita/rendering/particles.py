"""Visceral particle effects engine for Py-Noita."""

import math
from typing import List, Tuple
import pygame
import numpy as np

from py_noita.simulation.grid import SimulationGrid


class Particle:
    """A floating or physics-based visual particle."""
    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        color: Tuple[int, int, int],
        lifetime: int,
        size: float = 1.5,
        gravity: float = 0.15,
        drag: float = 0.98,
        glow: bool = False,
    ):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.max_lifetime = lifetime
        self.lifetime = lifetime
        self.size = size
        self.gravity = gravity
        self.drag = drag
        self.glow = glow

    def update(self, grid: SimulationGrid) -> bool:
        """Update particle position. Returns False if expired."""
        self.lifetime -= 1
        if self.lifetime <= 0:
            return False

        self.vy += self.gravity
        self.vx *= self.drag
        self.vy *= self.drag

        nx = self.x + self.vx
        ny = self.y + self.vy

        ix, iy = int(nx), int(ny)
        if 1 <= ix < grid.width - 1 and 1 <= iy < grid.height - 1:
            if grid.is_solid(ix, iy):
                # Bounce slightly or stop
                self.vx *= -0.3
                self.vy *= -0.3
            else:
                self.x = nx
                self.y = ny
        return True

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        """Draw particle to surface with alpha fade."""
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)

        if 0 <= sx < surface.get_width() and 0 <= sy < surface.get_height():
            alpha = max(0.2, self.lifetime / self.max_lifetime)
            fade_col = (
                int(self.color[0] * alpha),
                int(self.color[1] * alpha),
                int(self.color[2] * alpha),
            )
            int_size = max(1, int(round(self.size * alpha)))
            if int_size <= 1:
                surface.set_at((sx, sy), fade_col)
            else:
                pygame.draw.circle(surface, fade_col, (sx, sy), int_size)


class ParticleSystem:
    """Manages spawning, updating, and drawing active particles."""

    def __init__(self):
        self.particles: List[Particle] = []
        self.density: float = 1.0

    def spawn_blood_burst(self, x: float, y: float, count: int = 15) -> None:
        """Spawn visceral arterial blood spurts."""
        actual_count = max(1, int(count * self.density))
        for _ in range(actual_count):
            angle = np.random.uniform(0, 2 * math.pi)
            speed = np.random.uniform(1.0, 4.5)
            col = (
                np.random.randint(150, 220),
                np.random.randint(10, 30),
                np.random.randint(15, 35),
            )
            self.particles.append(
                Particle(
                    x, y,
                    math.cos(angle) * speed,
                    math.sin(angle) * speed - 1.0,
                    col,
                    lifetime=np.random.randint(25, 60),
                    size=np.random.uniform(1.0, 2.5),
                    gravity=0.22,
                )
            )

    def spawn_acid_sparks(self, x: float, y: float, count: int = 12) -> None:
        """Spawn neon acid bubbling droplets and sparks."""
        actual_count = max(1, int(count * self.density))
        for _ in range(actual_count):
            angle = np.random.uniform(0, 2 * math.pi)
            speed = np.random.uniform(0.8, 3.5)
            col = (
                np.random.randint(60, 100),
                np.random.randint(220, 255),
                np.random.randint(30, 70),
            )
            self.particles.append(
                Particle(
                    x, y,
                    math.cos(angle) * speed,
                    math.sin(angle) * speed - 0.8,
                    col,
                    lifetime=np.random.randint(20, 45),
                    size=np.random.uniform(1.0, 2.0),
                    gravity=0.18,
                    glow=True,
                )
            )

    def spawn_spore_puff(self, x: float, y: float, count: int = 10) -> None:
        """Spawn floating fungal spore cloud particles."""
        actual_count = max(1, int(count * self.density))
        for _ in range(actual_count):
            angle = np.random.uniform(0, 2 * math.pi)
            speed = np.random.uniform(0.3, 1.8)
            col = (
                np.random.randint(170, 205),
                np.random.randint(180, 220),
                np.random.randint(40, 70),
            )
            self.particles.append(
                Particle(
                    x, y,
                    math.cos(angle) * speed,
                    math.sin(angle) * speed - 0.4,
                    col,
                    lifetime=np.random.randint(40, 90),
                    size=np.random.uniform(1.2, 2.2),
                    gravity=0.03,  # Drifts gently
                    drag=0.95,
                )
            )

    def update(self, grid: SimulationGrid) -> None:
        """Step all particles and remove dead ones."""
        self.particles = [p for p in self.particles if p.update(grid)]

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        """Draw all living particles."""
        for p in self.particles:
            p.draw(surface, cam_x, cam_y)
