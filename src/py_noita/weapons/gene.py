"""Gene and Enzyme cards (equivalent to Noita Spells) for Organ-Cannulas."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from py_noita.simulation.materials import (
    MAT_ACID,
    MAT_AIR,
    MAT_BILE,
    MAT_BLOOD,
    MAT_BONE,
    MAT_BONE_CHIP,
    MAT_FIRE,
    MAT_MUTAGEN,
    MAT_NERVE,
    MAT_SPORES,
)


class GeneType(Enum):
    PROJECTILE = "PROJECTILE"
    TRIGGER = "TRIGGER"
    MODIFIER = "MODIFIER"
    MULTICAST = "MULTICAST"
    PASSIVE = "PASSIVE"


@dataclass
class Gene:
    """A genetic sequence card installed in an Organ-Cannula."""
    id: str
    name: str
    gene_type: GeneType
    description: str

    # Energy & timing
    biomass_cost: float = 10.0
    cast_delay_mod: float = 0.0      # Added to cannula cast delay (seconds)
    recharge_mod: float = 0.0        # Added to cannula recharge time (seconds)

    # Projectile properties (for PROJECTILE and TRIGGER types)
    damage: float = 12.0
    speed: float = 6.0
    lifetime: int = 70               # Ticks
    radius: float = 2.5
    spread_mod: float = 0.0
    bounce: int = 0
    piercing: bool = False
    homing: bool = False
    trail_material: int = MAT_AIR
    impact_material: int = MAT_AIR
    impact_material_count: int = 0
    explosion_radius: int = 0

    # Multicast count (for MULTICAST types)
    multicast_count: int = 1

    # Icon RGB color for UI rendering
    color: Tuple[int, int, int] = (200, 200, 200)


# Library of all Bio-Horror Genes
GENE_LIBRARY: List[Gene] = [
    # --- Projectiles ---
    Gene(
        id="BONE_SPIKE",
        name="Knochenspeer",
        gene_type=GeneType.PROJECTILE,
        description="Ein spitzer Knochensplitter mit hoher Geschwindigkeit und moderatem Schaden.",
        biomass_cost=8.0,
        cast_delay_mod=0.04,
        damage=15.0,
        speed=8.5,
        lifetime=65,
        radius=2.0,
        impact_material=MAT_BONE_CHIP,
        impact_material_count=4,
        color=(235, 230, 215),
    ),
    Gene(
        id="ACID_GLOBULE",
        name="Säuregalle",
        gene_type=GeneType.PROJECTILE,
        description="Schwerer Magensäure-Ballen, der bei Aufprall in ätzende Säure zerspritzt.",
        biomass_cost=20.0,
        cast_delay_mod=0.18,
        damage=22.0,
        speed=4.5,
        lifetime=55,
        radius=3.5,
        impact_material=MAT_ACID,
        impact_material_count=16,
        color=(70, 255, 30),
    ),
    Gene(
        id="BILE_NEEDLE",
        name="Gallen-Nadel",
        gene_type=GeneType.PROJECTILE,
        description="Feine, giftige Galle-Projektile mit minimalem Rückstoß und schneller Kadenz.",
        biomass_cost=5.0,
        cast_delay_mod=-0.04,
        damage=7.0,
        speed=10.0,
        lifetime=45,
        radius=1.5,
        impact_material=MAT_BILE,
        impact_material_count=3,
        color=(170, 200, 25),
    ),
    Gene(
        id="PARASITE_LEECH",
        name="Parasiten-Egel",
        gene_type=GeneType.PROJECTILE,
        description="Kriecht durch Gewebe, saugt Blutzellen an und hinterlässt Blutspuren.",
        biomass_cost=15.0,
        cast_delay_mod=0.12,
        damage=18.0,
        speed=5.0,
        lifetime=90,
        radius=3.0,
        trail_material=MAT_BLOOD,
        impact_material=MAT_BLOOD,
        impact_material_count=8,
        color=(185, 25, 45),
    ),
    Gene(
        id="NERVE_BOLT",
        name="Nerven-Blitz",
        gene_type=GeneType.PROJECTILE,
        description="Elektrisierender Nervenimpuls, der organisches Gewebe durchzuckt.",
        biomass_cost=18.0,
        cast_delay_mod=0.08,
        damage=25.0,
        speed=12.0,
        lifetime=35,
        radius=2.0,
        piercing=True,
        color=(40, 220, 255),
    ),
    Gene(
        id="BONE_BOMB",
        name="Knochen-Tumor (Bombe)",
        gene_type=GeneType.PROJECTILE,
        description="Explosive Knochenkapsel mit verheerender Druckwelle und Kraterbildung.",
        biomass_cost=45.0,
        cast_delay_mod=0.45,
        damage=75.0,
        speed=4.0,
        lifetime=80,
        radius=5.0,
        explosion_radius=18,
        color=(245, 120, 60),
    ),

    # --- Triggers ---
    Gene(
        id="TRIGGER_HIT_BONE",
        name="Knochenspeer [Treffer-Trigger]",
        gene_type=GeneType.TRIGGER,
        description="Knochenspeer, der beim Einschlag die nachfolgende Gen-Sequenz zündet.",
        biomass_cost=12.0,
        cast_delay_mod=0.06,
        damage=12.0,
        speed=8.0,
        lifetime=65,
        radius=2.0,
        color=(255, 220, 160),
    ),
    Gene(
        id="TRIGGER_TIMER_SPORE",
        name="Sporen-Kapsel [Timer-Trigger]",
        gene_type=GeneType.TRIGGER,
        description="Fliegt vorwärts und detoniert nach 30 Ticks in die nächste Gen-Sequenz.",
        biomass_cost=14.0,
        cast_delay_mod=0.08,
        damage=8.0,
        speed=6.0,
        lifetime=30,
        radius=2.5,
        trail_material=MAT_SPORES,
        color=(190, 215, 50),
    ),

    # --- Modifiers ---
    Gene(
        id="MOD_HOMING",
        name="Pheromon-Peilung",
        gene_type=GeneType.MODIFIER,
        description="Verleiht Projektilen die Fähigkeit, organisch auf Feinde zuzufliegen.",
        biomass_cost=10.0,
        cast_delay_mod=0.05,
        homing=True,
        color=(220, 40, 220),
    ),
    Gene(
        id="MOD_NECROTIC_BURN",
        name="Nekrotischer Brand",
        gene_type=GeneType.MODIFIER,
        description="Entzündet Projektile mit nekrotischem Feuer, das Fleisch in Brand steckt.",
        biomass_cost=12.0,
        cast_delay_mod=0.02,
        damage=6.0,
        trail_material=MAT_FIRE,
        impact_material=MAT_FIRE,
        impact_material_count=4,
        color=(255, 140, 30),
    ),
    Gene(
        id="MOD_PIERCING_SPINE",
        name="Durchdringende Chitinspitze",
        gene_type=GeneType.MODIFIER,
        description="Lässt Projektile durch weiches Fleisch hindurchschlagen.",
        biomass_cost=15.0,
        cast_delay_mod=0.10,
        piercing=True,
        damage=5.0,
        color=(140, 180, 220),
    ),
    Gene(
        id="MOD_MUTAGEN_COATING",
        name="Mutagen-Mantel",
        gene_type=GeneType.MODIFIER,
        description="Überzieht Projektile mit Mutagenschleim, der Gewebe in Tentakel verwandelt.",
        biomass_cost=25.0,
        cast_delay_mod=0.15,
        damage=10.0,
        trail_material=MAT_MUTAGEN,
        impact_material=MAT_MUTAGEN,
        impact_material_count=12,
        color=(230, 60, 255),
    ),
    Gene(
        id="MOD_SPEED_METABOLISM",
        name="Beschleunigter Stoffwechsel",
        gene_type=GeneType.MODIFIER,
        description="Erhöht Geschwindigkeit um 60% und reduziert Abklingzeit.",
        biomass_cost=6.0,
        cast_delay_mod=-0.06,
        recharge_mod=-0.08,
        speed=1.6,  # Multiplier applied in evaluator
        color=(80, 250, 210),
    ),

    # --- Multicasts ---
    Gene(
        id="MULTI_DOUBLE",
        name="Doppel-Injektion",
        gene_type=GeneType.MULTICAST,
        description="Feuert die nächsten 2 Gene gleichzeitig ab.",
        biomass_cost=4.0,
        multicast_count=2,
        spread_mod=4.0,
        color=(240, 180, 60),
    ),
    Gene(
        id="MULTI_TRIPLE",
        name="Dreifach-Kanal",
        gene_type=GeneType.MULTICAST,
        description="Feuert die nächsten 3 Gene im Fächer ab.",
        biomass_cost=8.0,
        multicast_count=3,
        spread_mod=8.0,
        color=(250, 140, 50),
    ),
    # --- Primordial Secret Ur-Genes (Orb Rewards) ---
    Gene(
        id="PRIMORDIAL_BEAM",
        name="Ur-Plasma-Strahl",
        gene_type=GeneType.PROJECTILE,
        description="Uralte hochenergetische Entladung, die Gewebe durchdringt und Mutagen-Rückstände hinterlässt.",
        biomass_cost=32.0,
        cast_delay_mod=0.18,
        recharge_mod=0.25,
        damage=45.0,
        speed=10.0,
        lifetime=110,
        radius=4.0,
        piercing=True,
        trail_material=MAT_MUTAGEN,
        impact_material=MAT_MUTAGEN,
        impact_material_count=5,
        color=(230, 60, 255),
    ),
    Gene(
        id="UR_CYTOKINE",
        name="Ur-Zytokin-Nova",
        gene_type=GeneType.PROJECTILE,
        description="Gewaltige bio-zytotoxische Kugel mit zielsuchendem Vektor und verheerender Sprengkraft.",
        biomass_cost=40.0,
        cast_delay_mod=0.35,
        recharge_mod=0.45,
        damage=65.0,
        speed=5.0,
        lifetime=140,
        radius=6.0,
        homing=True,
        explosion_radius=22,
        color=(255, 230, 40),
    ),
    Gene(
        id="MUTAGEN_COLLAPSE",
        name="Mutagen-Zellkollaps",
        gene_type=GeneType.TRIGGER,
        description="Löst bei Aufprall eine schwere nukleotidische Implosion aus, die Terrain zerschmettert.",
        biomass_cost=38.0,
        cast_delay_mod=0.22,
        recharge_mod=0.35,
        damage=55.0,
        speed=7.5,
        lifetime=85,
        radius=4.5,
        explosion_radius=28,
        trail_material=MAT_MUTAGEN,
        color=(180, 20, 240),
    ),
]

GENE_DICT = {gene.id: gene for gene in GENE_LIBRARY}
