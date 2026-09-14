"""Material definitions and properties for Py-Noita simulation."""

from dataclasses import dataclass
from typing import Dict, List, Tuple
import numpy as np


# States of Matter
STATE_EMPTY = 0
STATE_SOLID = 1
STATE_POWDER = 2
STATE_LIQUID = 3
STATE_GAS = 4
STATE_ENERGY = 5

# Decal / Stain Types for permanent wall scarring & staining
STAIN_NONE = 0
STAIN_BLOOD = 1
STAIN_SLIME = 2
STAIN_MUTAGEN = 3
STAIN_ACID = 4
STAIN_CHAR = 5

# Material IDs (uint8)
MAT_AIR = 0
MAT_TISSUE = 1
MAT_BONE = 2
MAT_CHITIN = 3
MAT_WALL_BONE = 4
MAT_NERVE = 5
MAT_TENTACLE_FLESH = 6

MAT_SPORES = 10
MAT_EGGS = 11
MAT_ASH = 12
MAT_BONE_CHIP = 13
MAT_GOLD = 14


MAT_BLOOD = 20
MAT_ACID = 21
MAT_BILE = 22
MAT_LYMPH = 23
MAT_PUS = 24
MAT_MUTAGEN = 25
MAT_WATER = 26

MAT_BIOGAS = 30
MAT_TOXIC_VAPOR = 31
MAT_SMOKE = 32

MAT_FIRE = 40
MAT_CORROSION = 41

# Maximum material ID
MAX_MATERIALS = 64

# Material properties table arrays for Numba JIT (1D lookup tables by Material ID)
# State of matter
PROP_STATE = np.zeros(MAX_MATERIALS, dtype=np.uint8)
# Density (higher sinks in lower)
PROP_DENSITY = np.zeros(MAX_MATERIALS, dtype=np.float32)
# Flammability (0 = immune, 1-100 = catch chance)
PROP_FLAMMABILITY = np.zeros(MAX_MATERIALS, dtype=np.uint8)
# Acid vulnerability (0 = immune, 1-100 = dissolve speed)
PROP_ACID_VULN = np.zeros(MAX_MATERIALS, dtype=np.uint8)
# Dispersion speed (horizontal spread for liquids/gases)
PROP_DISPERSION = np.zeros(MAX_MATERIALS, dtype=np.uint8)
# Base lifetime in ticks (for fire, smoke, gas, corrosion)
PROP_LIFETIME = np.zeros(MAX_MATERIALS, dtype=np.uint16)
# Bioluminescence glow strength (0-255)
PROP_GLOW = np.zeros(MAX_MATERIALS, dtype=np.uint8)

# Color palettes (Base RGB + variations for visceral procedural texturing)
MATERIAL_COLORS: Dict[int, List[Tuple[int, int, int]]] = {
    MAT_AIR: [(12, 8, 16)],
    MAT_TISSUE: [
        (160, 32, 45), (140, 25, 38), (175, 40, 55), (120, 20, 30), (190, 50, 60)
    ],
    MAT_BONE: [
        (215, 208, 185), (230, 222, 200), (195, 188, 165), (240, 235, 215)
    ],
    MAT_CHITIN: [
        (45, 35, 55), (60, 48, 70), (35, 28, 42), (75, 60, 85)
    ],
    MAT_WALL_BONE: [
        (90, 85, 80), (105, 100, 95), (75, 70, 65)
    ],
    MAT_NERVE: [
        (40, 200, 230), (30, 170, 210), (70, 225, 245), (20, 140, 180)
    ],
    MAT_TENTACLE_FLESH: [
        (130, 20, 110), (105, 15, 90), (150, 30, 130), (85, 10, 75)
    ],
    MAT_SPORES: [
        (180, 195, 45), (165, 180, 35), (195, 210, 60)
    ],
    MAT_EGGS: [
        (220, 160, 120), (205, 145, 105), (235, 175, 135)
    ],
    MAT_ASH: [
        (80, 80, 85), (65, 65, 70), (95, 95, 100)
    ],
    MAT_BONE_CHIP: [
        (220, 215, 195), (200, 195, 175), (235, 230, 210)
    ],
    MAT_GOLD: [
        (255, 215, 0), (240, 195, 20), (255, 235, 50), (220, 175, 10)
    ],
    MAT_BLOOD: [

        (170, 12, 24), (195, 18, 30), (145, 8, 18), (215, 25, 38)
    ],
    MAT_ACID: [
        (65, 245, 30), (90, 255, 50), (45, 220, 20), (110, 255, 70)
    ],
    MAT_BILE: [
        (160, 180, 20), (180, 200, 30), (140, 160, 15)
    ],
    MAT_LYMPH: [
        (220, 230, 200), (205, 220, 185), (235, 240, 215)
    ],
    MAT_PUS: [
        (210, 205, 120), (195, 190, 105), (225, 220, 135)
    ],
    MAT_MUTAGEN: [
        (190, 25, 230), (220, 50, 255), (160, 15, 200), (240, 80, 255)
    ],
    MAT_WATER: [
        (45, 95, 190), (60, 115, 210), (35, 80, 170)
    ],
    MAT_BIOGAS: [
        (190, 160, 90), (210, 180, 110), (170, 140, 75)
    ],
    MAT_TOXIC_VAPOR: [
        (110, 200, 80), (130, 220, 100), (90, 180, 65)
    ],
    MAT_SMOKE: [
        (55, 50, 55), (45, 40, 45), (65, 60, 65)
    ],
    MAT_FIRE: [
        (255, 210, 40), (255, 140, 20), (255, 70, 10), (255, 245, 100)
    ],
    MAT_CORROSION: [
        (180, 255, 100), (150, 240, 80), (210, 255, 130)
    ],
}

