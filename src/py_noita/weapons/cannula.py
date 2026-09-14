"""Organ-Cannula (living bio-wand) data structure and runtime state."""

from typing import List, Optional
import random

from py_noita.weapons.gene import Gene


class OrganCannula:
    """An organic injection cannula holding a sequence of genes/enzymes."""

    def __init__(
        self,
        name: str,
        capacity: int = 4,
        cast_delay: float = 0.15,
        recharge_time: float = 0.55,
        biomass_max: float = 120.0,
        biomass_recharge: float = 45.0,
        spread: float = 2.0,
        shuffle: bool = False,
    ):
        self.name = name
        self.capacity = capacity
        self.cast_delay = cast_delay
        self.recharge_time = recharge_time
        self.biomass_max = biomass_max
        self.biomass_recharge = biomass_recharge
        self.spread = spread
        self.shuffle = shuffle

        # Gene slots (list of length capacity)
        self.slots: List[Optional[Gene]] = [None] * capacity

        # Runtime state
        self.current_biomass: float = biomass_max
        self.cast_cooldown: float = 0.0
        self.recharge_cooldown: float = 0.0
        self.deck_pointer: int = 0
        self.is_recharging: bool = False

    @property
    def genes(self) -> List[Gene]:
        """Return non-empty gene cards currently installed."""
        return [g for g in self.slots if g is not None]

    def add_gene(self, gene: Gene) -> bool:
        """Add gene to the first available slot."""
        for i in range(self.capacity):
            if self.slots[i] is None:
                self.slots[i] = gene
                return True
        return False

    def set_slot(self, index: int, gene: Optional[Gene]) -> None:
        """Set or clear a specific slot."""
        if 0 <= index < self.capacity:
            self.slots[index] = gene

    def update(self, dt: float) -> None:
        """Tick cooldowns and recover biomass energy."""
        # Biomass recharge
        if self.current_biomass < self.biomass_max:
            self.current_biomass = min(self.biomass_max, self.current_biomass + self.biomass_recharge * dt)

        # Cast delay cooldown
        if self.cast_cooldown > 0.0:
            self.cast_cooldown = max(0.0, self.cast_cooldown - dt)

        # Wand recharge cooldown
        if self.recharge_cooldown > 0.0:
            self.recharge_cooldown = max(0.0, self.recharge_cooldown - dt)
            if self.recharge_cooldown <= 0.0:
                self.is_recharging = False
                self.deck_pointer = 0

    def can_fire(self) -> bool:
        """Check if cannula is ready to cast."""
        return self.cast_cooldown <= 0.0 and self.recharge_cooldown <= 0.0 and len(self.genes) > 0

    def start_recharge(self, total_recharge_mod: float = 0.0) -> None:
        """Enter wand recharge state."""
        duration = max(0.05, self.recharge_time + total_recharge_mod)
        self.recharge_cooldown = duration
        self.is_recharging = True
        self.deck_pointer = 0
