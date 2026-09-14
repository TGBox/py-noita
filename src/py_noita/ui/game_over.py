"""Game Over and Victory Screen with run summary, meta rewards, and 3 alternative endings."""

from typing import Optional
import pygame

from py_noita.world.endings import (
    ENDING_COSMIC_METAMORPHOSIS,
    ENDING_HOST_DEATH,
    ENDING_NONE,
    ENDING_SYMBIOSIS,
    ENDINGS,
)


class GameOverScreen:
    """Renders run summary, statistics, and 3 alternative ending narratives."""

    def __init__(self):
        self.title_font = pygame.font.SysFont("Arial", 18, bold=True)
        self.sub_font = pygame.font.SysFont("Arial", 12, bold=True)
        self.text_font = pygame.font.SysFont("Arial", 11)
        self.lore_font = pygame.font.SysFont("Arial", 10, italic=True)

    def draw(
        self,
        surface: pygame.Surface,
        victory: bool,
        depth: int,
        kills: int,
        biomass: int,
        earned_mutagen: int,
        total_mutagen: int,
        ending_id: int = ENDING_HOST_DEATH,
        orbs_collected: int = 0,
    ) -> None:
        """Render visceral death or alternative ending victory card."""
        view_w = surface.get_width()
        view_h = surface.get_height()

        overlay = pygame.Surface((view_w, view_h), pygame.SRCALPHA)
        if not victory:
            overlay.fill((45, 10, 20, 225))
            surface.blit(overlay, (0, 0))

            title_surf = self.title_font.render("DER SYMBIOT WURDE ZERSETZT", True, (255, 60, 60))
            sub_surf = self.sub_font.render("Zellulärer Tod im Wirtsgewebe", True, (200, 150, 150))
            surface.blit(title_surf, (view_w // 2 - title_surf.get_width() // 2, 35))
            surface.blit(sub_surf, (view_w // 2 - sub_surf.get_width() // 2, 60))
        else:
            ending = ENDINGS.get(ending_id, ENDINGS[ENDING_HOST_DEATH])
            # Ambient colored overlay
            r, g, b = ending.color
            overlay.fill((max(10, r // 8), max(10, g // 8), max(10, b // 8), 235))
            surface.blit(overlay, (0, 0))

            title_surf = self.title_font.render(ending.title, True, ending.color)
            sub_surf = self.sub_font.render(ending.sub_title, True, (240, 230, 210))
            surface.blit(title_surf, (view_w // 2 - title_surf.get_width() // 2, 25))
            surface.blit(sub_surf, (view_w // 2 - sub_surf.get_width() // 2, 48))

            # Narrative Lore Box
            lore_w = min(360, view_w - 40)
            lore_box = pygame.Rect(view_w // 2 - lore_w // 2, 70, lore_w, 48)
            pygame.draw.rect(surface, (20, 15, 25), lore_box, border_radius=4)
            pygame.draw.rect(surface, ending.color, lore_box, 1, border_radius=4)

            # Split text to fit
            words = ending.lore_text.split(" ")
            lines = []
            curr = ""
            for w in words:
                test = curr + (" " if curr else "") + w
                if len(test) < 58:
                    curr = test
                else:
                    lines.append(curr)
                    curr = w
            if curr:
                lines.append(curr)

            for li, line in enumerate(lines[:3]):
                l_surf = self.lore_font.render(line, True, (225, 220, 210))
                surface.blit(l_surf, (lore_box.x + 8, lore_box.y + 6 + li * 13))

        # Stats Card
        card_w, card_h = 260, 95
        card_x = view_w // 2 - card_w // 2
        card_y = 125 if victory else 85
        pygame.draw.rect(surface, (25, 18, 30), (card_x, card_y, card_w, card_h), border_radius=4)
        border_col = (140, 80, 100) if not victory else ENDINGS.get(ending_id, ENDINGS[ENDING_HOST_DEATH]).color
        pygame.draw.rect(surface, border_col, (card_x, card_y, card_w, card_h), 1, border_radius=4)

        stats = [
            f"Erreichte Tiefe: Organ-Schicht {depth}  •  DNA-Orbs: {orbs_collected}/11",
            f"Neutralisierte Immunzellen: {kills}",
            f"Absorbierte Biomasse: {biomass} B",
            f"Gewonnene Mutagen-Essenz: +{earned_mutagen} (Gesamt: {total_mutagen})",
        ]

        for i, stat in enumerate(stats):
            s_surf = self.text_font.render(stat, True, (230, 220, 210))
            surface.blit(s_surf, (card_x + 12, card_y + 8 + i * 21))

        # Prompt
        prompt = self.sub_font.render("[LEERTASTE] Erneut infizieren (Neuer Run)   |   [ESC] Menü", True, (255, 230, 120))
        surface.blit(prompt, (view_w // 2 - prompt.get_width() // 2, card_y + card_h + 12))