# Precomputed RGB lookup table (MAX_MATERIALS x 3, uint8) for ultra-fast rendering
LUT_COLORS = np.zeros((MAX_MATERIALS, 3), dtype=np.uint8)
for mid, colors in MATERIAL_COLORS.items():
    LUT_COLORS[mid] = colors[0]


def _init_property_tables() -> None:
    """Initialize lookup tables for physics and chemical reactions."""
    # Air
    PROP_STATE[MAT_AIR] = STATE_EMPTY
    PROP_DENSITY[MAT_AIR] = 0.0

    # Solids
    for mat in (MAT_TISSUE, MAT_BONE, MAT_CHITIN, MAT_WALL_BONE, MAT_NERVE, MAT_TENTACLE_FLESH):
        PROP_STATE[mat] = STATE_SOLID
        PROP_DENSITY[mat] = 100.0

    PROP_FLAMMABILITY[MAT_TISSUE] = 60
    PROP_ACID_VULN[MAT_TISSUE] = 85

    PROP_FLAMMABILITY[MAT_BONE] = 5
    PROP_ACID_VULN[MAT_BONE] = 30

    PROP_FLAMMABILITY[MAT_CHITIN] = 15
    PROP_ACID_VULN[MAT_CHITIN] = 5

    PROP_FLAMMABILITY[MAT_NERVE] = 80
    PROP_ACID_VULN[MAT_NERVE] = 90
    PROP_GLOW[MAT_NERVE] = 180

    PROP_FLAMMABILITY[MAT_TENTACLE_FLESH] = 70
    PROP_ACID_VULN[MAT_TENTACLE_FLESH] = 60
    PROP_GLOW[MAT_TENTACLE_FLESH] = 80

    # Powders
    for mat in (MAT_SPORES, MAT_EGGS, MAT_ASH, MAT_BONE_CHIP, MAT_GOLD):
        PROP_STATE[mat] = STATE_POWDER

    PROP_DENSITY[MAT_GOLD] = 9.0
    PROP_FLAMMABILITY[MAT_GOLD] = 0
    PROP_ACID_VULN[MAT_GOLD] = 0
    PROP_GLOW[MAT_GOLD] = 120


    PROP_DENSITY[MAT_SPORES] = 1.2
    PROP_FLAMMABILITY[MAT_SPORES] = 90
    PROP_ACID_VULN[MAT_SPORES] = 95
    PROP_GLOW[MAT_SPORES] = 60

    PROP_DENSITY[MAT_EGGS] = 2.0
    PROP_FLAMMABILITY[MAT_EGGS] = 40
    PROP_ACID_VULN[MAT_EGGS] = 70

    PROP_DENSITY[MAT_ASH] = 1.1
    PROP_FLAMMABILITY[MAT_ASH] = 0
    PROP_ACID_VULN[MAT_ASH] = 10

    PROP_DENSITY[MAT_BONE_CHIP] = 3.5
    PROP_FLAMMABILITY[MAT_BONE_CHIP] = 5
    PROP_ACID_VULN[MAT_BONE_CHIP] = 35

    # Liquids
    for mat in (MAT_BLOOD, MAT_ACID, MAT_BILE, MAT_LYMPH, MAT_PUS, MAT_MUTAGEN, MAT_WATER):
        PROP_STATE[mat] = STATE_LIQUID

    PROP_DENSITY[MAT_BLOOD] = 2.1
    PROP_DISPERSION[MAT_BLOOD] = 4

    PROP_DENSITY[MAT_ACID] = 2.4
    PROP_DISPERSION[MAT_ACID] = 5
    PROP_GLOW[MAT_ACID] = 200

    PROP_DENSITY[MAT_BILE] = 2.2
    PROP_DISPERSION[MAT_BILE] = 3
    PROP_FLAMMABILITY[MAT_BILE] = 30
    PROP_GLOW[MAT_BILE] = 50

    PROP_DENSITY[MAT_LYMPH] = 1.9
    PROP_DISPERSION[MAT_LYMPH] = 5

    PROP_DENSITY[MAT_PUS] = 2.0
    PROP_DISPERSION[MAT_PUS] = 2

    PROP_DENSITY[MAT_MUTAGEN] = 2.5
    PROP_DISPERSION[MAT_MUTAGEN] = 4
    PROP_GLOW[MAT_MUTAGEN] = 230

    PROP_DENSITY[MAT_WATER] = 1.8
    PROP_DISPERSION[MAT_WATER] = 5

    # Gases
    for mat in (MAT_BIOGAS, MAT_TOXIC_VAPOR, MAT_SMOKE):
        PROP_STATE[mat] = STATE_GAS

    PROP_DENSITY[MAT_BIOGAS] = 0.4
    PROP_DISPERSION[MAT_BIOGAS] = 3
    PROP_FLAMMABILITY[MAT_BIOGAS] = 100   # Highly flammable / explosive
    PROP_LIFETIME[MAT_BIOGAS] = 900       # Survives 15 seconds unless ignited

    PROP_DENSITY[MAT_TOXIC_VAPOR] = 0.6
    PROP_DISPERSION[MAT_TOXIC_VAPOR] = 2
    PROP_LIFETIME[MAT_TOXIC_VAPOR] = 600
    PROP_GLOW[MAT_TOXIC_VAPOR] = 90

    PROP_DENSITY[MAT_SMOKE] = 0.5
    PROP_DISPERSION[MAT_SMOKE] = 3
    PROP_LIFETIME[MAT_SMOKE] = 350

    # Energy / Fire / Reactions
    PROP_STATE[MAT_FIRE] = STATE_ENERGY
    PROP_DENSITY[MAT_FIRE] = 0.2
    PROP_LIFETIME[MAT_FIRE] = 45
    PROP_GLOW[MAT_FIRE] = 255

    PROP_STATE[MAT_CORROSION] = STATE_ENERGY
    PROP_DENSITY[MAT_CORROSION] = 1.0
    PROP_LIFETIME[MAT_CORROSION] = 30
    PROP_GLOW[MAT_CORROSION] = 160


