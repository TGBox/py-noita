"""Symbiote player character with flagella levitation, liquid glands, and bio-physics."""

import math
from typing import List, Optional, Tuple
import pygame
import numpy as np

from py_noita.config import (
    COLOR_ACID_GLOW,
    COLOR_PLAYER_GLOW,
    GRAVITY,
    PLAYER_HEIGHT,
    PLAYER_HOVER_IMPULSE,
    PLAYER_LEVITATION_DRAIN,
    PLAYER_LEVITATION_RECHARGE,
    PLAYER_MAX_HP,
    PLAYER_MAX_LEVITATION,
    PLAYER_MOVE_SPEED,
    PLAYER_WIDTH,
)
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import (
    MAT_ACID,
    MAT_AIR,
    MAT_BLOOD,
    MAT_FIRE,
    MAT_LYMPH,
    MAT_MUTAGEN,
    MAT_WATER,
    PROP_STATE,
    STATE_LIQUID,
    STATE_SOLID,
)


class LiquidGland:
    """An organic reservoir sac to suck up and spray liquids (equivalent to Noita flasks)."""
    def __init__(self, capacity: int = 150):
        self.capacity = capacity
        self.current_amount: int = 0
        self.material_id: int = MAT_AIR

    def absorb(self, mat_id: int) -> bool:
        """Absorb a liquid pixel into this gland."""
        if self.current_amount == 0:
            self.material_id = mat_id
            self.current_amount = 1
            return True
        elif self.material_id == mat_id and self.current_amount < self.capacity:
            self.current_amount += 1
            return True
        return False

    def discharge(self) -> Optional[int]:
        """Discharge one liquid pixel from this gland."""
        if self.current_amount > 0:
            self.current_amount -= 1
            mat = self.material_id
            if self.current_amount == 0:
                self.material_id = MAT_AIR
            return mat
        return None


