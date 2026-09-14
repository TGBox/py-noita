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
) -> Optional[HoverTarget]:
    """Inspect world coordinates and return the hovered entity, object, or material.

    Priority order:
    1. Living enemies (closest if overlapping)
    2. Loot cysts / interactive environmental objects
    3. Pixel material from the physics simulation grid (if not air)
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
        if best_enemy.enemy_type == "MACROPHAGE":
            col = (210, 200, 110)
        elif best_enemy.enemy_type == "ANTIBODY":
            col = (210, 230, 245)
        elif best_enemy.enemy_type == "GRANULOCYTE":
            col = (110, 245, 60)
        elif best_enemy.enemy_type == "FLESH_WORM":
            col = (230, 50, 70)
        elif best_enemy.enemy_type == "TUMOR_CYST":
            col = (220, 50, 230)

        return HoverTarget(
            target_type="ENEMY",
            name=best_enemy.display_name,
            category="Gegner",
            color=col,
            current_hp=best_enemy.hp,
            max_hp=best_enemy.max_hp,
        )

    # 2. Check loot cysts
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

    # 3. Check simulation grid pixel
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
