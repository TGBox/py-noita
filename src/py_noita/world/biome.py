"""Biome definitions, materials, hazard pools, and ambient colors."""

from dataclasses import dataclass, field
from typing import List, Tuple

from py_noita.simulation.materials import (
    MAT_ACID,
    MAT_AIR,
    MAT_ASH,
    MAT_BILE,
    MAT_BIOGAS,
    MAT_BLOOD,
    MAT_BONE,
    MAT_BONE_CHIP,
    MAT_CHITIN,
    MAT_EGGS,
    MAT_LYMPH,
    MAT_MUTAGEN,
    MAT_NERVE,
    MAT_PUS,
    MAT_SPORES,
    MAT_TENTACLE_FLESH,
    MAT_TISSUE,
    MAT_TOXIC_VAPOR,
    MAT_WALL_BONE,
)


@dataclass
class Biome:
    """Configuration for a procedural organ biome."""
    biome_id: str
    name: str
    depth_level: int
    ambient_color: Tuple[int, int, int]
    primary_solid: int
    secondary_solid: int
    liquid_pool_mat: int
    gas_mat: int
    powder_mat: int
    enemy_types: List[str]
    loot_rarity_multiplier: float = 1.0
    gravity_multiplier: float = 1.0
    is_side_path: bool = False
    generation_style: str = "DEFAULT"


# 1. Hauptpfad: Epidermis & Kutis
BIOME_EPIDERMIS = Biome(
    biome_id="EPIDERMIS",
    name="Epidermis & Kutis (Hautschicht)",
    depth_level=1,
    ambient_color=(38, 20, 26),
    primary_solid=MAT_TISSUE,
    secondary_solid=MAT_BONE,
    liquid_pool_mat=MAT_LYMPH,
    gas_mat=MAT_AIR,
    powder_mat=MAT_SPORES,
    enemy_types=["MACROPHAGE", "ANTIBODY"],
    loot_rarity_multiplier=1.0,
    gravity_multiplier=1.0,
    is_side_path=False,
    generation_style="DEFAULT",
)

# 2. Hauptpfad: Vaskulärer Muskel
BIOME_VASCULAR = Biome(
    biome_id="VASCULAR",
    name="Vaskulärer Muskel (Blutbahnen)",
    depth_level=2,
    ambient_color=(45, 12, 18),
    primary_solid=MAT_TISSUE,
    secondary_solid=MAT_BONE,
    liquid_pool_mat=MAT_BLOOD,
    gas_mat=MAT_AIR,
    powder_mat=MAT_EGGS,
    enemy_types=["MACROPHAGE", "ANTIBODY", "FLESH_WORM"],
    loot_rarity_multiplier=1.3,
    gravity_multiplier=1.0,
    is_side_path=False,
    generation_style="DEFAULT",
)

# 3. Hauptpfad: Magensäure-Kavernen
BIOME_GASTRIC = Biome(
    biome_id="GASTRIC",
    name="Magensäure-Kavernen (Verdauungstrakt)",
    depth_level=3,
    ambient_color=(24, 38, 14),
    primary_solid=MAT_TISSUE,
    secondary_solid=MAT_CHITIN,
    liquid_pool_mat=MAT_ACID,
    gas_mat=MAT_BIOGAS,
    powder_mat=MAT_ASH,
    enemy_types=["GRANULOCYTE", "MACROPHAGE", "TUMOR_CYST"],
    loot_rarity_multiplier=1.6,
    gravity_multiplier=1.0,
    is_side_path=False,
    generation_style="DEFAULT",
)

# 4. Nebenpfad: Toxische Gallen-Lagune (horizontaler Abzweig nach Biom 3)
BIOME_BILE_LAGOON = Biome(
    biome_id="BILE_LAGOON",
    name="Toxische Gallen-Lagune (Nebenpfad)",
    depth_level=4,
    ambient_color=(28, 42, 14),
    primary_solid=MAT_CHITIN,
    secondary_solid=MAT_TISSUE,
    liquid_pool_mat=MAT_BILE,
    gas_mat=MAT_TOXIC_VAPOR,
    powder_mat=MAT_ASH,
    enemy_types=["CHITIN_BEETLE", "GRANULOCYTE", "MACROPHAGE"],
    loot_rarity_multiplier=2.0,
    gravity_multiplier=1.0,
    is_side_path=True,
    generation_style="LAGOON",
)

