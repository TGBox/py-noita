"""Perk Manager to track and apply genetic mutation hooks."""

from typing import List, Set
from py_noita.perks.perk_definitions import MutationPerk
from py_noita.simulation.materials import MAT_SPORES


class PerkManager:
    """Tracks active mutation perks and applies gameplay hooks."""

    def __init__(self):
        self.active_perks: List[MutationPerk] = []
        self._perk_ids: Set[str] = set()

        # Shield cooldown
        self.shield_ready: bool = False
        self.shield_timer: float = 0.0

    def has_perk(self, perk_id: str) -> bool:
        return perk_id in self._perk_ids

    def add_perk(self, perk: MutationPerk, player) -> None:
        """Register perk and trigger immediate stat modifications."""
        self.active_perks.append(perk)
        self._perk_ids.add(perk.id)

        # Immediate stat modifications
        if perk.id == "GIANT_SYMBIOTE":
            player.max_hp *= 2.5
            player.hp = player.max_hp
            player.width = int(player.width * 1.5)
            player.height = int(player.height * 1.5)
        elif perk.id == "GLASS_CARAPACE":
            player.max_hp = 30.0
            player.hp = min(player.hp, 30.0)

    def modify_damage_taken(self, amount: float, source: str) -> float:
        """Hook to mitigate or nullify damage."""
        if source == "ACID" and self.has_perk("ACID_IMMUNITY"):
            return 0.0

        if self.has_perk("CYTOKINE_SHIELD") and self.shield_ready:
            self.shield_ready = False
            self.shield_timer = 10.0  # 10s cooldown
            return 0.0

        return amount

    def modify_damage_dealt(self, amount: float) -> float:
        """Hook to scale outgoing damage."""
        mult = 1.0
        if self.has_perk("GLASS_CARAPACE"):
            mult *= 3.5
        if self.has_perk("GIANT_SYMBIOTE"):
            mult *= 1.5
        return amount * mult

    def update(self, dt: float, player, grid) -> None:
        """Tick perk passive effects."""
        # Shield recovery
        if self.has_perk("CYTOKINE_SHIELD") and not self.shield_ready:
            self.shield_timer -= dt
            if self.shield_timer <= 0.0:
                self.shield_ready = True

        # Turbo flagella
        if self.has_perk("FLAGELLA_TURBO"):
            player.max_levitation = 140.0

        # Spore trail
        if self.has_perk("SPORE_TRAIL") and player.is_levitating:
            ix = int(player.center_x)
            iy = int(player.y + player.height + 2)
            if 1 <= ix < grid.width - 1 and 1 <= iy < grid.height - 1:
                if grid.is_empty(ix, iy):
                    grid.set_pixel(ix, iy, MAT_SPORES)
