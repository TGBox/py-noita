"""Game Over and Victory Screen with run summary and meta rewards."""

import pygame


class GameOverScreen:
    """Renders run summary, statistics, and restart prompts."""

    def __init__(self):
        self.title_font = pygame.font.SysFont("Arial", 20, bold=True)
        self.sub_font = pygame.font.SysFont("Arial", 13, bold=True)
        self.text_font = pygame.font.SysFont("Arial", 11)

    def draw(
        self,
        surface: pygame.Surface,
        victory: bool,
        depth: int,
        kills: int,
        biomass: int,
        earned_mutagen: int,
        total_mutagen: int,
    ) -> None:
        """Render visceral death or victory card."""
        view_w = surface.get_width()
        view_h = surface.get_height()

        # Darkened red/violet overlay
        overlay = pygame.Surface((view_w, view_h), pygame.SRCALPHA)
        bg_col = (45, 10, 20, 220) if not victory else (15, 35, 45, 220)
        overlay.fill(bg_col)
        surface.blit(overlay, (0, 0))

        # Title
        title_text = "DER SYMBIOT WURDE ZERSETZT" if not victory else "WIRTS-ORGANISMUS VOLLSTÄNDIG INFIZIERT!"
        title_col = (255, 60, 60) if not victory else (60, 255, 140)
        title_surf = self.title_font.render(title_text, True, title_col)
        surface.blit(title_surf, (view_w // 2 - title_surf.get_width() // 2, 45))

        # Stats Card
        card_w, card_h = 240, 110
        card_x = view_w // 2 - card_w // 2
        card_y = 85
        pygame.draw.rect(surface, (25, 18, 30), (card_x, card_y, card_w, card_h), border_radius=4)
        pygame.draw.rect(surface, (140, 80, 100), (card_x, card_y, card_w, card_h), 1, border_radius=4)

        stats = [
            f"Erreichte Tiefe: Organ-Schicht {depth}",
            f"Neutralisierte Immunzellen: {kills}",
            f"Absorbierte Biomasse: {biomass} B",
            f"Gewonnene Mutagen-Essenz: +{earned_mutagen} (Gesamt: {total_mutagen})",
        ]

        for i, stat in enumerate(stats):
            s_surf = self.text_font.render(stat, True, (230, 220, 210))
            surface.blit(s_surf, (card_x + 15, card_y + 12 + i * 22))

        # Prompt
        prompt = self.sub_font.render("[LEERTASTE] Erneut infizieren (Neuer Run)   |   [ESC] Menü", True, (255, 230, 120))
        surface.blit(prompt, (view_w // 2 - prompt.get_width() // 2, card_y + card_h + 18))