# 5. Hauptpfad: Infizierte Lunge (niedrige Schwerkraft, Atemluft-Ströme)
BIOME_INFECTED_LUNG = Biome(
    biome_id="INFECTED_LUNG",
    name="Infizierte Lunge (Atemhöhlen)",
    depth_level=5,
    ambient_color=(35, 30, 42),
    primary_solid=MAT_TISSUE,
    secondary_solid=MAT_WALL_BONE,
    liquid_pool_mat=MAT_PUS,
    gas_mat=MAT_AIR,
    powder_mat=MAT_SPORES,
    enemy_types=["SPORE_POD", "ANTIBODY", "MACROPHAGE"],
    loot_rarity_multiplier=2.2,
    gravity_multiplier=0.68,
    is_side_path=False,
    generation_style="LUNG",
)

# 6. Hauptpfad: Knochen-Katakomben (Skelett-Labyrinth)
BIOME_BONE_CATACOMBS = Biome(
    biome_id="BONE_CATACOMBS",
    name="Knochen-Katakomben (Skelett-Labyrinth)",
    depth_level=6,
    ambient_color=(34, 30, 26),
    primary_solid=MAT_BONE,
    secondary_solid=MAT_WALL_BONE,
    liquid_pool_mat=MAT_BLOOD,
    gas_mat=MAT_AIR,
    powder_mat=MAT_BONE_CHIP,
    enemy_types=["FLESH_WORM", "GRANULOCYTE", "CHITIN_BEETLE"],
    loot_rarity_multiplier=2.5,
    gravity_multiplier=1.0,
    is_side_path=False,
    generation_style="LABYRINTH",
)

# 7. Hauptpfad: Wirbelsäule & Nervenbahnen (Hochspannungs-Synapsen)
BIOME_SPINE_NERVES = Biome(
    biome_id="SPINE_NERVES",
    name="Wirbelsäule & Nervenbahnen (Synapsen)",
    depth_level=7,
    ambient_color=(16, 26, 46),
    primary_solid=MAT_NERVE,
    secondary_solid=MAT_BONE,
    liquid_pool_mat=MAT_MUTAGEN,
    gas_mat=MAT_AIR,
    powder_mat=MAT_SPORES,
    enemy_types=["SYNAPTIC_SENTRY", "ANTIBODY", "TUMOR_CYST"],
    loot_rarity_multiplier=2.8,
    gravity_multiplier=1.0,
    is_side_path=False,
    generation_style="SPINE",
)

# 8. Hauptpfad: Das Ur-Zentrum (Gehirnkern & Boss-Kammer)
BIOME_PRIMORDIAL_CORE = Biome(
    biome_id="PRIMORDIAL_CORE",
    name="Das Ur-Zentrum (Gehirnkern & Boss-Kammer)",
    depth_level=8,
    ambient_color=(24, 12, 42),
    primary_solid=MAT_NERVE,
    secondary_solid=MAT_TENTACLE_FLESH,
    liquid_pool_mat=MAT_MUTAGEN,
    gas_mat=MAT_BIOGAS,
    powder_mat=MAT_EGGS,
    enemy_types=["SYNAPTIC_SENTRY", "FLESH_WORM", "GRANULOCYTE", "TUMOR_CYST"],
    loot_rarity_multiplier=3.5,
    gravity_multiplier=1.0,
    is_side_path=False,
    generation_style="CORE",
)

# Backwards compatibility alias
BIOME_NEURAL_CORE = BIOME_PRIMORDIAL_CORE

ALL_BIOMES: List[Biome] = [
    BIOME_EPIDERMIS,
    BIOME_VASCULAR,
    BIOME_GASTRIC,
    BIOME_BILE_LAGOON,
    BIOME_INFECTED_LUNG,
    BIOME_BONE_CATACOMBS,
    BIOME_SPINE_NERVES,
    BIOME_PRIMORDIAL_CORE,
]

MAIN_PATH_BIOMES: List[Biome] = [
    BIOME_EPIDERMIS,
    BIOME_VASCULAR,
    BIOME_GASTRIC,
    BIOME_INFECTED_LUNG,
    BIOME_BONE_CATACOMBS,
    BIOME_SPINE_NERVES,
    BIOME_PRIMORDIAL_CORE,
]

BIOME_BY_ID = {b.biome_id: b for b in ALL_BIOMES}

