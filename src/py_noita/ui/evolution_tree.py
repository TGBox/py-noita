"""Interactive Bio-Laboratory and Evolution Mutation Tree for meta-progression.

Allows the player to spend earned Mutagen-Essence to unlock:
- Starter Symbiote Strains (Acid Synthesizer, Synaptic Leech, Primordial Parasite)
- Organ & Cellular Modifiers (+HP, +flight duration, +projectile speed, +mutagen yield)
- Primordial Nucleus & DNA-Orb synergies
"""

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Tuple
import pygame

from py_noita.ui.codex import ALL_STRAINS, BioCodex


@dataclass
class EvolutionNode:
    """A node in the branching biological evolution graph."""

    node_id: str
    name: str
    node_type: str  # "STRAIN", "MODIFIER", "ORB"
    category: str
    cost: int
    description: str
    lore_text: str
    pos: Tuple[int, int]  # (x, y) coordinates on standard 640x360 canvas
    parents: List[str] = field(default_factory=list)
    strain_id: Optional[str] = None
    color: Tuple[int, int, int] = (180, 180, 190)
    symbol: str = "DNA"


ALL_TREE_NODES: List[EvolutionNode] = [
    # Root
    EvolutionNode(
        node_id="NODE_ROOT_PARASITE",
        name="Ur-Parasit (Standard)",
        node_type="STRAIN",
        category="[STARTER-STAMM]",
        cost=0,
        description="Agiler Basis-Symbiote mit Knochenspeer und regenerierendem Blutbeutel.",
        lore_text="Der Ursprung aller Infektionen im feindlichen Wirtskörper.",
        pos=(320, 110),
        parents=[],
        strain_id="STRAIN_DEFAULT",
        color=(210, 80, 90),
        symbol="✦",
    ),
    # Acid Branch (Left)
    EvolutionNode(
        node_id="NODE_ACID_SYNTH",
        name="Säure-Synthetisierer",
        node_type="STRAIN",
        category="[STARTER-STAMM]",
        cost=80,
        description="Schaltet den Säure-Stamm frei (Säuregalle-Drüse & Säure-Immunität).",
        lore_text="Mutierte Magendrüsen scheiden ätzende Verdauungssekrete aus.",
        pos=(180, 175),
        parents=["NODE_ROOT_PARASITE"],
        strain_id="STRAIN_ACID_SYNTH",
        color=(90, 240, 50),
        symbol="☣",
    ),
    EvolutionNode(
        node_id="NODE_CORROSIVE_METABOLISM",
        name="Ätzender Metabolismus",
        node_type="MODIFIER",
        category="[ORGAN-MODIFIKATION]",
        cost=120,
        description="+20% Säure-Widerstand und korrosiver Kontaktschaden gegen Feinde.",
        lore_text="Die Zellmembranen neutralisieren selbst konzentrierte Galle.",
        pos=(110, 245),
        parents=["NODE_ACID_SYNTH"],
        color=(140, 255, 80),
        symbol="♨",
    ),
    EvolutionNode(
        node_id="NODE_CHITIN_CARAPACE",
        name="Chitin-Panzerung",
        node_type="MODIFIER",
        category="[ORGAN-MODIFIKATION]",
        cost=200,
        description="+25 Maximale Trefferpunkte (HP) für alle Symbioten-Stämme.",
        lore_text="Verhärtete Chitinplatten schirmen empfindliche Organe ab.",
        pos=(110, 315),
        parents=["NODE_CORROSIVE_METABOLISM"],
        color=(160, 140, 190),
        symbol="⬢",
    ),
    # Synaptic Branch (Right)
    EvolutionNode(
        node_id="NODE_SYNAPTIC_LEECH",
        name="Synaptischer Egel",
        node_type="STRAIN",
        category="[STARTER-STAMM]",
        cost=150,
        description="Schaltet den Synapsen-Stamm frei (Nervenimpuls & Turbo-Geißel).",
        lore_text="Verbindet sich mit den Myelinscheiden des zentralen Nervensystems.",
        pos=(460, 175),
        parents=["NODE_ROOT_PARASITE"],
        strain_id="STRAIN_SYNAPTIC",
        color=(70, 210, 255),
        symbol="⚡",
    ),
    EvolutionNode(
        node_id="NODE_NEURAL_COMPRESSION",
        name="Nerven-Kompression",
        node_type="MODIFIER",
        category="[ORGAN-MODIFIKATION]",
        cost=180,
        description="+35% maximale Flagellen-Schwebedauer und schnellere Erholung.",
        lore_text="Optimierte Bio-Aktionspotenziale verhindern vorzeitige Ermüdung.",
        pos=(530, 245),
        parents=["NODE_SYNAPTIC_LEECH"],
        color=(90, 230, 240),
        symbol="≋",
    ),
    EvolutionNode(
        node_id="NODE_MYELIN_ACCELERATOR",
        name="Myelin-Katalysator",
        node_type="MODIFIER",
        category="[ORGAN-MODIFIKATION]",
        cost=250,
        description="+25% Fluggeschwindigkeit aller verschossenen Projektile.",
        lore_text="Bio-Elektrizität beschleunigt das Ausstoßen der Sporenkapseln.",
        pos=(530, 315),
        parents=["NODE_NEURAL_COMPRESSION"],
        color=(160, 180, 255),
        symbol="»",
    ),
    # Meta / Primordial Branch (Center)
    EvolutionNode(
        node_id="NODE_MUTAGEN_HARVESTER",
        name="Mutagen-Extraktor",
        node_type="MODIFIER",
        category="[META-FORSCHUNG]",
        cost=100,
        description="+20% gewonnene Mutagen-Essenz am Ende jedes beendeten Laufs.",
        lore_text="Enzymatische Filter gewinnen zusätzliche Nährstoffe aus neutralisierten Zellen.",
        pos=(320, 215),
        parents=["NODE_ROOT_PARASITE"],
        color=(240, 70, 220),
        symbol="🧪",
    ),
    EvolutionNode(
        node_id="NODE_PRIMORDIAL_NUCLEUS",
        name="Ur-Zellkern (11 DNA-Orbs)",
        node_type="ORB",
        category="[UR-GEN-FORSCHUNG]",
        cost=300,
        description="Katalysiert die Macht aller verborgenen Ur-Gen-Orbs für kosmisches Erwachen.",
        lore_text="Verschmilzt das Genom des Wirts mit uralter transzendenter DNA.",
        pos=(320, 290),
        parents=["NODE_MUTAGEN_HARVESTER"],
        color=(255, 215, 60),
        symbol="★",
    ),
]


