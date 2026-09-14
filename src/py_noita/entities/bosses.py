"""Secret optional Bio-Bosse: Der Riesen-Helminth, Die Ur-Fresszelle, and Der Synaptische Parasit."""

import math
import random
from typing import List, Optional, Tuple
import pygame
import numpy as np

from py_noita.entities.enemy import Antibody, Enemy, Macrophage, WormSegment
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import (
    MAT_ACID,
    MAT_AIR,
    MAT_BILE,
    MAT_BLOOD,
    MAT_MUTAGEN,
    MAT_PUS,
)
from py_noita.weapons.projectile import Projectile


class GiantHelminth(Enemy):
    """Secret Boss 1: Gigantischer 30-Segment-Fleischwurm im Knochen-Labyrinth."""

    def __init__(self, x: float, y: float):
        super().__init__(
            x, y,
            enemy_type="GIANT_HELMINTH",
            hp=650.0,
            width=26,
            height=26,
            blood_mat=MAT_BLOOD,
            biomass_value=250,
        )
        self.segments: List[WormSegment] = [WormSegment(x - i * 10, y) for i in range(30)]
        self.target_angle: float = 0.0
        self.spit_cooldown: float = 2.0
        self.boss_title = "DER RIESEN-HELMINTH // UR-PARASIT"

    def contains_point(self, wx: float, wy: float, pad: float = 5.0) -> bool:
        if not self.alive:
            return False
        if super().contains_point(wx, wy, pad):
            return True
        for seg in self.segments:
            if math.hypot(wx - seg.x, wy - seg.y) <= (11.0 + pad):
                return True
        return False

    def update_boss(
        self,
        player,
        grid: SimulationGrid,
        dt: float,
    ) -> Tuple[List[Projectile], List[Enemy]]:
        """Tunnel through terrain and hunt player relentlessly."""
        if not self.alive or not player.alive:
            return [], []

        spawned_projs: List[Projectile] = []
        dx = player.center_x - self.center_x
        dy = player.center_y - self.center_y
        dist = math.hypot(dx, dy)

        # Steer head
        target_angle = math.atan2(dy, dx)
        cur_angle = self.target_angle
        angle_diff = (target_angle - cur_angle + math.pi) % (2 * math.pi) - math.pi
        self.target_angle += max(-0.06, min(0.06, angle_diff))

        speed = 2.8 if self.hp > 300 else 3.6  # Enraged when low HP
        self.vx = math.cos(self.target_angle) * speed
        self.vy = math.sin(self.target_angle) * speed
        self.x += self.vx
        self.y += self.vy

        # Massive head carves wide tunnel through terrain!
        hx = int(self.center_x)
        hy = int(self.center_y)
        grid.carve_circle(hx, hy, radius=12, fill_mat=MAT_AIR)

        # Update 30 segments
        if self.segments:
            self.segments[0].x = self.x
            self.segments[0].y = self.y
            for i in range(1, len(self.segments)):
                lead = self.segments[i - 1]
                seg = self.segments[i]
                sdx = lead.x - seg.x
                sdy = lead.y - seg.y
                sdist = math.hypot(sdx, sdy)
                if sdist > 8.0:
                    seg.x += (sdx / sdist) * (sdist - 8.0)
                    seg.y += (sdy / sdist) * (sdist - 8.0)

        # Massive contact damage
        if dist < 22.0:
            player.take_damage(1.8, "HELMINTH_MANDIBLE")

        # Ranged bone-spike burst
        self.spit_cooldown -= dt
        if self.spit_cooldown <= 0.0 and dist < 320:
            self.spit_cooldown = random.uniform(2.5, 4.0)
            for spread_ang in (-0.3, -0.15, 0.0, 0.15, 0.3):
                ang = self.target_angle + spread_ang
                p = Projectile(
                    x=self.center_x,
                    y=self.center_y,
                    vx=math.cos(ang) * 5.0,
                    vy=math.sin(ang) * 5.0,
                    damage=15.0,
                    lifetime=90,
                    radius=3.0,
                    color=(240, 230, 200),
                    owner="ENEMY",
                )
                spawned_projs.append(p)

        return spawned_projs, []

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        if not self.alive:
            return

        for i in range(len(self.segments) - 1, -1, -1):
            seg = self.segments[i]
            sx = int(seg.x - cam_x)
            sy = int(seg.y - cam_y)
            rad = max(4, 12 - (i // 3))
            col = (130, 20, 32) if i > 0 else (220, 30, 50)
            pygame.draw.circle(surface, col, (sx, sy), rad)
            if i % 3 == 0:
                # Segment chitin ridges
                pygame.draw.circle(surface, (190, 180, 150), (sx, sy), rad, 1)

            if i == 0:
                # Colossal mandibles on head
                pygame.draw.circle(surface, (255, 240, 210), (sx - 4, sy - 4), 3)
                pygame.draw.circle(surface, (255, 240, 210), (sx + 4, sy - 4), 3)


class PrimordialPhagocyte(Enemy):
    """Secret Boss 2: Kolossaler Amöben-Titan in der Gallen-Lagune."""

    def __init__(self, x: float, y: float):
        super().__init__(
            x, y,
            enemy_type="PRIMORDIAL_PHAGOCYTE",
            hp=520.0,
            width=36,
            height=36,
            blood_mat=MAT_BILE,
            biomass_value=220,
        )
        self.attack_timer: float = 2.0
        self.bud_timer: float = 6.0
        self.boss_title = "DIE UR-FRESSZELLE // AMÖBEN-TITAN"

    def update_boss(
        self,
        player,
        grid: SimulationGrid,
        dt: float,
    ) -> Tuple[List[Projectile], List[Enemy]]:
        if not self.alive or not player.alive:
            return [], []

        spawned_projs: List[Projectile] = []
        spawned_minions: List[Enemy] = []

        dx = player.center_x - self.center_x
        dy = player.center_y - self.center_y
        dist = math.hypot(dx, dy)

        # Slow inexorable amoeboid crawl
        if dist < 320:
            move_dir = 1.0 if dx > 0 else -1.0
            self.vx += (move_dir * 0.9 - self.vx) * 0.1

        self.vy += 0.22
        self.vy = min(self.vy, 3.5)
        self.x += self.vx
        self.y += self.vy

        # Melee engulfment
        if dist < (self.width + player.width) / 2.0:
            player.take_damage(1.4, "TITAN_ENGULFMENT")

        # Bile spray wave
        self.attack_timer -= dt
        if self.attack_timer <= 0.0 and dist < 260:
            self.attack_timer = random.uniform(3.0, 4.5)
            for i in range(8):
                ang = (i / 8.0) * math.pi * 2.0
                p = Projectile(
                    x=self.center_x,
                    y=self.center_y,
                    vx=math.cos(ang) * 4.2,
                    vy=math.sin(ang) * 4.2,
                    damage=14.0,
                    lifetime=80,
                    radius=3.5,
                    color=(160, 220, 20),
                    owner="ENEMY",
                )
                spawned_projs.append(p)

        # Spawns / buds micro-macrophage cells
        self.bud_timer -= dt
        if self.bud_timer <= 0.0 and dist < 300:
            self.bud_timer = random.uniform(7.0, 10.0)
            spawned_minions.append(Macrophage(self.center_x - 14, self.center_y - 10))

        return spawned_projs, spawned_minions

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        if not self.alive:
            return
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)

        # Pulsating giant amoeba
        pulse = math.sin(self.anim_time * 2.0) * 3.5
        rect = pygame.Rect(sx - int(pulse // 2), sy - int(pulse // 2), int(self.width + pulse), int(self.height + pulse))
        pygame.draw.ellipse(surface, (170, 185, 30), rect)
        pygame.draw.ellipse(surface, (210, 230, 70), rect, 2)
        # Giant nucleolus
        pygame.draw.circle(surface, (90, 120, 15), (sx + self.width // 2, sy + self.height // 2), 10)


class SynapticParasite(Enemy):
    """Secret Boss 3: Teleportierender Neuro-Wächter in der Wirbelsäule."""

    def __init__(self, x: float, y: float):
        super().__init__(
            x, y,
            enemy_type="SYNAPTIC_PARASITE",
            hp=420.0,
            width=22,
            height=22,
            blood_mat=MAT_MUTAGEN,
            biomass_value=200,
        )
        self.teleport_timer: float = 3.5
        self.attack_timer: float = 1.6
        self.boss_title = "DER SYNAPTISCHE PARASIT // NEURO-WÄCHTER"

    def update_boss(
        self,
        player,
        grid: SimulationGrid,
        dt: float,
    ) -> Tuple[List[Projectile], List[Enemy]]:
        if not self.alive or not player.alive:
            return [], []

        spawned_projs: List[Projectile] = []
        dx = player.center_x - self.center_x
        dy = player.center_y - self.center_y
        dist = math.hypot(dx, dy)

        # Hover around player
        desired_dist = 140.0
        tx = player.center_x - (dx / max(1.0, dist)) * desired_dist
        ty = player.center_y - (dy / max(1.0, dist)) * desired_dist
        self.vx += ((tx - self.center_x) * 0.08 - self.vx) * 0.2
        self.vy += ((ty - self.center_y) * 0.08 - self.vy) * 0.2
        self.x += self.vx
        self.y += self.vy

        # Teleport blink
        self.teleport_timer -= dt
        if self.teleport_timer <= 0.0:
            self.teleport_timer = random.uniform(3.0, 4.5)
            ang = random.uniform(0, math.pi * 2)
            self.x = player.center_x + math.cos(ang) * 120.0
            self.y = player.center_y + math.sin(ang) * 120.0

        # Spiral bio-electric synapse spark attack
        self.attack_timer -= dt
        if self.attack_timer <= 0.0 and dist < 280:
            self.attack_timer = random.uniform(1.8, 2.6)
            for k in range(6):
                ang = math.atan2(dy, dx) + (k - 2.5) * 0.22
                p = Projectile(
                    x=self.center_x,
                    y=self.center_y,
                    vx=math.cos(ang) * 6.8,
                    vy=math.sin(ang) * 6.8,
                    damage=14.0,
                    lifetime=75,
                    radius=2.5,
                    color=(40, 230, 255),
                    owner="ENEMY",
                )
                spawned_projs.append(p)

        return spawned_projs, []

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        if not self.alive:
            return
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)

        cx = sx + self.width // 2
        cy = sy + self.height // 2
        glow_rad = int(12 + math.sin(self.anim_time * 5.0) * 3)
        pygame.draw.circle(surface, (20, 140, 220), (cx, cy), glow_rad, 1)
        pygame.draw.circle(surface, (50, 220, 255), (cx, cy), 8)
        pygame.draw.circle(surface, (255, 255, 255), (cx, cy), 3)

        # Rotating bio-electric tendrils
        for offset in (0.0, 1.25, 2.5, 3.75, 5.0):
            tx = cx + int(math.cos(self.anim_time * 2.0 + offset) * 16)
            ty = cy + int(math.sin(self.anim_time * 2.0 + offset) * 16)
            pygame.draw.line(surface, (90, 240, 255), (cx, cy), (tx, ty), 2)


def draw_boss_health_bar(
    surface: pygame.Surface,
    boss: Enemy,
    font: pygame.font.Font,
    view_w: int,
    view_h: int,
) -> None:
    """Render top-center boss health bar with decorative bio-horror styling."""
    if not boss.alive or boss.max_hp <= 0:
        return

    bar_w = 260
    bar_h = 10
    bx = (view_w - bar_w) // 2
    by = 24

    fraction = max(0.0, min(1.0, boss.hp / boss.max_hp))

    # Outer ornate frame
    pygame.draw.rect(surface, (30, 18, 25), (bx - 2, by - 2, bar_w + 4, bar_h + 4), border_radius=3)
    # Background
    pygame.draw.rect(surface, (60, 20, 25), (bx, by, bar_w, bar_h))
    # Fill
    fill_w = int(bar_w * fraction)
    fill_col = (220, 35, 50) if fraction > 0.3 else (255, 80, 20)
    if fill_w > 0:
        pygame.draw.rect(surface, fill_col, (bx, by, fill_w, bar_h))
    # Border
    pygame.draw.rect(surface, (215, 195, 160), (bx - 2, by - 2, bar_w + 4, bar_h + 4), 1, border_radius=3)

    # Title label
    title_str = getattr(boss, "boss_title", boss.display_name.upper())
    label = font.render(title_str, True, (255, 220, 160))
    surface.blit(label, (view_w // 2 - label.get_width() // 2, by - 14))

    # Health numbers
    hp_str = f"{int(boss.hp)} / {int(boss.max_hp)}"
    hp_lbl = font.render(hp_str, True, (255, 255, 255))
    surface.blit(hp_lbl, (view_w // 2 - hp_lbl.get_width() // 2, by + bar_h + 2))
