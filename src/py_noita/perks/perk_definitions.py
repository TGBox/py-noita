"""Mutation Perk definitions and effect hooks."""

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple
import random


@dataclass
class MutationPerk:
    """A genetic mutation selected in the Incubation Node."""
    id: str
    name: str
    description: str
    is_high_risk: bool
    color: Tuple[int, int, int]


ALL_PERKS: List[MutationPerk] = [
    # Regular Perks
    MutationPerk(
        id="ACID_IMMUNITY",
        name="Säure-Immunität",
        description="Vollständiger Schutz vor Zersetzung und Verätzung durch Magensäure.",
        is_high_risk=False,
        color=(75, 255, 35),
    ),
    MutationPerk(
        id="FLAGELLA_TURBO",
        name="Geißel-Turboschub",
        description="40% schnellere Levitation und 50% langsamere Ausdauerzehrung.",
        is_high_risk=False,
        color=(80, 220, 255),
    ),
    MutationPerk(
        id="BIO_MAGNET",
        name="Bio-Magnet",
        description="Zieht gelöste Biomasse-Nährstoffe und Bluttröpfchen automatisch an.",
        is_high_risk=False,
        color=(255, 140, 220),
    ),
    MutationPerk(
        id="CYTOKINE_SHIELD",
        name="Zytokin-Membranschild",
        description="Erzeugt eine biologische Schutzmembran, die alle 10 Sekunden einen Treffer abfängt.",
        is_high_risk=False,
        color=(255, 220, 90),
    ),
    MutationPerk(
        id="SPORE_TRAIL",
        name="Sporen-Schweif",
        description="Hinterlässt beim Schwebeflug eine Wolke aus infektiösen Fäulnis-Sporen.",
        is_high_risk=False,
        color=(190, 215, 50),
    ),
    MutationPerk(
        id="VAMPIRIC_METABOLISM",
        name="Vampir-Metabolismus",
        description="Blut heilt doppelt so effektiv und stellt zusätzliche Biomasse wieder her.",
        is_high_risk=False,
        color=(220, 30, 45),
    ),

    # High-Risk / High-Reward Trade-Offs
    MutationPerk(
        id="GIANT_SYMBIOTE",
        name="Riesen-Symbiot [Trade-Off]",
        description="+150% Max HP und doppelte Projektilgröße, aber -25% Bewegungsgeschwindigkeit.",
        is_high_risk=True,
        color=(240, 70, 70),
    ),
    MutationPerk(
        id="HYPER_METABOLISM",
        name="Hyper-Metabolismus [Trade-Off]",
        description="Waffen feuern 50% schneller. Bei leerer Biomasse wird HP als Energie verzehrt!",
        is_high_risk=True,
        color=(255, 160, 20),
    ),
    MutationPerk(
        id="GLASS_CARAPACE",
        name="Gläserner Chitinpanzer [Trade-Off]",
        description="+250% aller ausgeteilter Schaden, aber maximale HP werden auf 30 begrenzt!",
        is_high_risk=True,
        color=(220, 50, 255),
    ),
    MutationPerk(
        id="TENTACLE_RETALIATION",
        name="Tentakel-Vergeltung",
        description="Bei jedem erlittenen Treffer bricht eine Spirale aus 8 Knochenspießen hervor.",
        is_high_risk=False,
        color=(200, 100, 180),
    ),
]


def getRandomPerks(count: int = 3) -> List[MutationPerk]:
    """Return randomized selection of perks for the Incubation Node."""
    return random.sample(ALL_PERKS, min(count, len(ALL_PERKS)))
