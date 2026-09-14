"""Alternative Ending Sequences and Endgame Quests for Py-Noita:
- Ending 1 (Host Death): Destruction of the Primordial Core.
- Ending 2 (Symbiosis): Activation of all 11 DNA Orbs at the Neural Nexus.
- Ending 3 (Cosmic Metamorphosis): Ascending to the outer surface with the Primordial Genome.
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import pygame

ENDING_NONE = 0
ENDING_HOST_DEATH = 1
ENDING_SYMBIOSIS = 2
ENDING_COSMIC_METAMORPHOSIS = 3


@dataclass
class EndingInfo:
    ending_id: int
    title: str
    sub_title: str
    lore_text: str
    color: Tuple[int, int, int]
    bonus_mutagen: int
    achievement_unlocked: str


ENDINGS = {
    ENDING_HOST_DEATH: EndingInfo(
        ending_id=ENDING_HOST_DEATH,
        title="ENDE 1: WIRTSTOD",
        sub_title="Zerstörung des Ur-Zentrums // Totale Nekrose",
        lore_text=(
            "Der zentrale Gehirnkern des Wirts wurde vollständig vernichtet. "
            "Ohne neurale Steuerung erliegen die vitalen Organe der Selbstzersetzung. "
            "Der gigantische Körper kollabiert in eine Flut aus nekrotischem Schleim."
        ),
        color=(255, 60, 60),
        bonus_mutagen=100,
        achievement_unlocked="Wirts-Kollaps",
    ),
    ENDING_SYMBIOSIS: EndingInfo(
        ending_id=ENDING_SYMBIOSIS,
        title="ENDE 2: SYMBIOTISCHE VERSCHMELZUNG",
        sub_title="Vollständige Harmonie // Die ewige Einheit",
        lore_text=(
            "Mit der gesammelten Macht aller 11 uralten DNA-Orbs verbindet sich "
            "der Symbiot mit den Synapsen des Wirtsgehirns. Parasit und Wirt "
            "verschmelzen zu einem unsterblichen, unüberwindbaren Kosmos-Wesen."
        ),
        color=(60, 220, 255),
        bonus_mutagen=350,
        achievement_unlocked="Ewige Symbiose",
    ),
    ENDING_COSMIC_METAMORPHOSIS: EndingInfo(
        ending_id=ENDING_COSMIC_METAMORPHOSIS,
        title="ENDE 3: KOSMISCHE METAMORPHOSE",
        sub_title="Der große Aufstieg // Geburt einer Sternen-Kreatur",
        lore_text=(
            "Mit dem Ur-Genom durchbrach der Symbiot die schützende Kutisschicht "
            "und stieg in das endlose Vakuum auf. Unter dem Sternenlicht entfalten "
            "sich biomolekulare Schwingen zu einer majestätischen kosmischen Entität."
        ),
        color=(255, 215, 60),
        bonus_mutagen=500,
        achievement_unlocked="Kosmischer Aufstieg",
    ),
}


class SurfaceAscentPortal:
    """Gateway placed at the high ceiling of Biome 1 (Epidermis).
    Triggers Ending 3 if the player carries the Primordial Genome.
    """

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.radius = 18.0
        self.anim_time: float = 0.0

    def update(self) -> None:
        self.anim_time += 0.06

    def is_player_inside(self, px: float, py: float) -> bool:
        import math
        return math.hypot(px - self.x, py - self.y) < self.radius

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int, font: pygame.font.Font) -> None:
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)

        import math
        pulse = math.sin(self.anim_time * 2.5) * 3.0
        # Golden starry cosmic portal
        pygame.draw.circle(surface, (255, 220, 80), (sx, sy), int(self.radius + pulse), 2)
        pygame.draw.circle(surface, (255, 255, 200), (sx, sy), int(self.radius * 0.6))
        pygame.draw.circle(surface, (140, 60, 255), (sx, sy), int(self.radius * 0.25))

        if -40 <= sx <= surface.get_width() + 40:
            lbl = font.render("[KOSMISCHES PORTAL // AUFSTIEG]", True, (255, 230, 100))
            surface.blit(lbl, (sx - lbl.get_width() // 2, sy - 24))


class AscentReturnGateway:
    """Return conduit placed after the final boss that teleports the bearer of the Primordial Genome back to Biome 1."""

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.radius = 16.0
        self.anim_time: float = 0.0

    def update(self) -> None:
        self.anim_time += 0.05

    def is_player_inside(self, px: float, py: float) -> bool:
        import math
        return math.hypot(px - self.x, py - self.y) < self.radius

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int, font: pygame.font.Font) -> None:
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)
        import math
        pulse = math.sin(self.anim_time * 2.5) * 3.0
        pygame.draw.circle(surface, (255, 200, 50), (sx, sy), int(self.radius + pulse), 2)
        pygame.draw.circle(surface, (180, 240, 255), (sx, sy), int(self.radius * 0.5))
        if -40 <= sx <= surface.get_width() + 40:
            lbl = font.render("[AUFSTIEGS-KANAL // ZUR OBERFLÄCHE]", True, (255, 220, 100))
            surface.blit(lbl, (sx - lbl.get_width() // 2, sy - 22))

