"""Enemy AI behavior routines for crawling, swarming, acid spewing, and worm burrowing."""

import math
import random
from typing import List, Optional, Tuple
import numpy as np

from py_noita.entities.enemy import (
    Antibody,
    ChitinBeetle,
    Enemy,
    FleshWorm,
    Granulocyte,
    Macrophage,
    SporePod,
    SynapticSentry,
    TumorCyst,
)
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import (
    MAT_ACID,
    MAT_AIR,
    MAT_SPORES,
    MAT_TOXIC_VAPOR,
)
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

    # 6. CHITIN BEETLE: Armored charging scuttler
    elif isinstance(enemy, ChitinBeetle):
        enemy.attack_cooldown -= dt
        if dist < 260:
            move_dir = 1.0 if dx > 0 else -1.0
            enemy.facing_dir = move_dir
            if not enemy.is_charging:
                if dist < 120 and abs(dy) < 35 and enemy.attack_cooldown <= 0.0:
                    enemy.is_charging = True
                    enemy.charge_timer = 0.85
                    enemy.attack_cooldown = 2.4
                else:
                    enemy.vx += (move_dir * 1.6 - enemy.vx) * 0.2
            else:
                enemy.charge_timer -= dt
                enemy.vx += (enemy.facing_dir * 3.8 - enemy.vx) * 0.4
                if enemy.charge_timer <= 0.0:
                    enemy.is_charging = False

            ahead_x = int(enemy.center_x + enemy.facing_dir * 12)
            ahead_y = int(enemy.center_y)
            if grid.is_solid(ahead_x, ahead_y):
                enemy.vy = -2.6

        enemy.vy += 0.26
        enemy.vy = min(enemy.vy, 4.5)
        nx = enemy.x + enemy.vx
        ny = enemy.y + enemy.vy
        if not grid.is_solid(int(nx + enemy.width // 2), int(ny + enemy.height)):
            enemy.x = nx
            enemy.y = ny
        else:
            enemy.y = ny - 1
            enemy.vy = 0.0
            enemy.x = nx

        if dist < (enemy.width + player.width) / 2.0 + 3.0:
            dmg = 1.2 if enemy.is_charging else 0.4
            player.take_damage(dmg, "BEETLE_RAM")

    # 7. SPORE POD: Floating low-gravity spore mine
    elif isinstance(enemy, SporePod):
        enemy.float_phase += 0.04
        enemy.vx += (math.cos(enemy.float_phase) * 0.6 - enemy.vx) * 0.08
        enemy.vy += (math.sin(enemy.float_phase * 1.3) * 0.6 - enemy.vy) * 0.08
        enemy.x += enemy.vx
        enemy.y += enemy.vy

        if dist < 220:
            enemy.attack_cooldown -= dt
            if enemy.attack_cooldown <= 0.0:
                enemy.attack_cooldown = random.uniform(2.5, 4.0)
                # Scatter spores and toxic vapor into surrounding air
                for _ in range(8):
                    sx = int(enemy.center_x + random.randint(-12, 12))
                    sy = int(enemy.center_y + random.randint(-12, 12))
                    if 1 <= sx < grid.width - 1 and 1 <= sy < grid.height - 1 and grid.is_empty(sx, sy):
                        grid.set_pixel(sx, sy, random.choice([MAT_SPORES, MAT_TOXIC_VAPOR]))

                # Fire seeking spore darts
                for angle_offset in (-0.25, 0.25):
                    angle = math.atan2(dy, dx) + angle_offset
                    spore_proj = Projectile(
                        x=enemy.center_x,
                        y=enemy.center_y,
                        vx=math.cos(angle) * 3.2,
                        vy=math.sin(angle) * 3.2,
                        damage=8.0,
                        lifetime=90,
                        radius=2.5,
                        color=(180, 220, 50),
                        owner="ENEMY",
                    )
                    spawned_projectiles.append(spore_proj)

    # 8. SYNAPTIC SENTRY: Bio-electric neuro-guardian
    elif isinstance(enemy, SynapticSentry):
        desired_dist = 130.0
        target_x = player.center_x - (dx / max(1.0, dist)) * desired_dist
        target_y = player.center_y - (dy / max(1.0, dist)) * desired_dist

        enemy.vx += ((target_x - enemy.center_x) * 0.07 - enemy.vx) * 0.2
        enemy.vy += ((target_y - enemy.center_y) * 0.07 - enemy.vy) * 0.2
        enemy.x += enemy.vx
        enemy.y += enemy.vy

        # Teleport blink if player gets too close
        enemy.teleport_cooldown -= dt
        if enemy.teleport_cooldown <= 0.0 and dist < 100:
            blink_angle = random.uniform(0, 2 * math.pi)
            enemy.x += math.cos(blink_angle) * 45.0
            enemy.y += math.sin(blink_angle) * 45.0
            enemy.teleport_cooldown = random.uniform(3.0, 5.0)

        # High-speed synapse spark attack
        enemy.attack_cooldown -= dt
        if enemy.attack_cooldown <= 0.0 and dist < 240:
            enemy.attack_cooldown = random.uniform(1.2, 2.0)
            angle = math.atan2(dy, dx)
            spark = Projectile(
                x=enemy.center_x,
                y=enemy.center_y,
                vx=math.cos(angle) * 6.5,
                vy=math.sin(angle) * 6.5,
                damage=12.0,
                lifetime=60,
                radius=2.0,
                color=(50, 220, 255),
                owner="ENEMY",
            )
            spawned_projectiles.append(spark)

    return spawned_projectiles, spawned_minions
