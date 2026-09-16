"""Py-Noita Bio-Sandbox / Testraum for weapon, gene, and material experimentation."""

import math
from typing import List, Optional, Tuple
import numpy as np

from py_noita.entities.enemy import Enemy
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import (
    MAT_ACID,
    MAT_AIR,
    MAT_ASH,
    MAT_BILE,
    MAT_BIOGAS,
    MAT_BLOOD,
    MAT_BONE,
    MAT_BONE_CHIP,
    MAT_CHITIN_SAND,
    MAT_FIBRIN_POWDER,
    MAT_FIRE,
    MAT_GOLD,
    MAT_LYMPH,
    MAT_MUTAGEN,
    MAT_NECRO_ASH,
    MAT_PUS,
    MAT_SPORES,
    MAT_SULFUR_SPORES,
    MAT_TISSUE,
    MAT_TOXIC_VAPOR,
    MAT_WALL_BONE,
    MAT_WATER,
)
from py_noita.world.generator import WorldPortal


class TestDummy(Enemy):
    """An indestructible fleshy training dummy that tracks damage taken."""

    def __init__(self, x: float, y: float):
        super().__init__(
            x=x,
            y=y,
            enemy_type="TEST_DUMMY",
            hp=99999.0,
            width=24,
            height=32,
            blood_mat=MAT_BLOOD,
            biomass_value=0,
        )
        self.total_damage_taken: float = 0.0
        self.last_hit_timer: float = 0.0
        self.dps_timer: float = 0.0
        self.dps_damage: float = 0.0
        self.current_dps: float = 0.0

    def take_damage(self, amount: float, source: str = "DAMAGE") -> None:
        self.total_damage_taken += amount
        self.dps_damage += amount
        self.last_hit_timer = 2.0
        self.hp = self.max_hp

    def update(self, player, grid, dt: float = 0.016):
        self.hp = self.max_hp
        self.vx = 0.0
        self.vy = 0.0

        if self.last_hit_timer > 0.0:
            self.last_hit_timer = max(0.0, self.last_hit_timer - dt)

        self.dps_timer += dt
        if self.dps_timer >= 1.0:
            self.current_dps = self.dps_damage / self.dps_timer
            self.dps_damage = 0.0
            self.dps_timer = 0.0
        return []

    def draw(self, surface, cam_x: int, cam_y: int) -> None:
        import pygame
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)

        # Fleshy training dummy graphic
        rect = pygame.Rect(sx, sy, self.width, self.height)
        pulse = 20 if self.last_hit_timer > 0 else 0
        pygame.draw.rect(surface, (180 + pulse, 60, 80), rect, border_radius=6)
        pygame.draw.rect(surface, (230, 200, 150), rect, 2, border_radius=6)

        # Target crosshair on dummy
        cx = sx + self.width // 2
        cy = sy + self.height // 2
        pygame.draw.circle(surface, (255, 230, 100), (cx, cy), 8, 1)
        pygame.draw.circle(surface, (255, 60, 60), (cx, cy), 3)

        font = pygame.font.SysFont("Arial", 9, bold=True)
        # Stats above dummy
        dps_surf = font.render(f"DPS: {self.current_dps:.1f}", True, (255, 225, 100))
        surface.blit(dps_surf, (cx - dps_surf.get_width() // 2, sy - 14))


def generate_sandbox_level(grid: SimulationGrid) -> Tuple[Tuple[float, float], WorldPortal, List[Enemy]]:
    """Build the clean testing laboratory arena with training dummies and material pools."""
    w = grid.width
    h = grid.height

    # Fill boundaries with indestructible bone
    grid.grid.fill(MAT_AIR)
    grid.life.fill(0)
    grid.init_boundaries()

    # Outer indestructible frame
    grid.fill_rect(0, 0, w, 20, MAT_WALL_BONE)
    grid.fill_rect(0, h - 30, w, 30, MAT_WALL_BONE)
    grid.fill_rect(0, 0, 20, h, MAT_WALL_BONE)
    grid.fill_rect(w - 20, 0, 20, h, MAT_WALL_BONE)

    # Main testing floor (y = 180)
    floor_y = 190
    grid.fill_rect(20, floor_y, w - 40, 14, MAT_WALL_BONE)

    # Upper observation & firing gantry (y = 110)
    grid.fill_rect(40, 110, 160, 8, MAT_WALL_BONE)
    grid.fill_rect(w - 200, 110, 160, 8, MAT_WALL_BONE)

    # Firing range target wall (destructible regenerable tissue on the right)
    target_wall_x = w - 120
    grid.fill_rect(target_wall_x, 40, 60, floor_y - 40, MAT_TISSUE)
    grid.fill_rect(target_wall_x + 60, 40, 20, floor_y - 40, MAT_BONE)

    # Material Testing Basins along the bottom level
    materials_to_sample = [
        (MAT_WATER, "Wasser"),
        (MAT_BLOOD, "Blut"),
        (MAT_ACID, "Säure"),
        (MAT_BILE, "Galle"),
        (MAT_MUTAGEN, "Mutagen"),
        (MAT_PUS, "Eiter"),
        (MAT_CHITIN_SAND, "Chitin"),
        (MAT_SULFUR_SPORES, "Schwefel"),
    ]

    basin_spacing = (w - 100) // max(1, len(materials_to_sample))
    for idx, (mat_id, name) in enumerate(materials_to_sample):
        bx = 50 + idx * basin_spacing
        by = floor_y - 12
        # Carve small basin
        grid.fill_rect(bx - 12, by, 24, 12, MAT_WALL_BONE)
        grid.fill_rect(bx - 9, by, 18, 9, mat_id)

    # Player spawn pos
    spawn_pos = (70.0, float(floor_y - 25))

    # Exit portal back to main menu or hub
    exit_portal = WorldPortal(45.0, float(floor_y - 15))

    # Spawn test dummies
    dummies: List[Enemy] = [
        TestDummy(target_wall_x - 50, floor_y - 32),
        TestDummy(target_wall_x - 110, floor_y - 32),
    ]

    return spawn_pos, exit_portal, dummies