class Player:
    """The living Symbiote parasite character."""

    def __init__(self, x: float, y: float):
        self.x: float = x
        self.y: float = y
        self.vx: float = 0.0
        self.vy: float = 0.0

        self.width: int = PLAYER_WIDTH
        self.height: int = PLAYER_HEIGHT

        # Vital stats
        self.max_hp: float = PLAYER_MAX_HP
        self.hp: float = PLAYER_MAX_HP
        self.max_levitation: float = PLAYER_MAX_LEVITATION
        self.levitation: float = PLAYER_MAX_LEVITATION
        self.is_levitating: bool = False
        self.on_ground: bool = False

        # Status effects
        self.on_fire: bool = False
        self.fire_timer: int = 0
        self.acid_burn_timer: int = 0
        self.blood_soaked_timer: int = 0

        # Organ-Glands (Flasks): 4 liquid sacs
        self.glands: List[LiquidGland] = [LiquidGland() for _ in range(4)]
        # Start gland 0 with a little restorative blood
        self.glands[0].material_id = MAT_BLOOD
        self.glands[0].current_amount = 50
        self.active_gland_index: int = 0

        # Active weapon index (0 to 3 for 4 cannulas)
        self.active_cannula_index: int = 0
        self.cannulas = []  # Populated with OrganCannula objects

        # Aiming
        self.aim_angle: float = 0.0
        self.aim_world_x: float = x
        self.aim_world_y: float = y

        # Flagella / Cilia animation phase
        self.anim_time: float = 0.0
        self.flagella_count: int = 6

        # Meta attributes
        self.biomass_currency: int = 0
        self.alive: bool = True

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2.0

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2.0

    def apply_input(self, move_x: float, hover: bool) -> None:
        """Apply horizontal movement and flagella levitation."""
        if not self.alive:
            return

        # Horizontal movement
        target_vx = move_x * PLAYER_MOVE_SPEED
        self.vx += (target_vx - self.vx) * 0.25

        # Hover / Levitation
        if hover and self.levitation > 0.0:
            self.vy -= PLAYER_HOVER_IMPULSE
            self.vy = max(self.vy, -3.2)  # Terminal upward velocity
            self.levitation = max(0.0, self.levitation - PLAYER_LEVITATION_DRAIN)
            self.is_levitating = True
        else:
            self.is_levitating = False

    def update_physics(self, grid: SimulationGrid, gravity_multiplier: float = 1.0) -> None:
        """Update symbiote motion, collisions with terrain, and fluid contacts."""
        if not self.alive:
            return

        self.anim_time += 0.15

        # Gravity scaled by biome conditions (e.g. low-gravity in infected lung)
        self.vy += GRAVITY * gravity_multiplier
        # Terminal downward speed
        self.vy = min(self.vy, 5.0 * gravity_multiplier)

        # 1. Horizontal movement & collision
        steps_x = int(math.ceil(abs(self.vx)))
        step_dx = self.vx / max(1, steps_x)
        for _ in range(steps_x):
            new_x = self.x + step_dx
            if self._collides(grid, new_x, self.y):
                self.vx = 0.0
                break
            self.x = new_x

        # 2. Vertical movement & collision
        steps_y = int(math.ceil(abs(self.vy)))
        step_dy = self.vy / max(1, steps_y)
        self.on_ground = False

        for _ in range(steps_y):
            new_y = self.y + step_dy
            if self._collides(grid, self.x, new_y):
                if self.vy > 0:
                    self.on_ground = True
                self.vy = 0.0
                break
            self.y = new_y

        # Levitation recovery on ground
        if self.on_ground:
            self.levitation = min(self.max_levitation, self.levitation + PLAYER_LEVITATION_RECHARGE)
        elif not self.is_levitating:
            # Slower recovery while free-falling
            self.levitation = min(self.max_levitation, self.levitation + PLAYER_LEVITATION_RECHARGE * 0.25)

        # 3. Environment & Liquid interactions
        self._check_environmental_hazards(grid)

    def _collides(self, grid: SimulationGrid, test_x: float, test_y: float) -> bool:
        """Check if bounding box intersects solid terrain."""
        x0 = int(test_x)
        x1 = int(test_x + self.width - 1)
        y0 = int(test_y)
        y1 = int(test_y + self.height - 1)

        for py in range(y0, y1 + 1):
            for px in range(x0, x1 + 1):
                if grid.is_solid(px, py):
                    return True
        return False

    def _check_environmental_hazards(self, grid: SimulationGrid) -> None:
        """Check contact with Acid, Blood, Fire, Water."""
        cx = int(self.center_x)
        cy = int(self.center_y)

        # Sample cells in body
        for dy in (-3, 0, 3):
            for dx in (-2, 0, 2):
                mat = grid.get_pixel(cx + dx, cy + dy)

                # Blood heals & recharges
                if mat == MAT_BLOOD:
                    self.hp = min(self.max_hp, self.hp + 0.15)
                    self.blood_soaked_timer = 90
                # Acid burns tissue
                elif mat == MAT_ACID:
                    self.take_damage(0.6, "ACID")
                    self.acid_burn_timer = 60
                # Fire ignites
                elif mat == MAT_FIRE:
                    self.on_fire = True
                    self.fire_timer = 120
                # Water or Lymph cleanses fire & acid
                elif mat in (MAT_WATER, MAT_LYMPH):
                    self.on_fire = False
                    self.fire_timer = 0
                    self.acid_burn_timer = 0

        # Status effect ticks
        if self.on_fire:
            self.fire_timer -= 1
            self.take_damage(0.2, "FIRE")
            if self.fire_timer <= 0:
                self.on_fire = False

        if self.acid_burn_timer > 0:
            self.acid_burn_timer -= 1
            self.take_damage(0.15, "ACID")

    def take_damage(self, amount: float, source: str = "DAMAGE") -> None:
        """Apply damage and check death."""
        self.hp -= amount
        if self.hp <= 0.0:
            self.hp = 0.0
            self.alive = False

    def heal(self, amount: float) -> None:
        """Heal player up to max_hp."""
        self.hp = min(self.max_hp, self.hp + amount)

    def suck_liquid(self, grid: SimulationGrid) -> bool:
        """Suck up liquid from around feet into active gland."""
        mat = grid.sample_and_consume_liquid(int(self.center_x), int(self.y + self.height), radius=5)
        if mat is not None:
            return self.glands[self.active_gland_index].absorb(mat)
        return False

    def spray_liquid(self, grid: SimulationGrid) -> Optional[int]:
        """Discharge a stream of liquid in aiming direction."""
        gland = self.glands[self.active_gland_index]
        mat = gland.discharge()
        if mat is not None:
            # Emit liquid in front of player
            dist = 10.0
            sx = int(self.center_x + math.cos(self.aim_angle) * dist)
            sy = int(self.center_y + math.sin(self.aim_angle) * dist)
            grid.set_pixel(sx, sy, mat)
            return mat
        return None

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        """Draw the living symbiote with animated waving flagella."""
        if not self.alive:
            return

        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)

        # 1. Draw waving flagella (cilia hairs behind the body)
        for i in range(self.flagella_count):
            fraction = (i + 1) / (self.flagella_count + 1)
            attach_y = sy + int(self.height * fraction)
            # Flagella wave oscillation
            wave = math.sin(self.anim_time * 2.0 + i * 1.2) * 3.5
            thrust = -4.0 if self.is_levitating else -1.5

            # Root and tip
            root_x = sx + (self.width if self.vx < -0.1 else 0)
            tip_x = root_x + (thrust if self.vx >= -0.1 else -thrust)
            tip_y = attach_y + int(wave) + (4 if self.is_levitating else 1)

            flagella_col = (130, 20, 40) if not self.on_fire else (255, 120, 20)
            pygame.draw.line(surface, flagella_col, (root_x, attach_y), (tip_x, tip_y), 1)

        # 2. Draw organic symbiote body (capsule / soft ellipsoid)
        body_col = (175, 30, 50)
        if self.acid_burn_timer > 0:
            body_col = (120, 190, 40)  # Greenish acid sizzle tint
        elif self.on_fire:
            body_col = (255, 140, 20)

        rect = pygame.Rect(sx, sy, self.width, self.height)
        pygame.draw.ellipse(surface, body_col, rect)

        # 3. Inner bioluminescent cell nucleus / eye
        core_col = (240, 210, 160)
        core_rect = pygame.Rect(sx + 2, sy + 3, self.width - 4, 4)
        pygame.draw.ellipse(surface, core_col, core_rect)

        # 4. Aim indicator needle / cannula tip
        aim_dist = 9.0
        tip_x = int(sx + self.width / 2.0 + math.cos(self.aim_angle) * aim_dist)
        tip_y = int(sy + self.height / 2.0 + math.sin(self.aim_angle) * aim_dist)
        cannula_col = (215, 200, 175)
        pygame.draw.line(surface, cannula_col, (sx + self.width // 2, sy + self.height // 2), (tip_x, tip_y), 2)
