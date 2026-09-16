"""Incubation Node (Holy Mountain equivalent): Safe zone, healing, perks, shop, and tuning."""

import random
from typing import List, Optional, Tuple
import pygame

from py_noita.perks.perk_definitions import MutationPerk, getRandomPerks
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import (
    MAT_AIR,
    MAT_BONE,
    MAT_LYMPH,
    MAT_NERVE,
    MAT_TISSUE,
    MAT_WALL_BONE,
)
from py_noita.weapons.cannula import OrganCannula
from py_noita.weapons.gene import GENE_LIBRARY, Gene


class PerkPedestal:
    """An organic altar holding a selectable genetic mutation perk."""
    def __init__(self, x: float, y: float, perk: MutationPerk):
        self.x = x
        self.y = y
        self.perk = perk
        self.collected: bool = False
        self.width = 16
        self.height = 16

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int, font: pygame.font.Font) -> None:
        if self.collected:
            return

        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)

        # Pedestal base
        pygame.draw.rect(surface, (90, 80, 75), (sx - 7, sy + 7, 14, 5), border_radius=1)
        pygame.draw.rect(surface, (130, 120, 110), (sx - 5, sy + 3, 10, 4))

        # Floating pulsating DNA orb
        import math
        t = pygame.time.get_ticks() * 0.005
        float_y = sy + int(math.sin(t * 2.0 + self.x * 0.1) * 2.5)
        pulse_r = int(5 + math.sin(t * 3.0 + self.x * 0.1) * 1.5)
        pygame.draw.circle(surface, self.perk.color, (sx, float_y), pulse_r)
        pygame.draw.circle(surface, (255, 255, 255), (sx, float_y), 2)