class EvolutionTreeUI:
    """Interactive screen displaying the branching evolution tree graph."""

    def __init__(self, codex: BioCodex, audio_manager: Optional[Any] = None):
        self.codex = codex
        self.audio = audio_manager
        self.selected_node_index: int = 0
        self.nodes = list(ALL_TREE_NODES)
        self.anim_time: float = 0.0

        # Fonts
        self.title_font = pygame.font.SysFont("Arial", 16, bold=True)
        self.header_font = pygame.font.SysFont("Arial", 12, bold=True)
        self.text_font = pygame.font.SysFont("Arial", 10)
        self.bold_font = pygame.font.SysFont("Arial", 10, bold=True)
        self.glyph_font = pygame.font.SysFont("Arial", 13, bold=True)
        self.lore_font = pygame.font.SysFont("Arial", 9, italic=True)

        self.status_message: str = ""
        self.status_timer: float = 0.0

    def get_node_by_id(self, node_id: str) -> Optional[EvolutionNode]:
        for n in self.nodes:
            if n.node_id == node_id:
                return n
        return None

    def is_node_unlocked(self, node: EvolutionNode) -> bool:
        if node.strain_id and node.strain_id in self.codex.unlocked_strains:
            return True
        return node.node_id in self.codex.unlocked_tree_nodes

    def are_parents_unlocked(self, node: EvolutionNode) -> bool:
        if not node.parents:
            return True
        for pid in node.parents:
            parent_node = self.get_node_by_id(pid)
            if not parent_node or not self.is_node_unlocked(parent_node):
                return False
        return True

    def can_unlock_node(self, node: EvolutionNode) -> bool:
        if self.is_node_unlocked(node):
            return False
        if not self.are_parents_unlocked(node):
            return False
        return self.codex.mutagen_essence >= node.cost

    def update(self, dt: float) -> None:
        self.anim_time += dt
        if self.status_timer > 0.0:
            self.status_timer -= dt
            if self.status_timer <= 0.0:
                self.status_message = ""

    def handle_event(self, event: pygame.event.Event, view_w: int, view_h: int) -> bool:
        """Process keyboard navigation and mouse clicks. Returns True to exit back to menu."""
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                return True  # Close lab screen

            # Navigation
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self._navigate_direction(-1, 0)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self._navigate_direction(1, 0)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self._navigate_direction(0, -1)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._navigate_direction(0, 1)

            # Purchase / Select
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._attempt_unlock_selected()

        elif event.type == pygame.MOUSEMOTION:
            # Check hover over nodes
            scale_x = view_w / 640.0
            scale_y = view_h / 360.0
            mx, my = event.pos
            for i, n in enumerate(self.nodes):
                nx = n.pos[0] * scale_x
                ny = n.pos[1] * scale_y
                if math.hypot(mx - nx, my - ny) < 22 * scale_x:
                    self.selected_node_index = i
                    break

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                scale_x = view_w / 640.0
                scale_y = view_h / 360.0
                mx, my = event.pos
                for i, n in enumerate(self.nodes):
                    nx = n.pos[0] * scale_x
                    ny = n.pos[1] * scale_y
                    if math.hypot(mx - nx, my - ny) < 22 * scale_x:
                        self.selected_node_index = i
                        self._attempt_unlock_selected()
                        break

        return False

    def _navigate_direction(self, dx: int, dy: int) -> None:
        """Find the geometrically nearest node in the chosen direction."""
        curr = self.nodes[self.selected_node_index]
        best_idx = self.selected_node_index
        best_dist = float("inf")

        for i, n in enumerate(self.nodes):
            if i == self.selected_node_index:
                continue
            delta_x = n.pos[0] - curr.pos[0]
            delta_y = n.pos[1] - curr.pos[1]

            # Dot product with direction vector
            dot = delta_x * dx + delta_y * dy
            if dot > 10.0:  # In roughly the right direction
                dist = math.hypot(delta_x, delta_y)
                if dist < best_dist:
                    best_dist = dist
                    best_idx = i

        self.selected_node_index = best_idx

    def _attempt_unlock_selected(self) -> None:
        """Try to purchase the currently selected node."""
        node = self.nodes[self.selected_node_index]
        if self.is_node_unlocked(node):
            if node.strain_id:
                self.codex.selected_strain_id = node.strain_id
                self.codex.save()
                self.status_message = f"Stamm '{node.name}' als aktiver Wirt ausgewählt!"
                self.status_timer = 2.5
                if self.audio:
                    self.audio.play("pickup", volume=0.8)
            else:
                self.status_message = f"Knoten '{node.name}' ist bereits aktiv mutiert."
                self.status_timer = 2.0
            return

        if not self.are_parents_unlocked(node):
            self.status_message = "Vorausgehende Mutation(en) müssen zuerst freigeschaltet werden!"
            self.status_timer = 3.0
            return

        if self.codex.mutagen_essence < node.cost:
            missing = node.cost - self.codex.mutagen_essence
            self.status_message = f"Zu wenig Mutagen! Es fehlen noch {missing} Mutagen-Essenz."
            self.status_timer = 3.0
            return

        # Perform unlock
        success = self.codex.unlock_tree_node(node.node_id, node.cost, node.strain_id)
        if success:
            self.status_message = f"MUTATION ERFOLGREICH: '{node.name}' assimiliert!"
            self.status_timer = 3.5
            if self.audio:
                self.audio.play("pickup", volume=1.0)
            if node.strain_id:
                self.codex.selected_strain_id = node.strain_id
                self.codex.save()

    def draw(self, surface: pygame.Surface) -> None:
        """Render the complete laboratory tree canvas with nodes, connections, and tooltips."""
        view_w, view_h = surface.get_size()
        scale_x = view_w / 640.0
        scale_y = view_h / 360.0

        # 1. Dark organic bio-lab background
        surface.fill((12, 9, 16))

        # Ambient organic grid / membrane lines
        for gx in range(0, view_w, 40):
            pygame.draw.line(surface, (18, 14, 24), (gx, 0), (gx, view_h), 1)
        for gy in range(0, view_h, 40):
            pygame.draw.line(surface, (18, 14, 24), (0, gy), (view_w, gy), 1)

        # 2. Header Bar
        header_h = int(48 * scale_y)
        pygame.draw.rect(surface, (20, 14, 26), (0, 0, view_w, header_h))
        pygame.draw.line(surface, (60, 40, 75), (0, header_h), (view_w, header_h), 1)

        title_surf = self.title_font.render("BIO-LABOR // MUTATIONS- & FORSCHUNGSBAUM", True, (240, 80, 180))
        surface.blit(title_surf, (16, 8))

        formula_surf = self.text_font.render(
            "Mutagen-Formel: [Tiefe × 25] + [Kills × 2] + [Biomasse // 10] + [Boss-Boni]",
            True,
            (180, 175, 190),
        )
        surface.blit(formula_surf, (16, 28))

        # Mutagen Account Box (top right)
        mut_box_text = f"Mutagen-Konto: {self.codex.mutagen_essence} M"
        mut_surf = self.header_font.render(mut_box_text, True, (255, 230, 80))
        bw = mut_surf.get_width() + 20
        bx = view_w - bw - 16
        by = 10
        pygame.draw.rect(surface, (35, 22, 45), (bx, by, bw, 28), border_radius=4)
        pygame.draw.rect(surface, (210, 60, 230), (bx, by, bw, 28), 1, border_radius=4)
        surface.blit(mut_surf, (bx + 10, by + 6))

        # 3. Draw Tree Graph Connections
        for node in self.nodes:
            nx = int(node.pos[0] * scale_x)
            ny = int(node.pos[1] * scale_y)
            for pid in node.parents:
                parent = self.get_node_by_id(pid)
                if not parent:
                    continue
                px = int(parent.pos[0] * scale_x)
                py = int(parent.pos[1] * scale_y)

                is_active = self.is_node_unlocked(parent) and self.is_node_unlocked(node)
                is_available = self.is_node_unlocked(parent) and self.can_unlock_node(node)

                if is_active:
                    line_col = (80, 230, 180)
                    line_w = 2
                elif is_available:
                    # Pulsing connector line
                    pulse = int(180 + math.sin(self.anim_time * 6.0) * 50)
                    line_col = (pulse, 80, pulse)
                    line_w = 2
                else:
                    line_col = (50, 40, 60)
                    line_w = 1

                pygame.draw.line(surface, line_col, (px, py), (nx, ny), line_w)

        # 4. Draw Graph Nodes
        node_radius = int(16 * min(scale_x, scale_y))
        for i, node in enumerate(self.nodes):
            nx = int(node.pos[0] * scale_x)
            ny = int(node.pos[1] * scale_y)
            is_unlocked = self.is_node_unlocked(node)
            can_unlock = self.can_unlock_node(node)
            is_selected = i == self.selected_node_index

            # Node Base Fill
            if is_unlocked:
                bg_col = (25, 45, 40)
                border_col = node.color
            elif can_unlock:
                # Pulsing available state
                p = int(180 + math.sin(self.anim_time * 5.0) * 55)
                bg_col = (50, 20, 55)
                border_col = (p, 80, 240)
            else:
                bg_col = (18, 16, 22)
                border_col = (70, 60, 80)

            pygame.draw.circle(surface, bg_col, (nx, ny), node_radius)
            pygame.draw.circle(surface, border_col, (nx, ny), node_radius, 2)

            # Center symbol
            sym_col = (255, 255, 255) if (is_unlocked or can_unlock) else (110, 100, 120)
            sym_surf = self.glyph_font.render(node.symbol, True, sym_col)
            surface.blit(sym_surf, (nx - sym_surf.get_width() // 2, ny - sym_surf.get_height() // 2))

            # Selected Ring & pulse cursor
            if is_selected:
                pulse_r = node_radius + int(4 + math.sin(self.anim_time * 7.0) * 2)
                pygame.draw.circle(surface, (255, 230, 100), (nx, ny), pulse_r, 2)

            # Node Name label underneath
            name_col = (240, 230, 210) if is_unlocked else ((255, 160, 240) if can_unlock else (140, 130, 150))
            name_surf = self.text_font.render(node.name, True, name_col)
            surface.blit(name_surf, (nx - name_surf.get_width() // 2, ny + node_radius + 4))

            # Cost pill
            if not is_unlocked:
                cost_col = (100, 255, 120) if self.codex.mutagen_essence >= node.cost else (240, 80, 80)
                cost_text = f"{node.cost}M"
                cost_surf = self.text_font.render(cost_text, True, cost_col)
                surface.blit(cost_surf, (nx - cost_surf.get_width() // 2, ny + node_radius + 16))

        # 5. Floating / Docked Tooltip Card for Selected Node
        curr_node = self.nodes[self.selected_node_index]
        self._draw_node_card(surface, curr_node, view_w, view_h, scale_x, scale_y)

        # 6. Status Toast / Feedback message
        if self.status_message:
            s_surf = self.header_font.render(self.status_message, True, (255, 240, 140))
            sw = s_surf.get_width() + 24
            sx = view_w // 2 - sw // 2
            sy = view_h - 65
            pygame.draw.rect(surface, (25, 18, 30), (sx, sy, sw, 24), border_radius=4)
            pygame.draw.rect(surface, (240, 120, 220), (sx, sy, sw, 24), 1, border_radius=4)
            surface.blit(s_surf, (sx + 12, sy + 4))

        # 7. Bottom Navigation Controls Hint
        bottom_h = 24
        by = view_h - bottom_h
        pygame.draw.rect(surface, (16, 12, 20), (0, by, view_w, bottom_h))
        pygame.draw.line(surface, (45, 35, 55), (0, by), (view_w, by), 1)

        help_text = "[PFEILTASTEN / MAUS] Knoten wählen  |  [ENTER / KLICK] Freischalten  |  [ESC] Hauptmenü"
        help_surf = self.text_font.render(help_text, True, (170, 160, 180))
        surface.blit(help_surf, (view_w // 2 - help_surf.get_width() // 2, by + 5))

    def _draw_node_card(
        self,
        surface: pygame.Surface,
        node: EvolutionNode,
        view_w: int,
        view_h: int,
        scale_x: float,
        scale_y: float,
    ) -> None:
        """Render rich info card with stats, lore, and interaction prompt."""
        is_unlocked = self.is_node_unlocked(node)
        can_unlock = self.can_unlock_node(node)

        card_w = min(260, int(view_w * 0.38))
        card_h = 135
        # Dock to bottom left or right depending on node position
        card_x = 16 if node.pos[0] > 320 else (view_w - card_w - 16)
        card_y = view_h - card_h - 32

        card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        card_surf.fill((16, 14, 22, 240))
        border_col = (80, 220, 160) if is_unlocked else ((220, 70, 230) if can_unlock else (80, 70, 90))
        pygame.draw.rect(card_surf, border_col, (0, 0, card_w, card_h), 1, border_radius=4)

        # Header
        cat_surf = self.text_font.render(node.category, True, (160, 150, 170))
        card_surf.blit(cat_surf, (8, 6))

        title_surf = self.header_font.render(node.name, True, node.color)
        card_surf.blit(title_surf, (8, 20))

        # Status Badge
        if is_unlocked:
            status_text = "[ASSIMILIERT / AKTIV]"
            st_col = (80, 255, 160)
        elif can_unlock:
            status_text = "[BEREIT ZUR MUTATION]"
            st_col = (255, 120, 240)
        elif not self.are_parents_unlocked(node):
            status_text = "[GESPERRT: Vorstufe fehlt]"
            st_col = (240, 70, 80)
        else:
            status_text = f"[GESPERRT: Fehlen {node.cost - self.codex.mutagen_essence} M]"
            st_col = (240, 100, 100)

        st_surf = self.bold_font.render(status_text, True, st_col)
        card_surf.blit(st_surf, (8, 36))

        # Separator line
        pygame.draw.line(card_surf, (50, 40, 60), (8, 51), (card_w - 8, 51), 1)

        # Description (Word wrapped)
        words = node.description.split()
        lines = []
        curr = ""
        for w in words:
            test = f"{curr} {w}".strip()
            if self.text_font.size(test)[0] <= card_w - 16:
                curr = test
            else:
                if curr:
                    lines.append(curr)
                curr = w
        if curr:
            lines.append(curr)

        for li, line in enumerate(lines[:2]):
            d_surf = self.text_font.render(line, True, (220, 215, 230))
            card_surf.blit(d_surf, (8, 56 + li * 13))

        # Lore
        lore_surf = self.lore_font.render(f'"{node.lore_text}"', True, (170, 160, 180))
        card_surf.blit(lore_surf, (8, 86))

        # Action Prompt
        if is_unlocked:
            prompt_text = "[LEERTASTE / KLICK] Als aktiven Wirt wählen" if node.strain_id else "[Permanent aktiv]"
            pr_col = (140, 240, 180)
        elif can_unlock:
            prompt_text = f"[ENTER / KLICK] FREISCHALTEN (-{node.cost} Mutagen)"
            pr_col = (255, 230, 90)
        else:
            prompt_text = f"Kosten: {node.cost} Mutagen"
            pr_col = (180, 170, 185)

        pr_surf = self.bold_font.render(prompt_text, True, pr_col)
        card_surf.blit(pr_surf, (8, 112))

        surface.blit(card_surf, (card_x, card_y))
