"""In-game HUD: Vital bars (HP, levitation, biomass), active cannula, and liquid sacs."""

from typing import Tuple
import pygame

from py_noita.simulation.materials import LUT_COLORS, MAT_AIR


class HUD:
    """Renders the player's status bars, weapon slots, and liquid glands."""

    def __init__(self):
        self.font = pygame.font.SysFont("Arial", 12, bold=True)
        self.large_font = pygame.font.SysFont("Arial", 14, bold=True)

    def draw(
        self,
        surface: pygame.Surface,
        player,
        biome_name: str,
        depth_level: int,
    ) -> None:
        """Render HUD elements directly onto the viewport surface."""
        # 1. Vital Bars (Top Left)
        # HP Bar
        hp_frac = max(0.0, min(1.0, player.hp / max(1.0, player.max_hp)))
        self._draw_bar(
            surface,
            x=10, y=10, w=100, h=8,
            fraction=hp_frac,
            fill_col=(200, 25, 40),
            bg_col=(60, 15, 20),
            border_col=(180, 160, 140),
            label=f"{int(player.hp)}/{int(player.max_hp)}",
        )

        # Levitation Stamina Bar
        lev_frac = max(0.0, min(1.0, player.levitation / max(1.0, player.max_levitation)))
        self._draw_bar(
            surface,
            x=10, y=22, w=75, h=6,
            fraction=lev_frac,
            fill_col=(50, 200, 240),
            bg_col=(15, 50, 65),
            border_col=(140, 170, 180),
            label=None,
        )

        # Active Cannula Biomass (Mana) Bar
        if player.cannulas and 0 <= player.active_cannula_index < len(player.cannulas):
            cur_cannula = player.cannulas[player.active_cannula_index]
            bio_frac = max(0.0, min(1.0, cur_cannula.current_biomass / max(1.0, cur_cannula.biomass_max)))
            bio_col = (190, 40, 220) if not cur_cannula.is_recharging else (240, 140, 40)
            self._draw_bar(
                surface,
                x=10, y=32, w=65, h=5,
                fraction=bio_frac,
                fill_col=bio_col,
                bg_col=(50, 15, 60),
                border_col=(160, 140, 170),
                label=None,
            )

        # 2. Currency & Biome info (Top Right)
        view_w = surface.get_width()
        biomass_text = self.large_font.render(f"◆ {player.biomass_currency} Biomasse", True, (255, 220, 110))
        surface.blit(biomass_text, (view_w - biomass_text.get_width() - 10, 10))

        depth_text = self.font.render(f"{biome_name} [Tiefe {depth_level}]", True, (210, 200, 190))
        surface.blit(depth_text, (view_w - depth_text.get_width() - 10, 28))

        # 3. Organ-Cannula Slots (Keys 1-4, Bottom Left)
        self._draw_cannula_slots(surface, player, x=10, y=surface.get_height() - 28)

        # 4. Organ-Gland Sacs (Keys 5-8, Bottom Right)
        self._draw_gland_slots(surface, player, x=view_w - 95, y=surface.get_height() - 28)

    def _draw_bar(
        self,
        surface: pygame.Surface,
        x: int, y: int, w: int, h: int,
        fraction: float,
        fill_col: Tuple[int, int, int],
        bg_col: Tuple[int, int, int],
        border_col: Tuple[int, int, int],
        label: str = None,
    ) -> None:
        # Background
        pygame.draw.rect(surface, bg_col, (x, y, w, h))
        # Fill
        fill_w = int(w * fraction)
        if fill_w > 0:
            pygame.draw.rect(surface, fill_col, (x, y, fill_w, h))
        # Border
        pygame.draw.rect(surface, border_col, (x, y, w, h), 1)

        if label:
            text = self.font.render(label, True, (255, 255, 255))
            surface.blit(text, (x + w + 4, y - 2))

    def _draw_cannula_slots(self, surface: pygame.Surface, player, x: int, y: int) -> None:
        """Draw 4 weapon cannula slots."""
        for i in range(4):
            slot_x = x + i * 20
            is_active = (i == player.active_cannula_index)
            border_col = (255, 230, 100) if is_active else (80, 75, 70)
            bg_col = (40, 30, 35) if is_active else (25, 20, 25)

            pygame.draw.rect(surface, bg_col, (slot_x, y, 18, 18), border_radius=2)
            pygame.draw.rect(surface, border_col, (slot_x, y, 18, 18), 1 if not is_active else 2)

            if i < len(player.cannulas):
                c = player.cannulas[i]
                # Mini icon representing first gene color
                first_gene = next((g for g in c.slots if g is not None), None)
                if first_gene:
                    pygame.draw.circle(surface, first_gene.color, (slot_x + 9, y + 9), 4)

            # Slot number label
            num_surf = self.font.render(str(i + 1), True, (150, 140, 130))
            surface.blit(num_surf, (slot_x + 1, y - 11))

    def _draw_gland_slots(self, surface: pygame.Surface, player, x: int, y: int) -> None:
        """Draw 4 liquid sac glands."""
        for i in range(4):
            slot_x = x + i * 20
            is_active = (i == player.active_gland_index)
            border_col = (100, 230, 255) if is_active else (70, 75, 80)
            bg_col = (20, 25, 30)

            pygame.draw.rect(surface, bg_col, (slot_x, y, 18, 18), border_radius=2)
            pygame.draw.rect(surface, border_col, (slot_x, y, 18, 18), 1 if not is_active else 2)

            gland = player.glands[i]
            if gland.current_amount > 0 and gland.material_id != MAT_AIR:
                fill_frac = gland.current_amount / gland.capacity
                fill_h = max(2, int(14 * fill_frac))
                mat_col = tuple(LUT_COLORS[gland.material_id])
                pygame.draw.rect(surface, mat_col, (slot_x + 2, y + 16 - fill_h, 14, fill_h), border_radius=1)

            # Slot number label (5-8)
            num_surf = self.font.render(str(i + 5), True, (130, 140, 150))
            surface.blit(num_surf, (slot_x + 1, y - 11))
