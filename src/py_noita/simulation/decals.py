"""Visceral Skeletal Remains & Permanent Tissue Staining Decal System.

Provides anatomical corpse skeleton placement and permanent decal maps
(blood splatters, corrosive acid pitting, viscous slime sheens, and char/soot scars).
"""

import math
from typing import List, Tuple
import numpy as np

from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import (
    MAT_ACID,
    MAT_AIR,
    MAT_BONE,
    MAT_BONE_CHIP,
    MAT_CHITIN,
    MAT_MUTAGEN,
    MAT_PUS,
    MAT_WALL_BONE,
    PROP_LIFETIME,
    STAIN_ACID,
    STAIN_BLOOD,
    STAIN_CHAR,
    STAIN_MUTAGEN,
    STAIN_SLIME,
)


def spawn_corpse_skeleton(
    grid: SimulationGrid,
    center_x: float,
    center_y: float,
    enemy_type: str = "DEFAULT",
    blood_mat: int = 20,
) -> List[Tuple[int, int]]:
    """Spawn an anatomical bone skeleton into the simulation grid upon enemy death.
    The bone pixels interact with the falling-sand physics:
    - Dissolved and corroded into bubbling foam when exposed to acid
    - Shattered and blasted into flying bone chips by explosions
    - Fall and tumble if the supporting cavern terrain collapses
    """
    cx = int(center_x)
    cy = int(center_y)
    bone_pixels: List[Tuple[int, int]] = []

    def set_bone(px: int, py: int, mat: int = MAT_BONE) -> None:
        if 1 <= px < grid.width - 1 and 1 <= py < grid.height - 1:
            cur = grid.grid[py, px]
            if cur != MAT_WALL_BONE:
                grid.grid[py, px] = mat
                grid.life[py, px] = PROP_LIFETIME[mat]
                bone_pixels.append((px, py))

    # Determine skeletal structure based on enemy morphology
    if enemy_type in ("CHITIN_BEETLE", "PARASITE_SPIDER"):
        # Exoskeletal chitin carcass with fractured bone shards
        for dy in range(-2, 3):
            for dx in range(-3, 4):
                if abs(dx) == 3 or abs(dy) == 2:
                    if np.random.random() < 0.8:
                        set_bone(cx + dx, cy + dy, MAT_CHITIN)
        # Broken bone leg fragments
        for lx in (-4, -2, 2, 4):
            set_bone(cx + lx, cy + 3, MAT_BONE)
            set_bone(cx + lx + (1 if lx > 0 else -1), cy + 4, MAT_BONE_CHIP)

    elif enemy_type == "FLESH_WORM":
        # Vertebral column with segmented vertebrae
        for i in range(-5, 6):
            set_bone(cx + i, cy, MAT_BONE)
            if i % 2 == 0:
                set_bone(cx + i, cy - 1, MAT_BONE)
                set_bone(cx + i, cy + 1, MAT_BONE)

    elif enemy_type == "MACROPHAGE":
        # Calcified amoebic mineralized nucleus and loose bone chips
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                set_bone(cx + dx, cy + dy, MAT_BONE)
        # Scattered perimeter shards
        for _ in range(6):
            ox = np.random.randint(-4, 5)
            oy = np.random.randint(-3, 4)
            set_bone(cx + ox, cy + oy, MAT_BONE_CHIP)

    else:
        # Standard visceral vertebrate skeleton (Skull, Spine, Ribs, Pelvis)
        # Cranium
        for dx in (-1, 0, 1):
            set_bone(cx + dx, cy - 3, MAT_BONE)
        set_bone(cx - 1, cy - 2, MAT_BONE)
        set_bone(cx + 1, cy - 2, MAT_BONE)

        # Vertebral spine
        for dy in range(-2, 4):
            set_bone(cx, cy + dy, MAT_BONE)

        # Ribcage spurs
        set_bone(cx - 2, cy - 1, MAT_BONE)
        set_bone(cx + 2, cy - 1, MAT_BONE)
        set_bone(cx - 2, cy + 1, MAT_BONE)
        set_bone(cx + 2, cy + 1, MAT_BONE)

        # Pelvis & femur fragments
        set_bone(cx - 1, cy + 4, MAT_BONE)
        set_bone(cx + 1, cy + 4, MAT_BONE)
        set_bone(cx - 2, cy + 5, MAT_BONE_CHIP)
        set_bone(cx + 2, cy + 5, MAT_BONE_CHIP)

    # Permanent visceral wall decal splatter
    if blood_mat == MAT_MUTAGEN:
        stain = STAIN_MUTAGEN
    elif blood_mat == MAT_ACID:
        stain = STAIN_ACID
    elif blood_mat == MAT_PUS:
        stain = STAIN_SLIME
    else:
        stain = STAIN_BLOOD

    grid.apply_decal_splatter(cx, cy, radius=15, stain_type=stain, density=0.7)
    grid.mark_dirty(cx, cy, 10)
    return bone_pixels
