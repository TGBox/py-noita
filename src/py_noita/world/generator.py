"""Procedural organ cavern generator: Cellular automata, vascular tunnels, pools, and portals."""

import math
import random
from typing import Any, List, Optional, Tuple
import numpy as np

from py_noita.config import WORLD_HEIGHT, WORLD_WIDTH
from py_noita.physics.props import (
    AcidGallbladder,
    BiogasCyst,
    BoneMinecart,
    CartilageRaft,
    ChitinShield,
)
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import (
    MAT_AIR,
    MAT_BONE,
    MAT_TISSUE,
    MAT_WALL_BONE,
)
from py_noita.world.biome import Biome, BIOME_EPIDERMIS


class WorldPortal:
    """Transition portal leading into the Incubation Node (Holy Mountain)."""
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.radius = 16.0
        self.active: bool = True
        self.anim_time: float = 0.0

    def update(self) -> None:
        self.anim_time += 0.08

    def is_player_inside(self, px: float, py: float) -> bool:
        return math.hypot(px - self.x, py - self.y) < self.radius


class LootCyst:
    """An organic treasure cyst that drops biomass or genes when blasted."""
    def __init__(self, x: float, y: float, reward_type: str = "BIOMASS"):
        self.x = x
        self.y = y
        self.reward_type = reward_type
        self.radius = 8.0
        self.alive: bool = True


