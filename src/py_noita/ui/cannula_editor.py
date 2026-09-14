"""Organ-Tuning GUI: Interactive deckbuilder to swap, reorder, and tune gene cards."""

from typing import List, Optional, Tuple
import pygame

from py_noita.weapons.cannula import OrganCannula
from py_noita.weapons.gene import Gene


class CannulaEditor:
    """Deck-building interface to configure Gene cards in Organ-Cannulas."""

    def __init__(self):
        self.font = pygame.font.SysFont("Arial", 11)
        self.bold_font = pygame.font.SysFont("Arial", 12, bold=True)
        self.title_font = pygame.font.SysFont("Arial", 15, bold=True)

        self.selected_slot: Optional[Tuple[int, int]] = None  # (cannula_idx, slot_idx)
        self.hovered_gene: Optional[Gene] = None
        self.spare_stash: List[Gene] = []  # Unequipped gene cards collected

    def handle_click(self, mouse_x: int, mouse_y: int, player) -> None:
        """Handle clicking on a gene slot to select, move, or swap."""
        # Check cannula slots
        start_y = 50
        for c_idx, cannula in enumerate(player.cannulas):
            slot_y = start_y + c_idx * 46 + 18
            for s_idx in range(cannula.capacity):
                slot_x = 25 + s_idx * 22
                slot_rect = pygame.Rect(slot_x, slot_y, 20, 20)
                if slot_rect.collidepoint(mouse_x, mouse_y):
                    if self.selected_slot is None:
                        # Select this slot if it has a gene
                        if cannula.slots[s_idx] is not None:
                            self.selected_slot = (c_idx, s_idx)
                    else:
                        # Swap or move gene
                        src_c, src_s = self.selected_slot
                        src_cannula = player.cannulas[src_c]
                        # Swap contents
                        src_cannula.slots[src_s], cannula.slots[s_idx] = cannula.slots[s_idx], src_cannula.slots[src_s]
                        self.selected_slot = None
                    return

        # Clicked empty space: deselect
        self.selected_slot = None

    def draw(self, surface: pygame.Surface, player, mouse_pos: Tuple[int, int]) -> None:
        """Render the Organ-Tuning deckbuilder overlay."""
        view_w = surface.get_width()
        view_h = surface.get_height()

        # Semi-transparent background
        overlay = pygame.Surface((view_w, view_h), pygame.SRCALPHA)
        overlay.fill((16, 12, 22, 225))
        surface.blit(overlay, (0, 0))

        # Title
        title = self.title_font.render("ORGAN-TUNING // GEN-SEQUENZIERUNG", True, (240, 220, 150))
        surface.blit(title, (20, 16))

        hint = self.font.render("[TAB/E] Schließen  |  Klicke Gene zum Verschieben & Austauschen", True, (160, 150, 140))
        surface.blit(hint, (20, 34))

        self.hovered_gene = None
        start_y = 55

        # Render Cannulas
        for c_idx, cannula in enumerate(player.cannulas):
            cy = start_y + c_idx * 48
            is_active = (c_idx == player.active_cannula_index)
            header_col = (255, 230, 120) if is_active else (200, 190, 180)

            # Header info
            shuffle_str = "Chaos/Shuffle" if cannula.shuffle else "Sequentiell"
            info = f"#{c_idx + 1} {cannula.name} | Delay: {cannula.cast_delay}s | Rech: {cannula.recharge_time}s | Bio: {int(cannula.current_biomass)}/{int(cannula.biomass_max)} | {shuffle_str}"
            header_surf = self.bold_font.render(info, True, header_col)
            surface.blit(header_surf, (22, cy))

            # Slots
            slot_y = cy + 18
            for s_idx in range(cannula.capacity):
                slot_x = 25 + s_idx * 22
                slot_rect = pygame.Rect(slot_x, slot_y, 20, 20)

                is_selected = (self.selected_slot == (c_idx, s_idx))
                border_col = (255, 255, 100) if is_selected else (85, 75, 90)
                bg_col = (35, 28, 40)

                pygame.draw.rect(surface, bg_col, slot_rect, border_radius=2)
                pygame.draw.rect(surface, border_col, slot_rect, 2 if is_selected else 1)

                gene = cannula.slots[s_idx]
                if gene is not None:
                    # Gene card icon
                    pygame.draw.rect(surface, gene.color, (slot_x + 3, slot_y + 3, 14, 14), border_radius=2)

                # Tooltip check
                if slot_rect.collidepoint(mouse_pos) and gene is not None:
                    self.hovered_gene = gene

        # Render Tooltip at bottom
        if self.hovered_gene:
            self._draw_tooltip(surface, self.hovered_gene, view_w, view_h)

    def _draw_tooltip(self, surface: pygame.Surface, gene: Gene, view_w: int, view_h: int) -> None:
        """Render tooltip panel for hovered gene."""
        panel_rect = pygame.Rect(20, view_h - 60, view_w - 40, 52)
        pygame.draw.rect(surface, (28, 22, 35), panel_rect, border_radius=4)
        pygame.draw.rect(surface, gene.color, panel_rect, 1, border_radius=4)

        name_surf = self.bold_font.render(f"{gene.name} [{gene.gene_type.value}]", True, gene.color)
        surface.blit(name_surf, (panel_rect.x + 8, panel_rect.y + 6))

        stats = f"Kosten: {gene.biomass_cost} B  |  Schaden: {gene.damage}  |  Speed: {gene.speed}"
        stats_surf = self.font.render(stats, True, (210, 200, 180))
        surface.blit(stats_surf, (panel_rect.x + 8, panel_rect.y + 20))

        desc_surf = self.font.render(gene.description, True, (170, 165, 160))
        surface.blit(desc_surf, (panel_rect.x + 8, panel_rect.y + 34))
