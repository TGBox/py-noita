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
)

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
)

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
)

BIOME_NEURAL_CORE = Biome(
    biome_id="NEURAL_CORE",
    name="Nervenkern & Ur-Zentrum (Gehirn)",
    depth_level=4,
    ambient_color=(20, 16, 42),
    primary_solid=MAT_NERVE,
    secondary_solid=MAT_TENTACLE_FLESH,
    liquid_pool_mat=MAT_MUTAGEN,
    gas_mat=MAT_AIR,
    powder_mat=MAT_SPORES,
    enemy_types=["ANTIBODY", "GRANULOCYTE", "FLESH_WORM", "TUMOR_CYST"],
    loot_rarity_multiplier=2.0,
)

ALL_BIOMES = [BIOME_EPIDERMIS, BIOME_VASCULAR, BIOME_GASTRIC, BIOME_NEURAL_CORE]