def generate_world_level(
    grid: SimulationGrid,
    biome: Biome,
    physics_world: Optional[Any] = None,
) -> Tuple[Tuple[float, float], WorldPortal, List[Tuple[float, float, str]], List[LootCyst]]:
    """Generate a procedural subterranean organ level for the given biome.
    Returns: (player_spawn_pos, exit_portal, enemy_spawn_points, loot_cysts).
    """
    w = grid.width
    h = grid.height

    # 1. Fill entire grid with solid biome tissue
    grid.grid.fill(biome.primary_solid)
    grid.life.fill(0)
    grid.init_boundaries()

    # 2. Carve Top Starting Chamber (y: 25 to 110)
    spawn_x = float(w // 2)
    spawn_y = 60.0
    grid.fill_rect(w // 2 - 60, 30, 120, 80, MAT_AIR)
    # Starting floor
    grid.fill_rect(w // 2 - 80, 110, 160, 10, biome.secondary_solid)

    # 3. Procedural Cave Carving: Multi-agent random burrowers & cellular automata
    num_burrowers = max(4, w // 80)
    burrow_steps = max(300, int(w * h / 400))
    for b in range(num_burrowers):
        bx = random.randint(w // 4, 3 * w // 4)
        by = random.randint(max(40, int(h * 0.1)), max(50, int(h * 0.2)))
        radius = random.randint(8, 20)

        for _ in range(burrow_steps):
            grid.carve_circle(int(bx), int(by), radius, MAT_AIR)
            # Biased to drift downwards towards bottom
            bx += random.choice([-3, -2, -1, 0, 1, 2, 3])
            by += random.choice([-1, 0, 1, 2, 3, 4])

            # Keep inside world bounds
            bx = max(20, min(w - 20, bx))
            by = max(40, min(h - 80, by))

            if random.random() < 0.05:
                radius = random.randint(8, 22)

    # 4. Bone strut reinforcements throughout caverns
    num_struts = max(5, int(h / 50))
    for _ in range(num_struts):
        rx = random.randint(20, max(25, w - 60))
        ry = random.randint(int(h * 0.15), max(int(h * 0.16), h - 100))
        rw = random.randint(16, 48)
        rh = random.randint(5, 12)
        grid.fill_rect(rx, ry, rw, rh, biome.secondary_solid)

    # 5. Natural Liquid Basins & Pools
    num_pools = max(3, int(h / 80))
    pool_min_y = int(h * 0.2)
    pool_max_y = max(pool_min_y + 10, h - 80)
    for _ in range(num_pools):
        px = random.randint(30, max(35, w - 40))
        py = random.randint(pool_min_y, pool_max_y)
        # Search down for an air-to-solid boundary
        for search_y in range(py, min(h - 60, py + 60)):
            if grid.is_solid(px, search_y):
                # Carve basin and fill with liquid
                grid.carve_circle(px, search_y - 2, random.randint(8, 18), MAT_AIR)
                grid.fill_rect(px - 10, search_y - 6, 20, 10, biome.liquid_pool_mat)
                break

    # 6. Gas and Powder pockets
    if biome.gas_mat != MAT_AIR:
        for _ in range(max(2, int(h / 120))):
            gx = random.randint(30, max(35, w - 50))
            gy = random.randint(int(h * 0.25), max(int(h * 0.26), h - 90))
            grid.fill_rect(gx, gy, random.randint(12, 28), random.randint(6, 14), biome.gas_mat)

    if biome.powder_mat != MAT_AIR:
        for _ in range(max(3, int(h / 90))):
            sx = random.randint(30, max(35, w - 50))
            sy = random.randint(int(h * 0.2), max(int(h * 0.21), h - 90))
            grid.spray_circle(sx, sy, random.randint(6, 14), biome.powder_mat, density=0.8)

    # 7. Bottom Transition Hallway & Exit Portal
    portal_y = h - 60
    portal_x = w // 2

    # Carve grand exit hall
    grid.fill_rect(portal_x - 50, portal_y - 30, 100, 50, MAT_AIR)
    # Sturdy floor under portal
    grid.fill_rect(portal_x - 60, portal_y + 20, 120, 14, MAT_WALL_BONE)

    exit_portal = WorldPortal(float(portal_x), float(portal_y))

    # 8. Enemy spawn locations
    enemy_spawns: List[Tuple[float, float, str]] = []
    num_enemies = max(4, int(h / 30)) + biome.depth_level * 3
    attempts = 0
    while len(enemy_spawns) < num_enemies and attempts < 150:
        attempts += 1
        ex = random.randint(30, max(35, w - 40))
        ey = random.randint(int(h * 0.15), max(int(h * 0.16), h - 80))
        if grid.is_empty(ex, ey) and grid.is_solid(ex, ey + 8):
            etype = random.choice(biome.enemy_types)
            enemy_spawns.append((float(ex), float(ey), etype))

    # 9. Loot Cysts
    loot_cysts: List[LootCyst] = []
    for _ in range(max(2, int(h / 100))):
        cx = random.randint(40, max(45, w - 50))
        cy = random.randint(int(h * 0.2), max(int(h * 0.21), h - 80))
        if grid.is_empty(cx, cy):
            reward = "GENE" if random.random() < 0.4 else "BIOMASS"
            loot_cysts.append(LootCyst(float(cx), float(cy), reward))

    # 10. Organic Destructible Props
    pw = physics_world if physics_world is not None else getattr(grid, "physics_world", None)
    if pw is not None:
        spawn_biome_props(pw, grid, biome)

    return (spawn_x, spawn_y), exit_portal, enemy_spawns, loot_cysts


def spawn_biome_props(physics_world, grid: SimulationGrid, biome: Biome, count: int = 14) -> None:
    """Procedurally place organic environmental props into the level."""
    w = grid.width
    h = grid.height

    # 1. Floating cartilage rafts on liquid pools
    for px in range(25, max(30, w - 25), 20):
        for py in range(15, max(20, h - 15), 10):
            if grid.is_liquid(px, py) and grid.is_empty(px, py - 3):
                raft = CartilageRaft(physics_world.space, float(px), float(py - 2), width=random.choice([24.0, 30.0]))
                physics_world.add_body(raft)
                break

    # 2. Cavern props: Acid Gallbladders, Biogas Cysts, Bone Minecarts, Chitin Shields
    attempts = 0
    spawned = 0
    min_y = max(15, int(h * 0.08))
    max_y = max(min_y + 10, h - 20)
    while spawned < count and attempts < 150:
        attempts += 1
        rx = random.randint(20, max(25, w - 25))
        ry = random.randint(min_y, max_y)

        if grid.is_empty(rx, ry) and (grid.is_solid(rx, ry + 4) or grid.is_solid(rx, ry + 6)):
            prop_choice = random.random()
            if prop_choice < 0.35:
                prop = AcidGallbladder(physics_world.space, float(rx), float(ry))
            elif prop_choice < 0.65:
                prop = BiogasCyst(physics_world.space, float(rx), float(ry))
            elif prop_choice < 0.85:
                prop = BoneMinecart(physics_world.space, float(rx), float(ry))
            else:
                prop = ChitinShield(physics_world.space, float(rx), float(ry))

            physics_world.add_body(prop)
            spawned += 1
