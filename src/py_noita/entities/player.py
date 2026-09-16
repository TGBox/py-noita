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
from py_noita.rendering.ik import ProceduralTentacle
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import (
    MAT_ACID,
    MAT_AIR,
    MAT_BILE,
    MAT_BIOGAS,
    MAT_BLOOD,
    MAT_FIRE,
    MAT_GOLD,
    MAT_LYMPH,
    MAT_MUTAGEN,
    MAT_PUS,
    MAT_SPORES,
    MAT_SULFUR_SPORES,
    MAT_TOXIC_VAPOR,
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

    @property
    def max_amount(self) -> int:
        return self.capacity

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
        self.bile_slippery_timer: int = 0
        self.mutagen_frenzy_timer: int = 0
        self.spore_boost_timer: int = 0
        self.pus_sticky_timer: int = 0
        self.gas_exposure_timer: int = 0
        self.acid_immunity: bool = False

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

        # Procedural Gripping & Crawling Tentacles (FABRIK IK)
        self.tentacles: List[ProceduralTentacle] = [
            ProceduralTentacle(rel_root_x=-3.0, rel_root_y=3.0, preferred_angle=math.pi * 0.7, segment_lengths=[4.0, 4.0, 4.0, 3.0]),
            ProceduralTentacle(rel_root_x=3.0, rel_root_y=3.0, preferred_angle=math.pi * 0.3, segment_lengths=[4.0, 4.0, 4.0, 3.0]),
            ProceduralTentacle(rel_root_x=-4.0, rel_root_y=-1.0, preferred_angle=math.pi * 1.05, segment_lengths=[5.0, 4.0, 4.0, 3.0]),
            ProceduralTentacle(rel_root_x=4.0, rel_root_y=-1.0, preferred_angle=-math.pi * 0.05, segment_lengths=[5.0, 4.0, 4.0, 3.0]),
        ]

        # Extra sprouting mutation mini-tentacles (active during Mutagen / Spore frenzy)
        self.extra_tentacles: List[ProceduralTentacle] = [
            ProceduralTentacle(rel_root_x=-2.0, rel_root_y=-2.0, preferred_angle=math.pi * 1.3, segment_lengths=[3.0, 3.0, 2.0]),
            ProceduralTentacle(rel_root_x=2.0, rel_root_y=-2.0, preferred_angle=-math.pi * 0.3, segment_lengths=[3.0, 3.0, 2.0]),
            ProceduralTentacle(rel_root_x=0.0, rel_root_y=-3.0, preferred_angle=-math.pi * 0.5, segment_lengths=[3.5, 3.0, 2.5]),
        ]

        # Meta attributes
        self.biomass_currency: int = 0
        self.orbs_collected: int = 0
        self.discovered_tablets: List[int] = []
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

        # Speed scaling from Mutagen (+35%) and Pus (-35%)
        speed_mult = 1.0
        if self.mutagen_frenzy_timer > 0:
            speed_mult *= 1.35
        if self.pus_sticky_timer > 0:
            speed_mult *= 0.65

        # Horizontal movement (Bile drastically reduces friction damping)
        target_vx = move_x * PLAYER_MOVE_SPEED * speed_mult
        friction_lerp = 0.06 if self.bile_slippery_timer > 0 else 0.25
        self.vx += (target_vx - self.vx) * friction_lerp

        # Hover / Levitation (Spore booster gives stronger upward impulse)
        hover_impulse = PLAYER_HOVER_IMPULSE * (1.5 if self.spore_boost_timer > 0 else 1.25)
        max_upward = -4.8 if self.spore_boost_timer > 0 else -3.8
        if hover and self.levitation > 0.0:
            self.vy -= hover_impulse
            self.vy = max(self.vy, max_upward)  # Terminal upward velocity
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

        # 1. Horizontal movement & collision with step-up autostep (up to 3px for slopes/bumps)
        steps_x = int(math.ceil(abs(self.vx)))
        step_dx = self.vx / max(1, steps_x)
        MAX_STEP_UP = 3

        for _ in range(steps_x):
            new_x = self.x + step_dx
            if self._collides(grid, new_x, self.y):
                # Try stepping up 1, 2, or 3 pixels over obstacles and slopes
                stepped = False
                for step in range(1, MAX_STEP_UP + 1):
                    if not self._collides(grid, new_x, self.y - step):
                        self.y -= step
                        self.x = new_x
                        stepped = True
                        break
                if not stepped:
                    self.vx = 0.0
                    break
            else:
                # Downhill slope snap: if grounded and moving down a slope, snap down 1px smoothly
                if self.on_ground and not self.is_levitating and self.vy >= 0:
                    if not self._collides(grid, new_x, self.y + 1) and self._collides(grid, new_x, self.y + 2):
                        self.y += 1
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

        # Levitation recovery on ground (instant smooth walking without burning stamina)
        if self.on_ground:
            self.levitation = min(self.max_levitation, self.levitation + PLAYER_LEVITATION_RECHARGE)
        elif not self.is_levitating:
            # Active air recovery while gliding/free-falling
            self.levitation = min(self.max_levitation, self.levitation + PLAYER_LEVITATION_RECHARGE * 0.6)

        # 3. Update Procedural Gripping & Crawling Tentacles (IK)
        facing = 1.0 if self.vx >= -0.01 else -1.0
        for tentacle in self.tentacles:
            tentacle.update(self.center_x, self.center_y, grid, 0.016, self.vx, self.vy, facing)

        # Update extra sprouting mutation tentacles if active
        if self.mutagen_frenzy_timer > 0 or self.spore_boost_timer > 0:
            for extra in self.extra_tentacles:
                extra.update(self.center_x, self.center_y, grid, 0.025, self.vx, self.vy, facing)

        # 4. Environment & Liquid interactions
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
        """Check contact with Acid, Blood, Fire, Bile, Mutagen, Spores, Pus, Gas, and Water."""
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
                # Acid burns tissue (unless acid immune)
                elif mat == MAT_ACID:
                    if not self.acid_immunity:
                        self.take_damage(0.6, "ACID")
                        self.acid_burn_timer = 60
                # Fire ignites
                elif mat == MAT_FIRE:
                    self.on_fire = True
                    self.fire_timer = 120
                # Bile: slippery coating
                elif mat == MAT_BILE:
                    self.bile_slippery_timer = max(self.bile_slippery_timer, 150)
                # Mutagen: genetic frenzy
                elif mat == MAT_MUTAGEN:
                    self.mutagen_frenzy_timer = max(self.mutagen_frenzy_timer, 180)
                # Spores: flagella excitation booster
                elif mat in (MAT_SPORES, MAT_SULFUR_SPORES):
                    if self.spore_boost_timer == 0:
                        self.vy -= 0.6
                    self.spore_boost_timer = max(self.spore_boost_timer, 140)
                # Pus: viscous stickiness
                elif mat == MAT_PUS:
                    self.pus_sticky_timer = max(self.pus_sticky_timer, 150)
                # Toxic Vapor or Biogas: coughing exposure (unless acid/gas immune)
                elif mat in (MAT_TOXIC_VAPOR, MAT_BIOGAS):
                    if not self.acid_immunity:
                        self.gas_exposure_timer = min(180, self.gas_exposure_timer + 3)
                # Water or Lymph cleanses fire, acid, and coatings
                elif mat in (MAT_WATER, MAT_LYMPH):
                    self.on_fire = False
                    self.fire_timer = 0
                    self.acid_burn_timer = 0
                    self.bile_slippery_timer = 0
                    self.pus_sticky_timer = 0
                    self.gas_exposure_timer = 0
                # Biomass-Gold collection
                elif mat == MAT_GOLD:
                    self.biomass_currency += 1
                    grid.set_pixel(cx + dx, cy + dy, MAT_AIR)

        # Status effect ticks
        if self.on_fire:
            self.fire_timer -= 1
            self.take_damage(0.2, "FIRE")
            if self.fire_timer <= 0:
                self.on_fire = False

        if self.acid_burn_timer > 0:
            if self.acid_immunity:
                self.acid_burn_timer = 0
            else:
                self.acid_burn_timer -= 1
                self.take_damage(0.15, "ACID")

        if self.bile_slippery_timer > 0:
            self.bile_slippery_timer -= 1

        if self.mutagen_frenzy_timer > 0:
            self.mutagen_frenzy_timer -= 1

        if self.spore_boost_timer > 0:
            self.spore_boost_timer -= 1

        if self.pus_sticky_timer > 0:
            self.pus_sticky_timer -= 1

        if self.gas_exposure_timer > 0:
            if self.acid_immunity:
                self.gas_exposure_timer = 0
            else:
                if self.gas_exposure_timer >= 40 and (self.gas_exposure_timer % 20 == 0):
                    self.take_damage(0.25, "GAS")
                    self.vx += float(np.random.uniform(-0.4, 0.4))
                self.gas_exposure_timer -= 1

    def take_damage(self, amount: float, source: str = "DAMAGE") -> None:
        """Apply damage and check death."""
        # Acid & Toxic Gas immunity nullifies corrosive and gas damage
        if self.acid_immunity and source in ("ACID", "GAS", "TOXIC"):
            return

        # Pus grants +20% physical blunt resistance
        if self.pus_sticky_timer > 0 and source in ("DAMAGE", "IMPACT", "ENEMY"):
            amount *= 0.8
        # Bile coating increases fire vulnerability
        if self.bile_slippery_timer > 0 and source == "FIRE":
            amount *= 1.5

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
        """Draw the living symbiote with procedural gripping tentacles, flagella, and status visual mutations."""
        if not self.alive:
            return

        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)

        # Mutagen pulsing aura
        if self.mutagen_frenzy_timer > 0:
            glow_pulse = (math.sin(self.anim_time * 6.0) + 1.0) * 0.5
            gr = int(self.width * 1.5 + glow_pulse * 4)
            glow_s = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_s, (210, 40, 230, int(50 + glow_pulse * 40)), (gr, gr), gr)
            surface.blit(glow_s, (sx + self.width // 2 - gr, sy + self.height // 2 - gr))

        # 1. Draw procedural gripping / crawling tentacles (FABRIK IK)
        tentacle_col = (140, 22, 38) if not self.on_fire else (255, 120, 20)
        sucker_col = (210, 50, 75) if not self.on_fire else (255, 200, 50)
        for tentacle in self.tentacles:
            tentacle.draw(surface, cam_x, cam_y, tentacle_col, sucker_col)

        # 1b. Extra sprouting mutation mini-tentacles (Mutagen or Spore frenzy)
        if self.mutagen_frenzy_timer > 0 or self.spore_boost_timer > 0:
            m_tentacle_col = (220, 40, 240) if self.mutagen_frenzy_timer > 0 else (210, 240, 50)
            m_sucker_col = (255, 120, 255) if self.mutagen_frenzy_timer > 0 else (240, 255, 140)
            for extra in self.extra_tentacles:
                extra.draw(surface, cam_x, cam_y, m_tentacle_col, m_sucker_col)

        # 2. Draw waving flagella (cilia hairs behind the body)
        flagella_col = (130, 20, 40)
        if self.on_fire:
            flagella_col = (255, 120, 20)
        elif self.spore_boost_timer > 0:
            flagella_col = (215, 240, 60)
        elif self.pus_sticky_timer > 0:
            flagella_col = (190, 185, 95)

        for i in range(self.flagella_count):
            fraction = (i + 1) / (self.flagella_count + 1)
            attach_y = sy + int(self.height * fraction)
            # Flagella wave oscillation (clamped if pus makes it sticky)
            wave_scale = 1.0 if self.pus_sticky_timer > 0 else 3.5
            wave = math.sin(self.anim_time * 2.0 + i * 1.2) * wave_scale
            thrust = -4.0 if self.is_levitating else -1.5

            # Root and tip
            root_x = sx + (self.width if self.vx < -0.1 else 0)
            tip_x = root_x + (thrust if self.vx >= -0.1 else -thrust)
            tip_y = attach_y + int(wave) + (4 if self.is_levitating else 1)

            line_w = 2 if self.pus_sticky_timer > 0 else 1
            pygame.draw.line(surface, flagella_col, (root_x, attach_y), (tip_x, tip_y), line_w)

        # 3. Draw organic symbiote body (capsule / soft ellipsoid)
        body_col = (175, 30, 50)
        if self.acid_burn_timer > 0:
            body_col = (120, 190, 40)  # Greenish acid sizzle tint
        elif self.on_fire:
            body_col = (255, 140, 20)
        elif self.mutagen_frenzy_timer > 0:
            body_col = (215, 35, 230)  # Mutagen hyper-magenta
        elif self.pus_sticky_timer > 0:
            body_col = (210, 205, 110)  # Pus sticky yellow
        elif self.bile_slippery_timer > 0:
            body_col = (185, 180, 40)   # Bile oily greenish-amber

        rect = pygame.Rect(sx, sy, self.width, self.height)
        pygame.draw.ellipse(surface, body_col, rect)

        # 4. Inner bioluminescent cell nucleus / eye
        core_col = (240, 210, 160)
        core_rect = pygame.Rect(sx + 2, sy + 3, self.width - 4, 4)
        pygame.draw.ellipse(surface, core_col, core_rect)

        # 5. Aim indicator needle / cannula tip
        aim_dist = 9.0
        tip_x = int(sx + self.width / 2.0 + math.cos(self.aim_angle) * aim_dist)
        tip_y = int(sy + self.height / 2.0 + math.sin(self.aim_angle) * aim_dist)
        cannula_col = (215, 200, 175)
        pygame.draw.line(surface, cannula_col, (sx + self.width // 2, sy + self.height // 2), (tip_x, tip_y), 2)