_init_property_tables()

# German display names for materials and fluids
MATERIAL_NAMES: Dict[int, str] = {
    MAT_AIR: "",
    MAT_TISSUE: "Gewebe",
    MAT_BONE: "Knochen",
    MAT_CHITIN: "Chitin",
    MAT_WALL_BONE: "Dichter Knochen",
    MAT_NERVE: "Nervengewebe",
    MAT_TENTACLE_FLESH: "Tentakelfleisch",
    MAT_SPORES: "Sporen",
    MAT_EGGS: "Parasiteneier",
    MAT_ASH: "Asche",
    MAT_BONE_CHIP: "Knochensplitter",
    MAT_GOLD: "Biomasse-Gold",
    MAT_BLOOD: "Blut",

    MAT_ACID: "Säure",
    MAT_BILE: "Galle",
    MAT_LYMPH: "Lymphe",
    MAT_PUS: "Eiter",
    MAT_MUTAGEN: "Mutagen",
    MAT_WATER: "Wasser",
    MAT_BIOGAS: "Biogas",
    MAT_TOXIC_VAPOR: "Giftiger Dampf",
    MAT_SMOKE: "Rauch",
    MAT_FIRE: "Feuer",
    MAT_CORROSION: "Korrosion",
}

# German state of matter labels
STATE_NAMES: Dict[int, str] = {
    STATE_EMPTY: "Vakuum",
    STATE_SOLID: "Feststoff",
    STATE_POWDER: "Pulver",
    STATE_LIQUID: "Flüssigkeit",
    STATE_GAS: "Gas",
    STATE_ENERGY: "Energie",
}


def get_material_name(mat_id: int) -> str:
    """Return German display name of material, or fallback string."""
    return MATERIAL_NAMES.get(mat_id, f"Material {mat_id}")


def get_material_category(mat_id: int) -> str:
    """Return state of matter category name."""
    if 0 <= mat_id < MAX_MATERIALS:
        state = PROP_STATE[mat_id]
        return STATE_NAMES.get(int(state), "")
    return ""
