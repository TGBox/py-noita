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
        pygame.draw.rect(surface, (140, 130, 120), (sx - 6, sy + 8, 12, 4))
        # Floating pulsating DNA orb
        glow_rad = 5
        pygame.draw.circle(surface, self.perk.color, (sx, sy), glow_rad)
        pygame.draw.circle(surface, (255, 255, 255), (sx, sy), 2)

        # Name label
        label = font.render(self.perk.name, True, (240, 230, 200))
        surface.blit(label, (sx - label.get_width() // 2, sy - 14))


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
        pygame.draw.rect(surface, col, (sx - 7, sy - 7, 14, 14), border_radius=3)

        # Cost text
        cost_text = font.render(f"{self.cost} B", True, (255, 220, 100))
        surface.blit(cost_text, (sx - cost_text.get_width() // 2, sy + 9))


class IncubationNode:
    """Manages the sanctuary chamber between biomes."""

    def __init__(self, start_x: int, start_y: int, width: int = 380, height: int = 140):
        self.x = start_x
        self.y = start_y
        self.width = width
        self.height = height

        self.pedestals: List[PerkPedestal] = []
        self.shop_items: List[ShopItem] = []
        self.healed_player: bool = False
        self.tuning_active: bool = False

        # Altar positions
        self.heal_pool_pos = (start_x + 50, start_y + height - 25)
        self.tuning_altar_pos = (start_x + 130, start_y + height - 25)
        self.exit_shaft_pos = (start_x + width - 40, start_y + height - 10)

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

    def update(self, player) -> Optional[MutationPerk]:
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
                if dist < 18:
                    ped.collected = True
                    # Discard other pedestals (choose 1 of 3 like Noita)
                    for other in self.pedestals:
                        other.collected = True
                    return ped.perk

        # 3. Shop items
        for item in self.shop_items:
            if not item.purchased:
                dist = abs(player.center_x - item.x) + abs(player.center_y - item.y)
                if dist < 16 and player.biomass_currency >= item.cost:
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

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int, font: pygame.font.Font) -> None:
        """Render pedestals, shop items, and room markers."""
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
