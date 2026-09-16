"""Procedural organ cavern generator: Cellular automata, vascular tunnels, pools, and portals."""

import math
import random
from typing import Any, List, Optional, Tuple
import numpy as np

from py_noita.config import WORLD_HEIGHT, WORLD_WIDTH
from py_noita.physics.collapse import build_cartilage_bridge, build_stalactite
from py_noita.physics.joints import (
    CartilageTendon,
    CeilingTentacle,
    NerveLantern,
    SwingingMeatChunk,
)
from py_noita.physics.props import (
    AcidGallbladder,
    BiogasCyst,
    BoneMinecart,
    CartilageRaft,
    ChitinShield,
)
from py_noita.entities.bosses import (
    BrainCoreBoss,
    GiantHelminth,
    PrimordialPhagocyte,
    SynapticParasite,
)
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import (
    MAT_AIR,
    MAT_ASH,
    MAT_BONE,
    MAT_CHITIN_SAND,
    MAT_FIBRIN_POWDER,
    MAT_NECRO_ASH,
    MAT_SPORES,
    MAT_SULFUR_SPORES,
    MAT_TISSUE,
    MAT_WALL_BONE,
)
from py_noita.world.biome import Biome, BIOME_EPIDERMIS
from py_noita.world.secrets import DnaTablet, GeneOrb, spawn_secrets_for_biome


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
    seed: Optional[int] = None,
    orbs_collected: int = 0,
    progress_callback: Optional[Any] = None,
) -> Tuple[Tuple[float, float], WorldPortal, List[Tuple[float, float, str]], List[LootCyst], List[GeneOrb], List[DnaTablet], Optional[Any]]:
    """Generate a procedural subterranean organ level for the given biome.
    Returns: (player_spawn_pos, exit_portal, enemy_spawn_points, loot_cysts, gene_orbs, dna_tablets, secret_boss).
    """
    def report_progress(val: float, msg: str) -> None:
        if progress_callback is not None:
            try:
                progress_callback(val, msg)
            except Exception:
                pass

    report_progress(0.05, "Biom-Gewebe initialisieren...")

    if seed is not None:
        random.seed(seed)
        np.random.seed(abs(seed) % (2**31))

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
    # Starting floor with descent chutes
    grid.fill_rect(w // 2 - 80, 110, 160, 10, biome.secondary_solid)
    grid.carve_circle(w // 2 - 50, 115, 12, MAT_AIR)
    grid.carve_circle(w // 2 + 50, 115, 12, MAT_AIR)

    report_progress(0.15, "Horizontale Strata & Kavernen wachsen...")

    # 3. Horizontal Strata Cave Generation
    style = getattr(biome, "generation_style", "DEFAULT")
    y_start = 125
    y_end = max(y_start + 80, h - 90)
    playable_h = y_end - y_start

    num_strata = max(3, min(5, playable_h // 120))
    stratum_h = playable_h // num_strata
    strata_bounds = []
    for s in range(num_strata):
        s_top = y_start + s * stratum_h
        s_bot = s_top + stratum_h if s < num_strata - 1 else y_end
        strata_bounds.append((s_top, s_bot))

    # Carve horizontal caverns within each stratum
    for s, (s_top, s_bot) in enumerate(strata_bounds):
        report_progress(0.15 + (s / max(1, len(strata_bounds))) * 0.25, f"Horizontale Kaverne {s+1}/{len(strata_bounds)} wächst...")
        s_mid = (s_top + s_bot) // 2
        num_burrowers = max(3, w // 70)
        if style == "LAGOON":
            num_burrowers += 2
        elif style == "LABYRINTH":
            num_burrowers += 3

        steps_per_burrower = max(200, int(w * (s_bot - s_top) / 320))
        dx_choices = [-5, -4, -3, -2, -1, 1, 2, 3, 4, 5]
        dy_choices = [-1, 0, 0, 0, 1]

        for _ in range(num_burrowers):
            bx = random.randint(30, max(35, w - 30))
            by = random.randint(s_top + 10, max(s_top + 12, s_bot - 14))
            radius = random.randint(7, 13) if style == "LABYRINTH" else random.randint(9, 20)

            for _ in range(steps_per_burrower):
                grid.carve_circle(int(bx), int(by), radius, MAT_AIR)
                bx += random.choice(dx_choices)
                by += random.choice(dy_choices)

                # Keep within horizontal bounds and stratum limits
                bx = max(20, min(w - 20, bx))
                by = max(s_top + 8, min(s_bot - 10, by))

                if random.random() < 0.05:
                    radius = random.randint(6, 12) if style == "LABYRINTH" else random.randint(8, 22)

        # Carve 1-3 expansive open chamber rooms in each stratum
        num_chambers = random.randint(1, 3)
        for _ in range(num_chambers):
            cx = random.randint(40, max(45, w - 40))
            cy = random.randint(s_top + 15, max(s_top + 16, s_bot - 15))
            cr = random.randint(18, 32)
            grid.carve_circle(cx, cy, cr, MAT_AIR)
            # Add natural rock shelf in chamber
            shelf_w = random.randint(20, 45)
            grid.fill_rect(cx - shelf_w // 2, cy + cr // 3, shelf_w, 6, biome.secondary_solid)

        # Establish dense barrier shelf between stratum s and s+1 (except bottom stratum)
        if s < num_strata - 1:
            shelf_y = s_bot
            grid.fill_rect(20, shelf_y - 6, w - 40, 12, biome.secondary_solid)

            # Punch 2-4 deliberate vertical shafts / drops connecting stratum s to s+1
            num_shafts = random.randint(2, 4)
            seg_w = (w - 80) // num_shafts
            for shaft_idx in range(num_shafts):
                min_sx = 40 + shaft_idx * seg_w
                max_sx = min_sx + seg_w - 10
                shaft_x = random.randint(min_sx, max(min_sx + 5, max_sx))
                shaft_r = random.randint(9, 16)
                shaft_curr_x = shaft_x
                next_reach = strata_bounds[s + 1][1]
                for shaft_y in range(s_mid + 5, s_bot + max(15, (next_reach - s_bot) // 3)):
                    grid.carve_circle(int(shaft_curr_x), shaft_y, shaft_r, MAT_AIR)
                    if random.random() < 0.35:
                        shaft_curr_x += random.choice([-2, -1, 0, 1, 2])
                        shaft_curr_x = max(25, min(w - 25, shaft_curr_x))

    # Connect lowest stratum to bottom transition hall
    lowest_s_mid = (strata_bounds[-1][0] + strata_bounds[-1][1]) // 2
    for drop_x in (w // 2 - 60, w // 2 + 60, w // 2):
        for dy in range(lowest_s_mid, h - 80):
            grid.carve_circle(drop_x, dy, 12, MAT_AIR)

    # 3b. Biome-specific architectural features
    if style == "CORE":
        grid.carve_circle(w // 2, h // 2, 48, MAT_AIR)
        grid.fill_rect(w // 2 - 40, h // 2 + 35, 80, 8, biome.secondary_solid)
    elif style == "SPINE":
        grid.fill_rect(w // 2 - 8, int(h * 0.18), 16, int(h * 0.65), biome.secondary_solid)
        for sy in range(int(h * 0.22), int(h * 0.8), 35):
            grid.fill_rect(30, sy, w - 60, 4, biome.primary_solid)

    report_progress(0.40, "Knochenwände & Stützstreben verhärten...")

    # 4. Bone strut reinforcements throughout caverns
    num_struts = max(5, int(h / 50))
    if style == "LABYRINTH":
        num_struts *= 2
    for _ in range(num_struts):
        rx = random.randint(20, max(25, w - 60))
        ry = random.randint(int(h * 0.15), max(int(h * 0.16), h - 100))
        rw = random.randint(16, 48)
        rh = random.randint(5, 12)
        grid.fill_rect(rx, ry, rw, rh, biome.secondary_solid)

    report_progress(0.65, "Fluide & bio-organische Granulate lagern sich ab...")

    # 5. Natural Liquid Basins & Pools
    num_pools = max(3, int(h / 80))
    if style == "LAGOON":
        num_pools += 4
    pool_min_y = int(h * 0.2)
    pool_max_y = max(pool_min_y + 10, h - 80)
    for _ in range(num_pools):
        px = random.randint(30, max(35, w - 40))
        py = random.randint(pool_min_y, pool_max_y)
        for search_y in range(py, min(h - 60, py + 60)):
            if grid.is_solid(px, search_y):
                pool_r = random.randint(12, 24) if style == "LAGOON" else random.randint(8, 18)
                grid.carve_circle(px, search_y - 2, pool_r, MAT_AIR)
                basin_w = 30 if style == "LAGOON" else 20
                grid.fill_rect(px - basin_w // 2, search_y - 6, basin_w, 10, biome.liquid_pool_mat)
                break

    # 6. Gas and Powder pockets (Placed on solid floors / basins)
    if biome.gas_mat != MAT_AIR:
        gas_count = max(4, int(h / 80)) if style in ("LAGOON", "LUNG") else max(2, int(h / 120))
        for _ in range(gas_count):
            gx = random.randint(30, max(35, w - 50))
            gy = random.randint(int(h * 0.25), max(int(h * 0.26), h - 90))
            grid.fill_rect(gx, gy, random.randint(12, 28), random.randint(6, 14), biome.gas_mat)

    # Bio-powder materials selection per biome
    powder_palette = [biome.powder_mat] if biome.powder_mat != MAT_AIR else []
    if biome.biome_id in ("EPIDERMIS", "CHITIN_WARREN"):
        powder_palette.extend([MAT_CHITIN_SAND, MAT_NECRO_ASH])
    elif biome.biome_id in ("VASCULAR_SYSTEM", "GASTRIC_CAVERNS"):
        powder_palette.extend([MAT_FIBRIN_POWDER, MAT_ASH])
    elif biome.biome_id in ("BILE_LAGOON", "PULMONARY_LABYRINTH"):
        powder_palette.extend([MAT_SULFUR_SPORES, MAT_SPORES])
    else:
        powder_palette.extend([MAT_CHITIN_SAND, MAT_FIBRIN_POWDER, MAT_NECRO_ASH])
    powder_palette = [p for p in powder_palette if p != MAT_AIR]

    if powder_palette:
        powder_count = max(6, int(h / 45)) if style in ("LUNG", "LABYRINTH") else max(4, int(h / 70))
        for _ in range(powder_count):
            sx = random.randint(30, max(35, w - 50))
            sy = random.randint(int(h * 0.18), max(int(h * 0.19), h - 90))
            chosen_powder = random.choice(powder_palette)
            # Find solid ground below sx, sy to settle on
            for ground_y in range(sy, min(h - 60, sy + 70)):
                if grid.is_solid(sx, ground_y):
                    heap_w = random.randint(7, 15)
                    heap_h = random.randint(3, 7)
                    for hdx in range(-heap_w, heap_w + 1):
                        px = sx + hdx
                        if 2 <= px < w - 2:
                            col_h = int(heap_h * (1.0 - (hdx / (heap_w + 1.0)) ** 2))
                            for hdh in range(1, col_h + 1):
                                py = ground_y - hdh
                                if 2 <= py < h - 2 and grid.get_pixel(px, py) == MAT_AIR:
                                    grid.set_pixel(px, py, chosen_powder)
                    break

    # Pre-simulate settling so powders & liquids rest naturally
    report_progress(0.72, "Physikalische Sedimentierung & Dünen-Stabilisierung...")
    grid.settle_world(steps=15)

    # 7. Bottom Transition Hallway & Exit Portal
    portal_y = h - 60
    portal_x = w // 2

    # Carve grand exit hall
    grid.fill_rect(portal_x - 50, portal_y - 30, 100, 50, MAT_AIR)
    # Sturdy floor under portal
    grid.fill_rect(portal_x - 60, portal_y + 20, 120, 14, MAT_WALL_BONE)

    exit_portal = WorldPortal(float(portal_x), float(portal_y))

    report_progress(0.85, "Wächter und Biomasse-Zysten erwachen...")

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
    target_cysts = max(2, int(h / 100))
    cyst_attempts = 0
    while len(loot_cysts) < target_cysts and cyst_attempts < 100:
        cyst_attempts += 1
        cx = random.randint(30, max(35, w - 40))
        cy = random.randint(int(h * 0.15), max(int(h * 0.16), h - 80))
        if grid.is_empty(cx, cy):
            reward = "GENE" if random.random() < 0.4 else "BIOMASS"
            loot_cysts.append(LootCyst(float(cx), float(cy), reward))

    # 10. Organic Destructible Props
    pw = physics_world if physics_world is not None else getattr(grid, "physics_world", None)
    if pw is not None:
        spawn_biome_props(pw, grid, biome)

    # 11. Secrets: Gene Orbs and Ancient DNA Tablets
    gene_orbs, dna_tablets = spawn_secrets_for_biome(
        grid, biome.biome_id, biome.depth_level, seed=seed
    )

    # 12. Bosses (Optional Bio-Bosses & Final Primordial Brain Core)
    secret_boss = None
    if biome.biome_id == "BONE_CATACOMBS":
        # Ossuary lair for Giant Helminth in deep catacombs
        grid.carve_circle(w - 70, h - 90, 26, MAT_AIR)
        secret_boss = GiantHelminth(float(w - 70), float(h - 90))
    elif biome.biome_id == "BILE_LAGOON":
        # Bile trench lair for Primordial Phagocyte
        grid.carve_circle(w // 2, h - 90, 30, MAT_AIR)
        secret_boss = PrimordialPhagocyte(float(w // 2), float(h - 90))
    elif biome.biome_id == "SPINE_NERVES":
        # Electric synapse shrine for Synaptic Parasite
        grid.carve_circle(w // 2, h - 100, 28, MAT_AIR)
        secret_boss = SynapticParasite(float(w // 2), float(h - 100))
    elif biome.biome_id == "PRIMORDIAL_CORE":
        # Final Brain Core Boss in central chamber
        secret_boss = BrainCoreBoss(float(w // 2), float(h // 2), orbs_collected=orbs_collected)

    # 13. Surface Cosmic Ascent Portal (Biome 1: Epidermis ceiling)
    if biome.biome_id == "EPIDERMIS":
        from py_noita.world.endings import SurfaceAscentPortal
        grid.fill_rect(w // 2 - 25, 12, 50, 24, MAT_AIR)
        grid.ascent_portal = SurfaceAscentPortal(float(w // 2), 24.0)
    else:
        grid.ascent_portal = None

    report_progress(1.0, "Subterranes Organ bereit!")

    return (spawn_x, spawn_y), exit_portal, enemy_spawns, loot_cysts, gene_orbs, dna_tablets, secret_boss


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
            style = getattr(biome, "generation_style", "DEFAULT")
            prop_choice = random.random()
            if style == "LAGOON":
                # More chitin shields and acid bladders in lagoon
                if prop_choice < 0.40:
                    prop = AcidGallbladder(physics_world.space, float(rx), float(ry))
                elif prop_choice < 0.55:
                    prop = BiogasCyst(physics_world.space, float(rx), float(ry))
                elif prop_choice < 0.65:
                    prop = BoneMinecart(physics_world.space, float(rx), float(ry))
                else:
                    prop = ChitinShield(physics_world.space, float(rx), float(ry))
            elif style == "LABYRINTH":
                # More bone minecarts in catacombs
                if prop_choice < 0.20:
                    prop = AcidGallbladder(physics_world.space, float(rx), float(ry))
                elif prop_choice < 0.40:
                    prop = BiogasCyst(physics_world.space, float(rx), float(ry))
                elif prop_choice < 0.85:
                    prop = BoneMinecart(physics_world.space, float(rx), float(ry))
                else:
                    prop = ChitinShield(physics_world.space, float(rx), float(ry))
            else:
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

    # 3. Hanging objects from cavern ceilings: Nerve Lanterns, Meat Chunks, and Ceiling Tentacles
    ceiling_candidates = []
    for cx in range(25, max(30, w - 25), 12):
        for cy in range(int(h * 0.1), max(int(h * 0.11), int(h * 0.85))):
            if grid.is_solid(cx, cy):
                # Check for vertical clearance below
                is_clear_ceiling = True
                for dy in range(1, 18):
                    if not grid.is_empty(cx, cy + dy):
                        is_clear_ceiling = False
                        break
                if is_clear_ceiling:
                    ceiling_candidates.append((cx, cy))
                    break

    random.shuffle(ceiling_candidates)
    hanging_count = min(len(ceiling_candidates), max(3, int(count * 0.6)))
    for i in range(hanging_count):
        cx, cy = ceiling_candidates[i]
        choice = random.random()
        if choice < 0.45:
            # Nerve Lantern
            lantern = NerveLantern(physics_world.space, float(cx), float(cy + 16), anchor_y=float(cy))
            physics_world.add_body(lantern)
            if lantern.tendon:
                physics_world.add_tendon(lantern.tendon)
        elif choice < 0.75:
            # Swinging Meat Chunk
            chunk = SwingingMeatChunk(physics_world.space, float(cx), float(cy + 20), anchor_y=float(cy))
            physics_world.add_body(chunk)
            if chunk.tendon:
                physics_world.add_tendon(chunk.tendon)
        else:
            # Ceiling Tentacle
            tentacle = CeilingTentacle(physics_world, float(cx), float(cy + 1), num_segments=random.randint(4, 6))
            physics_world.add_tentacle(tentacle)

    # 4. Ceiling Stalactites (pointed bone formations that fall and impale when shot loose)
    stalactite_count = min(len(ceiling_candidates), max(3, int(count * 0.5)))
    for i in range(stalactite_count):
        cx, cy = ceiling_candidates[i]
        build_stalactite(
            grid,
            cx,
            cy + 1,
            length=random.randint(14, 22),
            base_width=random.randint(6, 9),
            mat=biome.secondary_solid,
        )

    # 5. Collapsing Cartilage Bridges across cavern gaps
    for _ in range(max(2, int(h / 120))):
        by = random.randint(int(h * 0.2), int(h * 0.8))
        bx_start = random.randint(25, max(30, w - 80))
        if grid.is_solid(bx_start, by):
            gap_len = 0
            for span in range(1, 40):
                if bx_start + span >= w - 1:
                    break
                if grid.is_empty(bx_start + span, by):
                    gap_len += 1
                elif grid.is_solid(bx_start + span, by) and gap_len >= 8:
                    build_cartilage_bridge(
                        grid,
                        bx_start,
                        bx_start + span,
                        by,
                        thickness=random.randint(3, 5),
                        mat=biome.secondary_solid,
                    )
                    break