class ShopItem:
    """An item (Gene or Cannula) for sale in the incubation chamber."""
    def __init__(self, x: float, y: float, item, cost: int, is_cannula: bool = False):
        self.x = x
        self.y = y
        self.item = item
        self.cost = cost
        self.is_cannula = is_cannula
        self.purchased: bool = False

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int, font: pygame.font.Font) -> None:
        if self.purchased:
            return

        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)

        # Pod base
        col = (220, 180, 70) if not self.is_cannula else (180, 80, 220)
        pygame.draw.rect(surface, (35, 30, 42), (sx - 8, sy - 8, 16, 16), border_radius=3)
        pygame.draw.rect(surface, col, (sx - 8, sy - 8, 16, 16), 1, border_radius=3)

        # Inner glyph
        if not self.is_cannula:
            gene_col = getattr(self.item, "color", (240, 200, 80))
            pygame.draw.circle(surface, gene_col, (sx, sy), 4)
            pygame.draw.circle(surface, (255, 255, 255), (sx, sy), 1)
        else:
            pygame.draw.line(surface, col, (sx - 4, sy), (sx + 4, sy), 2)
            pygame.draw.circle(surface, (255, 255, 255), (sx + 4, sy), 1)

        # Compact cost badge underneath
        cost_text = font.render(f"{self.cost}B", True, (255, 220, 100))
        surface.blit(cost_text, (sx - cost_text.get_width() // 2, sy + 10))


class IncubationNode:
    """Manages the sanctuary chamber between biomes."""

    def __init__(
        self,
        start_x: int,
        start_y: int,
        width: int = 380,
        height: int = 140,
        has_side_path: bool = False,
        side_biome_id: Optional[str] = None,
        side_biome_name: str = "Gallen-Lagune",
    ):
        self.x = start_x
        self.y = start_y
        self.width = width
        self.height = height
        self.has_side_path = has_side_path
        self.side_biome_id = side_biome_id
        self.side_biome_name = side_biome_name

        self.pedestals: List[PerkPedestal] = []
        self.shop_items: List[ShopItem] = []
        self.healed_player: bool = False
        self.tuning_active: bool = False

        # Altar & portal positions
        self.heal_pool_pos = (start_x + 50, start_y + height - 25)
        self.tuning_altar_pos = (start_x + 130, start_y + height - 25)
        self.exit_shaft_pos = (start_x + width - 40, start_y + height - 10)
        self.side_portal_pos = (start_x + 30, start_y + 40)

    def generate_structure(self, grid: SimulationGrid) -> None:
        """Carve the holy mountain chamber out of indestructible bone."""
        x0, y0 = self.x, self.y
        w, h = self.width, self.height

        # 1. Clear interior room
        grid.fill_rect(x0, y0, w, h, MAT_AIR)

        # 2. Build unbreakable outer bone frame
        # Floor
        grid.fill_rect(x0, y0 + h - 10, w, 10, MAT_WALL_BONE)
        # Ceiling
        grid.fill_rect(x0, y0, w, 8, MAT_WALL_BONE)
        # Left wall
        grid.fill_rect(x0, y0, 8, h, MAT_WALL_BONE)
        # Right wall
        grid.fill_rect(x0 + w - 8, y0, 8, h, MAT_WALL_BONE)

        # 3. Create Mitosis Healing Pool (filled with pure Lymph)
        hx, hy = self.heal_pool_pos
        grid.fill_rect(hx - 15, hy - 4, 30, 8, MAT_LYMPH)
        # Basin structure
        grid.fill_rect(hx - 18, hy - 2, 3, 10, MAT_BONE)
        grid.fill_rect(hx + 15, hy - 2, 3, 10, MAT_BONE)

        # 4. Create Exit Shaft on right
        ex, ey = self.exit_shaft_pos
        grid.fill_rect(ex - 15, ey - 4, 30, 30, MAT_AIR)

        # 4b. If side branch enabled, carve upper-left access niche
        if self.has_side_path:
            sx, sy = self.side_portal_pos
            grid.fill_rect(sx - 16, sy - 16, 32, 32, MAT_AIR)
            grid.fill_rect(sx - 20, sy + 18, 40, 6, MAT_BONE)

        # 5. Populate 3 Perks
        self.pedestals.clear()
        perks = getRandomPerks(count=3)
        perk_start_x = self.x + 190
        for i, perk in enumerate(perks):
            px = perk_start_x + i * 40
            py = self.y + self.height - 30
            self.pedestals.append(PerkPedestal(px, py, perk))

        # 6. Populate Shop
        self.shop_items.clear()
        shop_start_x = self.x + 90
        # 1 Cannula
        new_cannula = OrganCannula(
            name=random.choice(["Tentakel-Röhre", "Zytotox-Injektor", "Chitin-Kanone"]),
            capacity=random.randint(3, 7),
            cast_delay=round(random.uniform(0.08, 0.22), 2),
            recharge_time=round(random.uniform(0.35, 0.75), 2),
            biomass_max=random.randint(90, 220),
            biomass_recharge=random.randint(35, 75),
            spread=round(random.uniform(1.0, 5.0), 1),
            shuffle=random.choice([False, True]),
        )
        self.shop_items.append(ShopItem(shop_start_x, self.y + self.height - 30, new_cannula, cost=40, is_cannula=True))

        # 2 Genes
        available_genes = [g for g in GENE_LIBRARY if g.id not in ("BONE_SPIKE", "ACID_GLOBULE")]
        for j in range(2):
            g = random.choice(available_genes)
            cost = int(g.biomass_cost * 2.5) + 15
            self.shop_items.append(
                ShopItem(shop_start_x + (j + 1) * 32, self.y + self.height - 30, g, cost=cost, is_cannula=False)
            )

    def update(self, player, interact_pressed: bool = False) -> Optional[MutationPerk]:
        """Check player interaction with healing pool, perks, and shop."""
        # 1. Healing Pool
        hx, hy = self.heal_pool_pos
        if abs(player.center_x - hx) < 25 and abs(player.center_y - hy) < 20:
            if not self.healed_player:
                player.heal(player.max_hp)
                self.healed_player = True

        # 2. Perks
        for ped in self.pedestals:
            if not ped.collected:
                dist = abs(player.center_x - ped.x) + abs(player.center_y - ped.y)
                if (dist < 22 and interact_pressed) or dist < 14:
                    ped.collected = True
                    # Discard other pedestals (choose 1 of 3 like Noita)
                    for other in self.pedestals:
                        other.collected = True
                    return ped.perk

        # 3. Shop items
        for item in self.shop_items:
            if not item.purchased:
                dist = abs(player.center_x - item.x) + abs(player.center_y - item.y)
                if ((dist < 22 and interact_pressed) or dist < 14) and player.biomass_currency >= item.cost:
                    player.biomass_currency -= item.cost
                    item.purchased = True
                    if item.is_cannula:
                        if len(player.cannulas) < 4:
                            player.cannulas.append(item.item)
                        else:
                            player.cannulas[player.active_cannula_index] = item.item
                    else:
                        # Add gene to active cannula or first free slot
                        added = False
                        for c in player.cannulas:
                            if c.add_gene(item.item):
                                added = True
                                break
                        if not added and player.cannulas:
                            player.cannulas[player.active_cannula_index].slots[0] = item.item

        return None

    def _draw_info_card(
        self,
        surface: pygame.Surface,
        cam_x: int,
        cam_y: int,
        font: pygame.font.Font,
        title: str,
        category: str,
        desc_lines: List[str],
        cost_text: Optional[str] = None,
        cost_affordable: bool = True,
        prompt: str = "[E] Berühren",
        accent_color: Tuple[int, int, int] = (220, 200, 80),
        world_x: float = 0.0,
        world_y: float = 0.0,
    ) -> None:
        """Render a styled floating info card without obscuring neighboring pedestals."""
        # Render text surfaces
        cat_surf = font.render(category, True, (160, 160, 180))
        title_surf = font.render(title, True, accent_color)
        rendered_desc = [font.render(line, True, (215, 215, 225)) for line in desc_lines]
        cost_surf = None
        if cost_text:
            cost_col = (110, 255, 130) if cost_affordable else (255, 90, 90)
            cost_surf = font.render(cost_text, True, cost_col)
        prompt_surf = font.render(prompt, True, (255, 230, 110))

        # Measure dimensions
        all_surfs = [cat_surf, title_surf] + rendered_desc
        if cost_surf:
            all_surfs.append(cost_surf)
        all_surfs.append(prompt_surf)

        pad_x = 8
        pad_y = 6
        line_spacing = 2
        card_w = max(130, max(s.get_width() for s in all_surfs) + pad_x * 2)
        card_h = pad_y * 2 + sum(s.get_height() for s in all_surfs) + line_spacing * (len(all_surfs) - 1) + 4

        # Calculate position centered over pedestal
        cx = int(world_x - cam_x)
        cy = int(world_y - cam_y)
        card_x = cx - card_w // 2
        card_y = cy - card_h - 18

        # Prevent clipping beyond screen bounds
        sw = surface.get_width()
        sh = surface.get_height()
        card_x = max(6, min(card_x, sw - card_w - 6))
        if card_y < 6:
            card_y = cy + 24
        card_y = max(6, min(card_y, sh - card_h - 6))

        # Render panel
        card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        card_surf.fill((18, 16, 26, 235))
        pygame.draw.rect(card_surf, accent_color, (0, 0, card_w, card_h), 1, border_radius=4)
        # Separator line under title
        sep_y = pad_y + cat_surf.get_height() + line_spacing + title_surf.get_height() + 2
        pygame.draw.line(card_surf, (accent_color[0] // 2, accent_color[1] // 2, accent_color[2] // 2), (pad_x, sep_y), (card_w - pad_x, sep_y), 1)

        # Blit text
        curr_y = pad_y
        card_surf.blit(cat_surf, (pad_x, curr_y))
        curr_y += cat_surf.get_height() + line_spacing

        card_surf.blit(title_surf, (pad_x, curr_y))
        curr_y += title_surf.get_height() + line_spacing + 4

        for ds in rendered_desc:
            card_surf.blit(ds, (pad_x, curr_y))
            curr_y += ds.get_height() + line_spacing

        if cost_surf:
            curr_y += 2
            card_surf.blit(cost_surf, (pad_x, curr_y))
            curr_y += cost_surf.get_height() + line_spacing

        curr_y += 2
        card_surf.blit(prompt_surf, (pad_x, curr_y))

        surface.blit(card_surf, (card_x, card_y))

    def draw(
        self,
        surface: pygame.Surface,
        cam_x: int,
        cam_y: int,
        font: pygame.font.Font,
        player=None,
        mouse_world: Optional[Tuple[float, float]] = None,
    ) -> None:
        """Render pedestals, shop items, and room markers with dynamic tooltip cards."""
        import math

        # Draw pedestals
        for ped in self.pedestals:
            ped.draw(surface, cam_x, cam_y, font)

        # Draw shop items
        for item in self.shop_items:
            item.draw(surface, cam_x, cam_y, font)

        # Healing pool text
        hx, hy = self.heal_pool_pos
        sx = int(hx - cam_x)
        sy = int(hy - cam_y)
        if -50 <= sx <= surface.get_width() + 50:
            heal_label = font.render("+ MITOSE-POOL +", True, (150, 255, 180))
            surface.blit(heal_label, (sx - heal_label.get_width() // 2, sy - 20))

        # Side path portal
        if self.has_side_path:
            spx, spy = self.side_portal_pos
            ssx = int(spx - cam_x)
            ssy = int(spy - cam_y)
            if -50 <= ssx <= surface.get_width() + 50:
                pulse = math.sin(pygame.time.get_ticks() * 0.006) * 2.5
                pygame.draw.circle(surface, (180, 210, 30), (ssx, ssy), int(14 + pulse), 2)
                pygame.draw.circle(surface, (140, 180, 20), (ssx, ssy), 7)
                side_label = font.render(f"[SEITENPFAD: {self.side_biome_name.upper()}]", True, (210, 240, 90))
                surface.blit(side_label, (ssx - side_label.get_width() // 2, ssy - 22))

        # Dynamic single info card for closest focused pedestal or shop item
        focused_target = None
        min_dist = float("inf")

        # 1. Check mouse hover first (< 22px)
        if mouse_world is not None:
            mx, my = mouse_world
            for ped in self.pedestals:
                if not ped.collected:
                    d = math.hypot(mx - ped.x, my - ped.y)
                    if d < 22.0 and d < min_dist:
                        min_dist = d
                        focused_target = ("PERK", ped)
            for item in self.shop_items:
                if not item.purchased:
                    d = math.hypot(mx - item.x, my - item.y)
                    if d < 22.0 and d < min_dist:
                        min_dist = d
                        focused_target = ("SHOP", item)

        # 2. If no mouse hover, check player proximity (< 35px)
        if focused_target is None and player is not None:
            px, py = player.center_x, player.center_y
            for ped in self.pedestals:
                if not ped.collected:
                    d = math.hypot(px - ped.x, py - ped.y)
                    if d < 35.0 and d < min_dist:
                        min_dist = d
                        focused_target = ("PERK", ped)
            for item in self.shop_items:
                if not item.purchased:
                    d = math.hypot(px - item.x, py - item.y)
                    if d < 35.0 and d < min_dist:
                        min_dist = d
                        focused_target = ("SHOP", item)

        if focused_target is not None:
            target_type, target_obj = focused_target
            if target_type == "PERK":
                ped = target_obj
                perk = ped.perk
                cat = "[HOHE MUTATION]" if perk.is_high_risk else "[GEN-MUTATION]"
                acc = (255, 85, 85) if perk.is_high_risk else perk.color
                prompt = "[E] Assimilieren"
                # Split description into manageable lines
                words = perk.description.split()
                lines = []
                curr = ""
                for w in words:
                    test = f"{curr} {w}".strip()
                    if font.size(test)[0] <= 165:
                        curr = test
                    else:
                        if curr:
                            lines.append(curr)
                        curr = w
                if curr:
                    lines.append(curr)

                self._draw_info_card(
                    surface,
                    cam_x,
                    cam_y,
                    font,
                    title=perk.name,
                    category=cat,
                    desc_lines=lines,
                    cost_text=None,
                    cost_affordable=True,
                    prompt=prompt,
                    accent_color=acc,
                    world_x=ped.x,
                    world_y=ped.y,
                )
            elif target_type == "SHOP":
                item = target_obj
                player_bio = player.biomass_currency if player else 0
                affordable = player_bio >= item.cost
                cost_text = f"Kosten: {item.cost} Biomasse" if affordable else f"Kosten: {item.cost} Biomasse (Fehlt!)"
                prompt = "[E] Kaufen" if affordable else "[Zu wenig Biomasse]"

                if item.is_cannula:
                    c = item.item
                    cat = "[ORGAN-KANÜLE]"
                    title = c.name
                    acc = (200, 110, 240)
                    lines = [
                        f"Kapazität: {c.capacity} | Streuung: {c.spread}°",
                        f"Verzögerung: {c.cast_delay}s | Ladez.: {c.recharge_time}s",
                        f"Biomasse: {c.biomass_max} (+{c.biomass_recharge}/s)",
                    ]
                else:
                    g = item.item
                    cat = f"[GEN: {g.gene_type}]"
                    title = g.name
                    acc = getattr(g, "color", (240, 200, 80))
                    words = g.description.split()
                    lines = []
                    curr = ""
                    for w in words:
                        test = f"{curr} {w}".strip()
                        if font.size(test)[0] <= 165:
                            curr = test
                        else:
                            if curr:
                                lines.append(curr)
                            curr = w
                    if curr:
                        lines.append(curr)
                    lines.append(f"Verbrauch: {g.biomass_cost} Biomasse")

                self._draw_info_card(
                    surface,
                    cam_x,
                    cam_y,
                    font,
                    title=title,
                    category=cat,
                    desc_lines=lines,
                    cost_text=cost_text,
                    cost_affordable=affordable,
                    prompt=prompt,
                    accent_color=acc,
                    world_x=item.x,
                    world_y=item.y,
                )

    def is_player_in_side_portal(self, player) -> bool:
        """Check if player is stepping through the side path portal."""
        if not self.has_side_path:
            return False
        spx, spy = self.side_portal_pos
        import math
        return math.hypot(player.center_x - spx, player.center_y - spy) < 18.0

