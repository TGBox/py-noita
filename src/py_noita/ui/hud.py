from typing import Any, Optional, Tuple
import pygame

from py_noita.simulation.materials import LUT_COLORS, MAT_AIR
from py_noita.ui.hover_info import HoverTarget


class HUD:
    """Renders the player's status bars, weapon slots, and liquid glands."""

    def __init__(self, scale: float = 1.0):
        self.scale: float = scale
        self.splash_text: Optional[str] = None
        self.splash_timer: float = 0.0
        self.splash_duration: float = 1.8
        self._init_fonts()

    def _init_fonts(self) -> None:
        """Create resolution/scale-adjusted fonts."""
        self.font = pygame.font.SysFont("Arial", max(8, int(12 * self.scale)), bold=True)
        self.large_font = pygame.font.SysFont("Arial", max(9, int(14 * self.scale)), bold=True)
        self.small_font = pygame.font.SysFont("Arial", max(7, int(10 * self.scale)), bold=True)
        self.tiny_font = pygame.font.SysFont("Arial", max(6, int(9 * self.scale)))

    def set_scale(self, scale: float) -> None:
        """Update HUD scaling factor (1.0x for 1080p up to 2.0x for 4K)."""
        self.scale = max(0.75, min(2.5, scale))
        self._init_fonts()

    def show_splash(self, text: str) -> None:
        """Trigger dynamic splash notification text (e.g. on slot switch)."""
        self.splash_text = text
        self.splash_timer = self.splash_duration

    def update(self, dt: float) -> None:
        """Update animated HUD timers."""
        if self.splash_timer > 0.0:
            self.splash_timer = max(0.0, self.splash_timer - dt)

    def draw(
        self,
        surface: pygame.Surface,
        player,
        biome_name: str,
        depth_level: int,
        hover_target: Optional[HoverTarget] = None,
        mouse_pos: Optional[Tuple[int, int]] = None,
        active_boss: Optional[Any] = None,
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

        # 1b. Active Bio-Status Effects Bar (Top Left, under vital bars)
        status_badges = []
        if getattr(player, "on_fire", False):
            status_badges.append(("F", (255, 120, 20), player.fire_timer, 120))
        if getattr(player, "acid_burn_timer", 0) > 0:
            status_badges.append(("A", (90, 255, 50), player.acid_burn_timer, 60))
        if getattr(player, "bile_slippery_timer", 0) > 0:
            status_badges.append(("G", (190, 210, 30), player.bile_slippery_timer, 150))
        if getattr(player, "mutagen_frenzy_timer", 0) > 0:
            status_badges.append(("M", (220, 40, 240), player.mutagen_frenzy_timer, 180))
        if getattr(player, "spore_boost_timer", 0) > 0:
            status_badges.append(("S", (200, 235, 40), player.spore_boost_timer, 140))
        if getattr(player, "pus_sticky_timer", 0) > 0:
            status_badges.append(("E", (220, 210, 110), player.pus_sticky_timer, 150))
        if getattr(player, "gas_exposure_timer", 0) > 0:
            status_badges.append(("X", (120, 230, 100), player.gas_exposure_timer, 180))

        badge_x = 10
        badge_y = 42
        badge_size = 14
        for initial, color, timer, max_time in status_badges:
            pygame.draw.rect(surface, (20, 15, 25), (badge_x, badge_y, badge_size, badge_size), border_radius=2)
            pygame.draw.rect(surface, color, (badge_x, badge_y, badge_size, badge_size), 1, border_radius=2)
            init_surf = self.tiny_font.render(initial, True, color)
            surface.blit(init_surf, (badge_x + (badge_size - init_surf.get_width()) // 2, badge_y))
            dur_frac = max(0.0, min(1.0, timer / max(1.0, float(max_time))))
            bar_w = int(badge_size * dur_frac)
            if bar_w > 0:
                pygame.draw.rect(surface, color, (badge_x, badge_y + badge_size + 1, bar_w, 2))
            badge_x += badge_size + 4

        # 2. Currency & Biome info (Top Right)
        view_w = surface.get_width()
        biomass_text = self.large_font.render(f"◆ {player.biomass_currency} Biomasse", True, (255, 220, 110))
        surface.blit(biomass_text, (view_w - biomass_text.get_width() - 10, 10))

        depth_text = self.font.render(f"{biome_name} [Tiefe {depth_level}]", True, (210, 200, 190))
        surface.blit(depth_text, (view_w - depth_text.get_width() - 10, 28))

        # DNA Orbs count
        orbs_count = getattr(player, "orbs_collected", 0)
        orbs_text = self.font.render(f"DNA-Orbs: {orbs_count} / 11", True, (255, 215, 60))
        surface.blit(orbs_text, (view_w - orbs_text.get_width() - 10, 44))
        pygame.draw.circle(surface, (255, 220, 80), (view_w - orbs_text.get_width() - 18, 50), 3)

        # 2b. Boss Health Bar (if engaged)
        if active_boss and active_boss.alive:
            from py_noita.entities.bosses import draw_boss_health_bar
            draw_boss_health_bar(surface, active_boss, self.font, view_w, surface.get_height())

        # 3. Organ-Cannula Slots (Keys 1-4, Bottom Left)
        self._draw_cannula_slots(surface, player, x=10, y=surface.get_height() - 28)

        # 4. Organ-Gland Sacs (Keys 5-8, Bottom Right)
        self._draw_gland_slots(surface, player, x=view_w - 95, y=surface.get_height() - 28)

        # 4b. Dynamic Slot Change Splash Text (Centered above hotbar)
        if self.splash_text and self.splash_timer > 0.0:
            elapsed = self.splash_duration - self.splash_timer
            if elapsed < 0.2:
                alpha = int(255 * (elapsed / 0.2))
            elif self.splash_timer < 0.4:
                alpha = int(255 * (self.splash_timer / 0.4))
            else:
                alpha = 255

            txt_surf = self.font.render(self.splash_text, True, (255, 235, 160))
            bw = txt_surf.get_width() + 18
            bh = txt_surf.get_height() + 6
            bx = (view_w - bw) // 2
            by = surface.get_height() - 50

            panel = pygame.Surface((bw, bh), pygame.SRCALPHA)
            panel.fill((16, 12, 22, int(alpha * 0.85)))
            pygame.draw.rect(panel, (210, 180, 80, alpha), (0, 0, bw, bh), 1, border_radius=3)
            panel.blit(txt_surf, (9, 3))
            surface.blit(panel, (bx, by))

        # 5. Hover Inspection Tooltip (Noita-style)
        if hover_target is not None and mouse_pos is not None:
            self._draw_hover_tooltip(surface, hover_target, mouse_pos[0], mouse_pos[1])

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

    def _draw_hover_tooltip(
        self,
        surface: pygame.Surface,
        target: HoverTarget,
        mx: int,
        my: int,
    ) -> None:
        """Render floating Noita-style tooltip beside the cursor."""
        view_w = surface.get_width()
        view_h = surface.get_height()

        if target.target_type == "ENEMY":
            # Enemy Tooltip: Name + Mini Health Bar
            name_surf = self.small_font.render(target.name, True, target.color)
            hp_curr = int(target.current_hp) if target.current_hp is not None else 0
            hp_max = int(target.max_hp) if target.max_hp is not None else 1
            hp_surf = self.tiny_font.render(f"{hp_curr}/{hp_max} HP", True, (220, 210, 205))

            bar_w = 40
            bar_h = 4
            content_w = max(name_surf.get_width(), bar_w + hp_surf.get_width() + 6)
            box_w = content_w + 16
            box_h = 28

            tip_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
            tip_surf.fill((16, 12, 20, 230))
            border_col = (
                min(255, target.color[0] // 2 + 50),
                min(255, target.color[1] // 2 + 50),
                min(255, target.color[2] // 2 + 50),
            )
            pygame.draw.rect(tip_surf, border_col, (0, 0, box_w, box_h), 1, border_radius=3)

            # Bullet dot
            pygame.draw.circle(tip_surf, target.color, (7, 8), 3)
            tip_surf.blit(name_surf, (14, 2))

            # Health bar & text on line 2
            hp_frac = max(0.0, min(1.0, (target.current_hp or 0.0) / max(1.0, target.max_hp or 1.0)))
            bar_x = 7
            bar_y = 17
            pygame.draw.rect(tip_surf, (50, 15, 20), (bar_x, bar_y, bar_w, bar_h))
            fill_w = int(bar_w * hp_frac)
            if fill_w > 0:
                pygame.draw.rect(tip_surf, (220, 35, 45), (bar_x, bar_y, fill_w, bar_h))
            pygame.draw.rect(tip_surf, (140, 80, 85), (bar_x, bar_y, bar_w, bar_h), 1)

            tip_surf.blit(hp_surf, (bar_x + bar_w + 5, 14))

        else:
            # Material / Liquid / Object Tooltip
            name_surf = self.small_font.render(target.name, True, (245, 240, 235))
            cat_text = f"[{target.category}]" if target.category else ""
            cat_surf = self.tiny_font.render(cat_text, True, (160, 155, 150)) if cat_text else None

            cat_w = cat_surf.get_width() + 4 if cat_surf else 0
            box_w = 12 + name_surf.get_width() + cat_w + 8
            box_h = 17

            tip_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
            tip_surf.fill((14, 10, 18, 225))
            border_col = (
                min(255, target.color[0] // 2 + 40),
                min(255, target.color[1] // 2 + 40),
                min(255, target.color[2] // 2 + 40),
            )
            pygame.draw.rect(tip_surf, border_col, (0, 0, box_w, box_h), 1, border_radius=3)

            # Color dot representing material / liquid
            pygame.draw.circle(tip_surf, target.color, (7, 8), 3)
            pygame.draw.circle(tip_surf, (255, 255, 255), (7, 8), 3, 1)

            tip_surf.blit(name_surf, (13, 2))
            if cat_surf:
                tip_surf.blit(cat_surf, (13 + name_surf.get_width() + 4, 3))

        # Position clamped to viewport
        tx = mx + 10
        ty = my + 10
        if tx + box_w > view_w - 4:
            tx = mx - box_w - 6
        if ty + box_h > view_h - 4:
            ty = my - box_h - 6

        tx = max(4, min(view_w - box_w - 4, tx))
        ty = max(4, min(view_h - box_h - 4, ty))

        surface.blit(tip_surf, (tx, ty))
