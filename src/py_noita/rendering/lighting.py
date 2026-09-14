"""Bioluminescent dynamic lighting engine for Py-Noita."""

import math
from typing import List, Tuple
import pygame
import numpy as np

from py_noita.config import (
    COLOR_ACID_GLOW,
    COLOR_BIOGAS_GLOW,
    COLOR_MUTAGEN_GLOW,
    COLOR_NERVE_GLOW,
    COLOR_PLAYER_GLOW,
)
from py_noita.simulation.materials import (
    MAT_ACID,
    MAT_BIOGAS,
    MAT_FIRE,
    MAT_MUTAGEN,
    MAT_NERVE,
    PROP_GLOW,
)


class LightSource:
    """A point light source with position, radius, color, and intensity."""
    def __init__(
        self,
        world_x: float,
        world_y: float,
        radius: float,
        color: Tuple[int, int, int],
        intensity: float = 1.0,
    ):
        self.world_x = world_x
        self.world_y = world_y
        self.radius = radius
        self.color = color
        self.intensity = intensity


class LightingEngine:
    """Renders dark cavern darkness with dynamic bioluminescent light sources."""

    def __init__(self, view_width: int, view_height: int):
        self.view_width = view_width
        self.view_height = view_height
        self.ambient_darkness = (24, 18, 30)  # Atmospheric dark visceral purple

        # Lightmap surface for additive/multiplicative lighting pass
        self.light_surface = pygame.Surface((view_width, view_height))
        # Precomputed circular gradient light textures
        self._light_cache = {}

    def resize(self, view_width: int, view_height: int) -> None:
        """Resize lighting surface when resolution changes."""
        self.view_width = view_width
        self.view_height = view_height
        self.light_surface = pygame.Surface((view_width, view_height))

    def _get_radial_light(self, radius: int, color: Tuple[int, int, int], intensity: float) -> pygame.Surface:
        """Get or create cached radial light gradient texture."""
        key = (radius, color, int(intensity * 10))
        if key in self._light_cache:
            return self._light_cache[key]

        diameter = radius * 2
        surf = pygame.Surface((diameter, diameter), pygame.SRCALPHA)

        # Draw concentric alpha rings
        for r in range(radius, 0, -2):
            t = 1.0 - (r / radius)
            alpha = int(255 * intensity * (t * t))
            alpha = min(255, max(0, alpha))
            col = (color[0], color[1], color[2], alpha)
            pygame.draw.circle(surf, col, (radius, radius), r)

        self._light_cache[key] = surf
        # Prevent cache bloat
        if len(self._light_cache) > 200:
            self._light_cache.clear()
        return surf

    def render(
        self,
        dest_surface: pygame.Surface,
        cam_x: int,
        cam_y: int,
        lights: List[LightSource],
        grid_grid: np.ndarray,
    ) -> None:
        """Draw dynamic bioluminescence and darkness onto dest_surface."""
        # 1. Fill light surface with ambient cavern color
        self.light_surface.fill(self.ambient_darkness)

        # 2. Sample bright glowing grid cells (stride 4 for fast sampling)
        step = 5
        y_max = min(grid_grid.shape[0] - 1, cam_y + self.view_height)
        x_max = min(grid_grid.shape[1] - 1, cam_x + self.view_width)

        for gy in range(cam_y, y_max, step):
            sy = gy - cam_y
            for gx in range(cam_x, x_max, step):
                mat = grid_grid[gy, gx]
                glow = PROP_GLOW[mat]
                if glow > 100:
                    sx = gx - cam_x
                    if mat == MAT_ACID:
                        col = COLOR_ACID_GLOW
                    elif mat == MAT_FIRE:
                        col = COLOR_BIOGAS_GLOW
                    elif mat == MAT_MUTAGEN:
                        col = COLOR_MUTAGEN_GLOW
                    elif mat == MAT_NERVE:
                        col = COLOR_NERVE_GLOW
                    else:
                        col = (200, 200, 200)

                    rad = int(glow * 0.12)
                    light_tex = self._get_radial_light(rad, col, 0.45)
                    self.light_surface.blit(
                        light_tex,
                        (sx - rad, sy - rad),
                        special_flags=pygame.BLEND_ADD,
                    )

        # 3. Blit entity lights (Player bioluminescence, projectiles, explosions)
        for light in lights:
            sx = int(light.world_x - cam_x)
            sy = int(light.world_y - cam_y)
            rad = int(light.radius)

            # Viewport culling
            if -rad <= sx <= self.view_width + rad and -rad <= sy <= self.view_height + rad:
                light_tex = self._get_radial_light(rad, light.color, light.intensity)
                self.light_surface.blit(
                    light_tex,
                    (sx - rad, sy - rad),
                    special_flags=pygame.BLEND_ADD,
                )

        # 4. Multiply lighting onto target world surface
        dest_surface.blit(self.light_surface, (0, 0), special_flags=pygame.BLEND_MULT)
