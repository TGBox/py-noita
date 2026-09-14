"""Hover target detection for materials, liquids, and enemies (Noita-style inspection)."""

from dataclasses import dataclass
import math
from typing import Any, Optional, Sequence, Tuple

from py_noita.entities.enemy import Enemy
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import (
    LUT_COLORS,
    MAT_AIR,
    get_material_category,
    get_material_name,
)


@dataclass
class HoverTarget:
    """Represents the entity or material currently hovered by the cursor."""

    target_type: str  # "ENEMY", "MATERIAL", "OBJECT"
    name: str  # Display name in German
    category: str  # "Gegner", "Flüssigkeit", "Feststoff", "Pulver", "Gas", "Energie"
    color: Tuple[int, int, int]
    current_hp: Optional[float] = None
    max_hp: Optional[float] = None


def get_hover_target(
    grid: SimulationGrid,
    enemies: Sequence[Enemy],
    world_x: float,
    world_y: float,
    loot_cysts: Optional[Sequence[Any]] = None,
    rigid_bodies: Optional[Sequence[Any]] = None,
    gene_orbs: Optional[Sequence[Any]] = None,
    dna_tablets: Optional[Sequence[Any]] = None,
) -> Optional[HoverTarget]:
    """Inspect world coordinates and return the hovered entity, object, or material.

    Priority order:
    1. Living enemies (closest if overlapping)
    2. Gene Orbs & DNA Lore Tablets
    3. Physical rigid bodies / props
    4. Loot cysts / interactive environmental objects
    5. Pixel material from the physics simulation grid (if not air)
    """
    # 1. Check living enemies
    candidate_enemies = []
    for enemy in enemies:
        if enemy.alive and enemy.contains_point(world_x, world_y):
            dist = math.hypot(world_x - enemy.center_x, world_y - enemy.center_y)
            candidate_enemies.append((dist, enemy))

    if candidate_enemies:
        candidate_enemies.sort(key=lambda item: item[0])
        best_enemy = candidate_enemies[0][1]

        # Accent color depending on enemy type
        col = (240, 70, 80)
        etype = best_enemy.enemy_type
        if etype == "MACROPHAGE":
            col = (210, 200, 110)
        elif etype == "ANTIBODY":
            col = (210, 230, 245)
        elif etype == "GRANULOCYTE":
            col = (110, 245, 60)
        elif etype == "FLESH_WORM" or etype == "GIANT_HELMINTH":
            col = (230, 50, 70)
        elif etype == "TUMOR_CYST":
            col = (220, 50, 230)
        elif etype == "CHITIN_BEETLE":
            col = (160, 140, 190)
        elif etype == "SPORE_POD" or etype == "PRIMORDIAL_PHAGOCYTE":
            col = (180, 220, 40)
        elif etype == "SYNAPTIC_SENTRY" or etype == "SYNAPTIC_PARASITE":
            col = (50, 220, 255)

        return HoverTarget(
            target_type="ENEMY",
            name=getattr(best_enemy, "boss_title", best_enemy.display_name),
            category="Bio-Boss" if "HELMINTH" in etype or "PHAGOCYTE" in etype or "PARASITE" in etype else "Gegner",
            color=col,
            current_hp=best_enemy.hp,
            max_hp=best_enemy.max_hp,
        )

    # 1b. Check Gene Orbs
    if gene_orbs:
        for orb in gene_orbs:
            if not getattr(orb, "collected", False):
                ox = getattr(orb, "x", 0.0)
                oy = getattr(orb, "y", 0.0)
                r = getattr(orb, "radius", 9.0)
                if math.hypot(world_x - ox, world_y - oy) <= (r + 4.0):
                    return HoverTarget(
                        target_type="OBJECT",
                        name=getattr(orb, "name", "DNA-Gen-Orb"),
                        category="Ur-Geheimnis",
                        color=(255, 215, 60),
                    )

    # 1c. Check DNA Lore Tablets
    if dna_tablets:
        for tab in dna_tablets:
            if hasattr(tab, "contains_point") and tab.contains_point(world_x, world_y):
                return HoverTarget(
                    target_type="OBJECT",
                    name=getattr(tab, "title", "Uraltes DNA-Tablet"),
                    category="Uralte Lore",
                    color=(210, 200, 160),
                )

    # 2. Check physical rigid bodies
    if rigid_bodies:
        for rb in rigid_bodies:
            if getattr(rb, "alive", False) and rb.contains_point(world_x, world_y):
                return HoverTarget(
                    target_type="OBJECT",
                    name=getattr(rb, "name", "Objekt"),
                    category="Objekt",
                    color=getattr(rb, "color", (190, 180, 165)),
                    current_hp=getattr(rb, "health", None) if getattr(rb, "destructible", False) else None,
                    max_hp=getattr(rb, "max_health", None) if getattr(rb, "destructible", False) else None,
                )

    # 3. Check loot cysts
    if loot_cysts:
        for cyst in loot_cysts:
            if getattr(cyst, "alive", False):
                cx = getattr(cyst, "x", 0.0)
                cy = getattr(cyst, "y", 0.0)
                radius = getattr(cyst, "radius", 8.0)
                if math.hypot(world_x - cx, world_y - cy) <= (radius + 3.0):
                    return HoverTarget(
                        target_type="OBJECT",
                        name="Biomasse-Zyste",
                        category="Objekt",
                        color=(230, 200, 60),
                    )

    # 4. Check simulation grid pixel
    ix = int(math.floor(world_x))
    iy = int(math.floor(world_y))

    if 0 <= ix < grid.width and 0 <= iy < grid.height:
        mat_id = int(grid.get_pixel(ix, iy))
        if mat_id != MAT_AIR:
            name = get_material_name(mat_id)
            cat = get_material_category(mat_id)
            col = tuple(int(c) for c in LUT_COLORS[mat_id])
            return HoverTarget(
                target_type="MATERIAL",
                name=name,
                category=cat,
                color=col,
            )

    return None
