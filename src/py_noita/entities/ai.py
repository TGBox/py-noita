"""Enemy AI behavior routines for crawling, swarming, acid spewing, and worm burrowing."""

import math
import random
from typing import List, Optional, Tuple
import numpy as np

from py_noita.entities.enemy import (
    Antibody,
    Enemy,
    FleshWorm,
    Granulocyte,
    Macrophage,
    TumorCyst,
)
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import MAT_ACID, MAT_AIR
from py_noita.weapons.projectile import Projectile


def update_enemy_ai(
    enemy: Enemy,
    player,
    grid: SimulationGrid,
    dt: float,
) -> Tuple[List[Projectile], List[Enemy]]:
    """Update AI decisions and attacks.
    Returns: (spawned_hostile_projectiles, spawned_minions)
    """
    if not enemy.alive or not player.alive:
        return [], []

    spawned_projectiles: List[Projectile] = []
    spawned_minions: List[Enemy] = []

    dx = player.center_x - enemy.center_x
    dy = player.center_y - enemy.center_y
    dist = math.hypot(dx, dy)

    # 1. MACROPHAGE: Crawling amoeba
    if isinstance(enemy, Macrophage):
        enemy.attack_cooldown -= dt
        # Move horizontally towards player
        if dist < 220:
            move_dir = 1.0 if dx > 0 else -1.0
            enemy.vx += (move_dir * 1.1 - enemy.vx) * 0.2

            # Check if wall in front -> jump/climb
            ahead_x = int(enemy.center_x + move_dir * 10)
            ahead_y = int(enemy.center_y)
            if grid.is_solid(ahead_x, ahead_y):
                enemy.vy = -2.2

        # Gravity & ground collision
        enemy.vy += 0.22
        enemy.vy = min(enemy.vy, 4.0)

        # Step physics
        nx = enemy.x + enemy.vx
        ny = enemy.y + enemy.vy
        if not grid.is_solid(int(nx + enemy.width // 2), int(ny + enemy.height)):
            enemy.x = nx
            enemy.y = ny
        else:
            enemy.y = ny - 1
            enemy.vy = 0.0
            enemy.x = nx

        # Melee engulfment damage
        if dist < (enemy.width + player.width) / 2.0 + 2.0:
            player.take_damage(0.4, "ENGULFMENT")

    # 2. ANTIBODY: Agile flying shooter
    elif isinstance(enemy, Antibody):
        enemy.attack_cooldown -= dt
        # Hover & pursue player from medium range (approx 90-140px)
        if dist < 280:
            desired_dist = 110.0
            target_x = player.center_x - (dx / max(1.0, dist)) * desired_dist
            target_y = player.center_y - (dy / max(1.0, dist)) * desired_dist

            enemy.vx += ((target_x - enemy.center_x) * 0.05 - enemy.vx) * 0.15
            enemy.vy += ((target_y - enemy.center_y) * 0.05 - enemy.vy) * 0.15

            enemy.x += enemy.vx
            enemy.y += enemy.vy

            # Shoot cytokine dart
            if enemy.attack_cooldown <= 0.0 and dist < 180:
                enemy.attack_cooldown = random.uniform(1.8, 3.2)
                angle = math.atan2(dy, dx)
                dart = Projectile(
                    x=enemy.center_x,
                    y=enemy.center_y,
                    vx=math.cos(angle) * 5.5,
                    vy=math.sin(angle) * 5.5,
                    damage=10.0,
                    lifetime=70,
                    radius=2.0,
                    color=(220, 240, 255),
                    owner="ENEMY",
                )
                spawned_projectiles.append(dart)

    # 3. GRANULOCYTE: Heavy acid spewer
    elif isinstance(enemy, Granulocyte):
        enemy.attack_cooldown -= dt
        # Lumber towards player
        if dist < 240:
            move_dir = 1.0 if dx > 0 else -1.0
            enemy.vx += (move_dir * 0.65 - enemy.vx) * 0.1

        enemy.vy += 0.28
        enemy.x += enemy.vx
        enemy.y += enemy.vy

        # Spew stream of acid when in range
        if dist < 120 and abs(dx) < 100:
            if random.random() < 0.35:
                # Emit acid into grid towards player
                angle = math.atan2(dy, dx) + random.uniform(-0.2, 0.2)
                emit_x = int(enemy.center_x + math.cos(angle) * 12)
                emit_y = int(enemy.center_y + math.sin(angle) * 12)
                if 1 <= emit_x < grid.width - 1 and 1 <= emit_y < grid.height - 1:
                    grid.set_pixel(emit_x, emit_y, MAT_ACID)

    # 4. FLESH WORM: Terrain-eating tunneling centipede
    elif isinstance(enemy, FleshWorm):
        if dist < 320:
            # Steer head towards player
            target_angle = math.atan2(dy, dx)
            cur_angle = enemy.target_angle
            angle_diff = (target_angle - cur_angle + math.pi) % (2 * math.pi) - math.pi
            enemy.target_angle += max(-0.08, min(0.08, angle_diff))

            speed = 2.4
            enemy.vx = math.cos(enemy.target_angle) * speed
            enemy.vy = math.sin(enemy.target_angle) * speed

            enemy.x += enemy.vx
            enemy.y += enemy.vy

            # Head carves tunnels through tissue!
            hx = int(enemy.center_x)
            hy = int(enemy.center_y)
            grid.carve_circle(hx, hy, radius=7, fill_mat=MAT_AIR)

            # Update body segments
            if enemy.segments:
                enemy.segments[0].x = enemy.x
                enemy.segments[0].y = enemy.y
                for i in range(1, len(enemy.segments)):
                    lead = enemy.segments[i - 1]
                    seg = enemy.segments[i]
                    seg_dx = lead.x - seg.x
                    seg_dy = lead.y - seg.y
                    seg_dist = math.hypot(seg_dx, seg_dy)
                    if seg_dist > 6.0:
                        seg.x += (seg_dx / seg_dist) * (seg_dist - 6.0)
                        seg.y += (seg_dy / seg_dist) * (seg_dist - 6.0)

            # High collision damage
            if dist < 14.0:
                player.take_damage(0.8, "WORM_BITE")

    # 5. TUMOR CYST: Spawner
    elif isinstance(enemy, TumorCyst):
        enemy.spawn_timer -= dt
        if enemy.spawn_timer <= 0.0 and dist < 300:
            enemy.spawn_timer = random.uniform(5.5, 8.5)
            # Spawn mini antibody
            minion = Antibody(enemy.center_x + random.randint(-15, 15), enemy.center_y - 12)
            spawned_minions.append(minion)

    return spawned_projectiles, spawned_minions
