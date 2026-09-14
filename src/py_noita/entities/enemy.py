"""Immune defense cells and rival parasite enemies."""

import math
from typing import List, Optional, Tuple
import pygame
import numpy as np

from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import (
    MAT_ACID,
    MAT_AIR,
    MAT_BLOOD,
    MAT_LYMPH,
    MAT_MUTAGEN,
    MAT_PUS,
    MAT_SPORES,
    MAT_TISSUE,
)
from py_noita.weapons.projectile import Projectile


ENEMY_NAMES = {
    "MACROPHAGE": "Makrophage",
    "ANTIBODY": "Antikörper",
    "GRANULOCYTE": "Granulozyt",
    "FLESH_WORM": "Fleischwurm",
    "TUMOR_CYST": "Tumorzyste",
    "CHITIN_BEETLE": "Chitin-Käfer",
    "SPORE_POD": "Sporen-Kapsel",
    "SYNAPTIC_SENTRY": "Synapsen-Wächter",
}


class Enemy:
    """Base class for immune defense cells and parasites."""

    def __init__(
        self,
        x: float,
        y: float,
        enemy_type: str,
        hp: float,
        width: int,
        height: int,
        blood_mat: int = MAT_BLOOD,
        biomass_value: int = 15,
    ):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.enemy_type = enemy_type
        self.max_hp = hp
        self.hp = hp
        self.width = width
        self.height = height
        self.blood_mat = blood_mat
        self.biomass_value = biomass_value

        self.alive: bool = True
        self.anim_time: float = np.random.uniform(0.0, 10.0)
        self.attack_cooldown: float = np.random.uniform(0.5, 2.0)
        self.bleed_buffer: int = 0

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2.0

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2.0

    @property
    def display_name(self) -> str:
        return ENEMY_NAMES.get(self.enemy_type, self.enemy_type.replace("_", " ").title())

    def contains_point(self, wx: float, wy: float, pad: float = 3.0) -> bool:
        """Check if world coordinates fall within enemy hitbox."""
        if not self.alive:
            return False
        return (
            self.x - pad <= wx <= self.x + self.width + pad
            and self.y - pad <= wy <= self.y + self.height + pad
        )

    def take_damage(self, amount: float, source: str = "DAMAGE") -> None:
        """Apply damage and queue blood bleeding particles."""
        self.hp -= amount
        self.bleed_buffer += int(min(20, amount * 0.8))
        if self.hp <= 0.0:
            self.hp = 0.0
            self.alive = False

    def update_physics(self, grid: SimulationGrid) -> None:
        """Step simple gravity and terrain collisions."""
        # Bleed damaged fluid into grid
        if self.bleed_buffer > 0:
            self.bleed_buffer -= 1
            bx = int(self.center_x + np.random.randint(-self.width // 2, self.width // 2 + 1))
            by = int(self.center_y + np.random.randint(-self.height // 2, self.height // 2 + 1))
            if 1 <= bx < grid.width - 1 and 1 <= by < grid.height - 1:
                if grid.is_empty(bx, by):
                    grid.set_pixel(bx, by, self.blood_mat)

        if not self.alive:
            return

        self.anim_time += 0.1

        # Check acid hazard contact
        cx, cy = int(self.center_x), int(self.center_y)
        if grid.get_pixel(cx, cy) == MAT_ACID and self.blood_mat != MAT_ACID:
            self.take_damage(0.4, "ACID")

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        """Render enemy shape and status."""
        pass


class Macrophage(Enemy):
    """Large amoeboid engulfing cell that crawls along ground and walls."""

    def __init__(self, x: float, y: float):
        super().__init__(x, y, "MACROPHAGE", hp=45.0, width=16, height=14, blood_mat=MAT_PUS, biomass_value=20)
        self.wobble_phase = np.random.uniform(0, math.pi * 2)

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        if not self.alive:
            return
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)

        # Pulsating amoeba shape
        wobble_x = int(math.sin(self.anim_time * 1.5) * 2.0)
        wobble_y = int(math.cos(self.anim_time * 1.5) * 2.0)

        rect = pygame.Rect(sx - wobble_x // 2, sy - wobble_y // 2, self.width + wobble_x, self.height + wobble_y)
        pygame.draw.ellipse(surface, (190, 185, 110), rect)
        # Inner vacuoles
        pygame.draw.circle(surface, (150, 140, 75), (sx + self.width // 2, sy + self.height // 2), 4)


class Antibody(Enemy):
    """Agile flying hunter that fires cytokine darts."""

    def __init__(self, x: float, y: float):
        super().__init__(x, y, "ANTIBODY", hp=22.0, width=10, height=10, blood_mat=MAT_LYMPH, biomass_value=15)

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        if not self.alive:
            return
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)

        # Y-shaped antibody structure
        cx = sx + self.width // 2
        cy = sy + self.height // 2
        col = (225, 235, 240)

        # Draw classic Y protein antibody
        pygame.draw.line(surface, col, (cx, cy + 4), (cx, cy - 1), 2)
        pygame.draw.line(surface, col, (cx, cy - 1), (cx - 4, cy - 5), 2)
        pygame.draw.line(surface, col, (cx, cy - 1), (cx + 4, cy - 5), 2)


class Granulocyte(Enemy):
    """Armored tank cell that spews continuous streams of digestive acid."""

    def __init__(self, x: float, y: float):
        super().__init__(x, y, "GRANULOCYTE", hp=85.0, width=20, height=18, blood_mat=MAT_ACID, biomass_value=40)

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        if not self.alive:
            return
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)

        # Heavy segmented chitin body
        rect = pygame.Rect(sx, sy, self.width, self.height)
        pygame.draw.ellipse(surface, (50, 42, 60), rect)
        # Acid nozzle gland
        pygame.draw.circle(surface, (70, 255, 30), (sx + self.width // 2, sy + self.height // 2), 5)


class WormSegment:
    """A body segment of the burrowing flesh worm."""
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y


class FleshWorm(Enemy):
    """Segmented burrowing worm that eats tunnels through tissue terrain."""

    def __init__(self, x: float, y: float, num_segments: int = 8):
        super().__init__(x, y, "FLESH_WORM", hp=110.0, width=14, height=14, blood_mat=MAT_BLOOD, biomass_value=60)
        self.segments: List[WormSegment] = [WormSegment(x - i * 8, y) for i in range(num_segments)]
        self.target_angle: float = 0.0

    def contains_point(self, wx: float, wy: float, pad: float = 3.0) -> bool:
        """Check if world coordinates fall within head or any segment."""
        if not self.alive:
            return False
        if super().contains_point(wx, wy, pad):
            return True
        for seg in self.segments:
            if math.hypot(wx - seg.x, wy - seg.y) <= (7.0 + pad):
                return True
        return False

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        if not self.alive:
            return

        # Draw segments from tail to head
        for i in range(len(self.segments) - 1, -1, -1):
            seg = self.segments[i]
            sx = int(seg.x - cam_x)
            sy = int(seg.y - cam_y)
            rad = max(3, 7 - i // 2)
            col = (150, 25, 38) if i > 0 else (210, 40, 55)
            pygame.draw.circle(surface, col, (sx, sy), rad)
            if i == 0:
                # Teeth on head
                pygame.draw.circle(surface, (230, 220, 190), (sx, sy), 3)


class TumorCyst(Enemy):
    """Stationary pulsating spawner."""

    def __init__(self, x: float, y: float):
        super().__init__(x, y, "TUMOR_CYST", hp=140.0, width=24, height=24, blood_mat=MAT_MUTAGEN, biomass_value=80)
        self.spawn_timer: float = 6.0

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        if not self.alive:
            return
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)

        pulse = math.sin(self.anim_time * 2.0) * 2.0
        rect = pygame.Rect(sx - int(pulse // 2), sy - int(pulse // 2), int(self.width + pulse), int(self.height + pulse))
        pygame.draw.ellipse(surface, (140, 20, 100), rect)
        pygame.draw.circle(surface, (210, 40, 240), (sx + self.width // 2, sy + self.height // 2), 6)


class ChitinBeetle(Enemy):
    """Heavily armored scuttler with chitin plates that reduce incoming damage."""

    def __init__(self, x: float, y: float):
        super().__init__(x, y, "CHITIN_BEETLE", hp=70.0, width=16, height=12, blood_mat=MAT_PUS, biomass_value=35)
        self.facing_dir: float = 1.0
        self.is_charging: bool = False
        self.charge_timer: float = 0.0

    def take_damage(self, amount: float, source: str = "DAMAGE") -> None:
        # Chitin exoskeleton absorbs 40% of standard damage
        reduced = amount * 0.6
        super().take_damage(reduced, source)

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        if not self.alive:
            return
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)

        rect = pygame.Rect(sx, sy, self.width, self.height)
        pygame.draw.ellipse(surface, (55, 45, 65), rect)
        pygame.draw.ellipse(surface, (85, 70, 100), rect, 1)

        eye_x = sx + self.width - 3 if self.facing_dir > 0 else sx + 3
        pygame.draw.circle(surface, (255, 180, 40), (eye_x, sy + 4), 2)

        mand_x = sx + self.width + 2 if self.facing_dir > 0 else sx - 2
        pygame.draw.line(surface, (210, 200, 180), (eye_x, sy + 7), (mand_x, sy + 9), 2)


class SporePod(Enemy):
    """Floating organic spore sac drifting in low-gravity chambers."""

    def __init__(self, x: float, y: float):
        super().__init__(x, y, "SPORE_POD", hp=35.0, width=14, height=14, blood_mat=MAT_SPORES, biomass_value=25)
        self.float_phase: float = np.random.uniform(0, math.pi * 2)

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        if not self.alive:
            return
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)

        pulse = math.sin(self.anim_time * 2.5) * 1.5
        rect = pygame.Rect(sx - int(pulse // 2), sy - int(pulse // 2), int(self.width + pulse), int(self.height + pulse))
        pygame.draw.ellipse(surface, (150, 180, 40), rect)
        pygame.draw.circle(surface, (210, 230, 60), (sx + self.width // 2, sy + 4), 2)
        pygame.draw.circle(surface, (110, 140, 25), (sx + 4, sy + self.height - 4), 2)
        pygame.draw.circle(surface, (110, 140, 25), (sx + self.width - 4, sy + self.height - 4), 2)


class SynapticSentry(Enemy):
    """Hovering neural guardian emitting bio-electric synapse discharges."""

    def __init__(self, x: float, y: float):
        super().__init__(x, y, "SYNAPTIC_SENTRY", hp=55.0, width=14, height=14, blood_mat=MAT_MUTAGEN, biomass_value=50)
        self.teleport_cooldown: float = np.random.uniform(3.0, 5.0)

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        if not self.alive:
            return
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)

        cx = sx + self.width // 2
        cy = sy + self.height // 2
        glow_rad = int(7 + math.sin(self.anim_time * 4.0) * 2)
        pygame.draw.circle(surface, (30, 160, 220), (cx, cy), glow_rad, 1)
        pygame.draw.circle(surface, (60, 220, 255), (cx, cy), 5)
        pygame.draw.circle(surface, (220, 250, 255), (cx, cy), 2)

        for angle_offset in (0.0, 1.57, 3.14, 4.71):
            ax = cx + int(math.cos(self.anim_time + angle_offset) * 8)
            ay = cy + int(math.sin(self.anim_time + angle_offset) * 8)
            pygame.draw.line(surface, (100, 240, 255), (cx, cy), (ax, ay), 1)


def create_enemy(etype: str, x: float, y: float) -> Enemy:
    """Factory method to instantiate enemies."""
    if etype == "MACROPHAGE":
        return Macrophage(x, y)
    elif etype == "ANTIBODY":
        return Antibody(x, y)
    elif etype == "GRANULOCYTE":
        return Granulocyte(x, y)
    elif etype == "FLESH_WORM":
        return FleshWorm(x, y)
    elif etype == "TUMOR_CYST":
        return TumorCyst(x, y)
    elif etype == "CHITIN_BEETLE":
        return ChitinBeetle(x, y)
    elif etype == "SPORE_POD":
        return SporePod(x, y)
    elif etype == "SYNAPTIC_SENTRY":
        return SynapticSentry(x, y)
    return Macrophage(x, y)
