"""Exploration secrets: 11 Hidden Gene Orbs, Ancient DNA Lore Tablets, and secret chambers."""

import math
import random
from typing import List, Optional, Tuple
import pygame

from py_noita.entities.player import Player
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import MAT_AIR, MAT_WALL_BONE
from py_noita.weapons.gene import GENE_DICT, Gene


class GeneOrb:
    """A hidden ancient DNA orb that awards a primordial gene, increases max HP,
    and scales the final boss difficulty.
    """

    def __init__(
        self,
        orb_id: int,
        x: float,
        y: float,
        reward_gene_id: str,
        name: str,
        description: str,
    ):
        self.orb_id = orb_id
        self.x = x
        self.y = y
        self.reward_gene_id = reward_gene_id
        self.name = name
        self.description = description
        self.radius = 9.0
        self.collected: bool = False
        self.anim_time: float = random.uniform(0.0, 10.0)

    def update(self, player: Player) -> Optional[Gene]:
        """Check player proximity collection."""
        if self.collected or not player.alive:
            return None

        self.anim_time += 0.08
        dist = math.hypot(player.center_x - self.x, player.center_y - self.y)
        if dist < (self.radius + player.width / 2.0 + 4.0):
            self.collected = True
            player.orbs_collected = getattr(player, "orbs_collected", 0) + 1
            # Permanent vitality boost
            player.max_hp += 25.0
            player.hp = min(player.max_hp, player.hp + 25.0)

            # Retrieve reward gene
            gene = GENE_DICT.get(self.reward_gene_id)
            if gene:
                # Add to first free slot in active cannula or player cannulas
                added = False
                for cannula in player.cannulas:
                    if cannula.add_gene(gene):
                        added = True
                        break
                if not added and player.cannulas:
                    player.cannulas[player.active_cannula_index].slots[0] = gene
            return gene
        return None

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int, font: Optional[pygame.font.Font] = None) -> None:
        if self.collected:
            return

        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)

        # Pulsating glowing aura
        pulse = math.sin(self.anim_time * 3.0) * 3.0
        r_outer = int(self.radius + 4.0 + pulse)
        pygame.draw.circle(surface, (120, 40, 220), (sx, sy), max(1, r_outer), 1)
        pygame.draw.circle(surface, (240, 190, 50), (sx, sy), int(self.radius))
        pygame.draw.circle(surface, (255, 255, 230), (sx, sy), max(1, int(self.radius * 0.45)))

        # Double-helix orbiting nodes
        for i in (0, 1):
            theta = self.anim_time * 2.5 + i * math.pi
            nx = sx + int(math.cos(theta) * (self.radius + 3.0))
            ny = sy + int(math.sin(theta) * 4.0)
            pygame.draw.circle(surface, (100, 240, 255), (nx, ny), 2)

        if font and -40 <= sx <= surface.get_width() + 40:
            lbl = font.render(f"DNA-ORB #{self.orb_id + 1}", True, (255, 230, 120))
            surface.blit(lbl, (sx - lbl.get_width() // 2, sy - 18))


class DnaTablet:
    """An ancient carved lore tablet revealing the origin of the host organism."""

    def __init__(self, tablet_id: int, x: float, y: float, title: str, text: str):
        self.tablet_id = tablet_id
        self.x = x
        self.y = y
        self.title = title
        self.text = text
        self.width = 16
        self.height = 22
        self.alive: bool = True
        self.is_near_player: bool = False
        self.is_hovered: bool = False

    def contains_point(self, wx: float, wy: float) -> bool:
        return (self.x - 4 <= wx <= self.x + self.width + 4 and
                self.y - 4 <= wy <= self.y + self.height + 4)

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int, font: Optional[pygame.font.Font] = None) -> None:
        if not self.alive:
            return

        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)

        # Pulsing golden aura
        ticks = pygame.time.get_ticks()
        pulse = (math.sin(ticks * 0.005 + self.tablet_id) + 1.0) * 0.5
        glow_r = int(14 + pulse * 4)
        glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (240, 200, 70, int(30 + pulse * 30)), (glow_r, glow_r), glow_r)
        surface.blit(glow_surf, (sx + self.width // 2 - glow_r, sy + self.height // 2 - glow_r))

        # Carved bone tablet rect
        rect = pygame.Rect(sx, sy, self.width, self.height)
        pygame.draw.rect(surface, (75, 70, 65), rect, border_radius=2)
        pygame.draw.rect(surface, (230, 210, 140), rect, 1, border_radius=2)

        # Inscribed glowing runes
        pygame.draw.line(surface, (255, 210, 80), (sx + 4, sy + 6), (sx + 12, sy + 6), 1)
        pygame.draw.line(surface, (255, 210, 80), (sx + 5, sy + 11), (sx + 11, sy + 11), 1)
        pygame.draw.line(surface, (255, 210, 80), (sx + 4, sy + 16), (sx + 12, sy + 16), 1)

        # Interaction Prompt when player is close
        if self.is_near_player and font:
            prompt_surf = font.render(f"[E] {self.title} entziffern", True, (255, 235, 140))
            bg_w = prompt_surf.get_width() + 10
            bg_h = prompt_surf.get_height() + 4
            bg_x = sx + self.width // 2 - bg_w // 2
            bg_y = sy - 18
            bg_surf = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
            bg_surf.fill((20, 15, 25, 220))
            pygame.draw.rect(bg_surf, (220, 180, 80), (0, 0, bg_w, bg_h), 1, border_radius=3)
            bg_surf.blit(prompt_surf, (5, 2))
            surface.blit(bg_surf, (bg_x, bg_y))


# The 8 Ancient Lore Tablets
ANCIENT_TABLETS_DATA = [
    (
        0,
        "I. Die Genesis des Wirtsfleisches",
        "Am Anfang war nur der gigantische Wirt, schlafend in der Leere. Seine Haut war ein endloser Kontinent aus Keratin.",
    ),
    (
        1,
        "II. Der Strom der roten Lebensflut",
        "Das Blut des Wirts pulsiert mit unendlicher Schöpfungskraft. Aus jeder Ader entspringen Myriaden von Fresszellen.",
    ),
    (
        2,
        "III. Das ätzende Vergessen",
        "In den Tiefen des Magens zerfallen alle Dinge. Doch die Säure tötet nicht nur — sie reinigt und verwandelt Materie.",
    ),
    (
        3,
        "IV. Die verbotene Galle",
        "Hinter den Gallenwegen liegt die toxische Lagune. Wer ihren ätzenden Dämpfen trotzt, findet Chitin von unzerbrechlicher Härte.",
    ),
    (
        4,
        "V. Der Hauch des Titanen",
        "Die Höhlen der Lunge dehnen und senken sich mit jedem Äon. Die Schwerkraft verliert hier ihre irdischen Fesseln.",
    ),
    (
        5,
        "VI. Das Beinhaus der Vergessenen",
        "Tief im Skelett des Wirts ruhen die Knochen uralter Parasiten. Der Riesenwurm Helminth durchdringt das Gebein.",
    ),
    (
        6,
        "VII. Die bio-elektrische Krone",
        "Die Wirbelsäule leitet die Befehle des unendlichen Geistes. Eine einzige Synapse birgt die Energie von tausend Blitzen.",
    ),
    (
        7,
        "VIII. Das Herz des Kosmos",
        "Im Kern des Gehirns schlägt das kosmische Bewusstsein. Wer die elf Ur-Orbs vereint, wird mit dem Wirt verschmelzen.",
    ),
]


# The 11 Hidden Gene Orbs
ORBS_DATA = [
    (0, "EPIDERMIS", "BILE_NEEDLE", "Ur-Gen-Orb I: Kutis-Nadel", "Erweckt die zytoplasmatische Nadel der Außenhaut."),
    (1, "VASCULAR", "PARASITE_LEECH", "Ur-Gen-Orb II: Hämo-Egel", "Verbindet den Symbioten mit den vitalen Blutströmen."),
    (2, "GASTRIC", "ACID_GLOBULE", "Ur-Gen-Orb III: Magensäure-Ballen", "Kondensiert die ätzende Magensäure zu reiner Zersetzungskraft."),
    (3, "BILE_LAGOON", "MOD_PIERCING_SPINE", "Ur-Gen-Orb IV: Chitinspitze", "Härtet Chitinfragmente mit unbändiger Durchdringungskraft."),
    (4, "BILE_LAGOON", "UR_CYTOKINE", "Ur-Gen-Orb V: Galle-Nova", "Entfesselt die verheerende Ur-Zytokin-Detonation."),
    (5, "INFECTED_LUNG", "TRIGGER_TIMER_SPORE", "Ur-Gen-Orb VI: Sporen-Timer", "Erschafft schwebende zeitgesteuerte Sporenkammern."),
    (6, "INFECTED_LUNG", "MUTAGEN_COLLAPSE", "Ur-Gen-Orb VII: Pneumo-Kraft", "Erzeugt eine nukleotidische Zellkollaps-Reaktion."),
    (7, "BONE_CATACOMBS", "BONE_BOMB", "Ur-Gen-Orb VIII: Osteo-Titan", "Bündelt das Knochenmark zu explosiven Splitterkernen."),
    (8, "BONE_CATACOMBS", "PRIMORDIAL_BEAM", "Ur-Gen-Orb IX: Helminth-DNA", "Kanalisiert den durchdringenden Ur-Plasma-Strahl des Riesenwurms."),
    (9, "SPINE_NERVES", "NERVE_BOLT", "Ur-Gen-Orb X: Synapsen-Nexus", "Verstärkt die bio-elektrische Neuro-Spannung aller Projektile."),
    (10, "PRIMORDIAL_CORE", "MOD_MUTAGEN_COATING", "Ur-Gen-Orb XI: Der Ur-Code", "Der elfte Schlüssel: Vollendet die Metamorphose des Symbioten."),
]


def spawn_secrets_for_biome(
    grid: SimulationGrid,
    biome_id: str,
    depth: int,
    seed: Optional[int] = None,
) -> Tuple[List[GeneOrb], List[DnaTablet]]:
    """Procedurally carve a secret chamber and place Gene Orbs and DNA Tablets."""
    if seed is not None:
        random.seed(seed + 9876)

    w = grid.width
    h = grid.height
    orbs: List[GeneOrb] = []
    tablets: List[DnaTablet] = []

    # 1. Spawn matching DNA Tablet for this biome depth (depth 1 to 8 -> index 0 to 7)
    tab_idx = min(len(ANCIENT_TABLETS_DATA) - 1, max(0, depth - 1))
    tid, title, text = ANCIENT_TABLETS_DATA[tab_idx]

    # Carve secret tablet niche on left wall
    tx = 35
    ty = int(h * 0.45)
    grid.fill_rect(tx - 12, ty - 12, 24, 28, MAT_AIR)
    grid.fill_rect(tx - 14, ty + 16, 28, 4, MAT_WALL_BONE)
    tablets.append(DnaTablet(tid, float(tx - 8), float(ty - 4), title, text))

    # 2. Spawn matching Gene Orbs for this biome
    matching_orbs = [o for o in ORBS_DATA if o[1] == biome_id]
    for i, (oid, _, gid, oname, odesc) in enumerate(matching_orbs):
        # Carve secret sanctum room encased in dense bone
        ox = w - 45 if i == 0 else 45
        oy = int(h * 0.35) if i == 0 else int(h * 0.75)

        # Secret chamber
        grid.fill_rect(ox - 22, oy - 22, 44, 44, MAT_AIR)
        # Indestructible shrine pedestal
        grid.fill_rect(ox - 10, oy + 12, 20, 6, MAT_WALL_BONE)

        orbs.append(GeneOrb(oid, float(ox), float(oy), gid, oname, odesc))

    return orbs, tablets
