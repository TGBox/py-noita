"""Deck evaluation engine: Triggers, modifiers, multicast, and wand wrapping."""

import math
import random
from typing import List, Optional, Tuple

from py_noita.weapons.cannula import OrganCannula
from py_noita.weapons.gene import Gene, GeneType
from py_noita.weapons.projectile import Projectile
from py_noita.simulation.materials import MAT_AIR


class CastState:
    """Accumulated state across modifiers for the current cast burst."""

    def __init__(self):
        self.damage_add: float = 0.0
        self.speed_mult: float = 1.0
        self.lifetime_add: int = 0
        self.spread_add: float = 0.0
        self.homing: bool = False
        self.piercing: bool = False
        self.trail_mat: int = MAT_AIR
        self.impact_mat: int = MAT_AIR
        self.impact_mat_count: int = 0
        self.cast_delay_mod: float = 0.0
        self.recharge_mod: float = 0.0
        self.explosion_radius: int = 0

    def apply_modifier(self, gene: Gene) -> None:
        """Apply a modifier gene to this cast state."""
        self.damage_add += gene.damage
        if gene.speed > 0:
            self.speed_mult *= gene.speed
        self.cast_delay_mod += gene.cast_delay_mod
        self.recharge_mod += gene.recharge_mod
        self.spread_add += gene.spread_mod
        if gene.homing:
            self.homing = True
        if gene.piercing:
            self.piercing = True
        if gene.trail_material != MAT_AIR:
            self.trail_mat = gene.trail_material
        if gene.impact_material != MAT_AIR:
            self.impact_mat = gene.impact_material
            self.impact_mat_count += gene.impact_material_count
        if gene.explosion_radius > 0:
            self.explosion_radius = max(self.explosion_radius, gene.explosion_radius)


def evaluate_cannula_fire(
    cannula: OrganCannula,
    origin_x: float,
    origin_y: float,
    base_angle: float,
    owner: str = "PLAYER",
) -> List[Projectile]:
    """Evaluate one cast burst from the active cannula according to Noita wand logic."""
    if not cannula.can_fire():
        return []

    active_genes = cannula.genes
    num_genes = len(active_genes)
    if num_genes == 0:
        return []

    # Get execution sequence
    if cannula.shuffle:
        sequence = list(range(num_genes))
        random.shuffle(sequence)
        pointer = 0
    else:
        sequence = list(range(num_genes))
        pointer = cannula.deck_pointer

    spawned_projectiles: List[Projectile] = []
    cast_state = CastState()
    needed_projectiles = 1
    projectiles_cast = 0
    genes_evaluated = 0

    while genes_evaluated < num_genes and projectiles_cast < needed_projectiles:
        idx = sequence[pointer]
        gene = active_genes[idx]

        pointer = (pointer + 1) % num_genes
        genes_evaluated += 1

        # Check biomass cost
        if cannula.current_biomass >= gene.biomass_cost:
            cannula.current_biomass -= gene.biomass_cost
        else:
            # Insufficient biomass: skip or fizzle
            continue

        cast_state.cast_delay_mod += gene.cast_delay_mod
        cast_state.recharge_mod += gene.recharge_mod

        # MODIFIER
        if gene.gene_type == GeneType.MODIFIER:
            cast_state.apply_modifier(gene)

        # MULTICAST
        elif gene.gene_type == GeneType.MULTICAST:
            needed_projectiles += gene.multicast_count - 1
            cast_state.spread_add += gene.spread_mod

        # TRIGGER
        elif gene.gene_type == GeneType.TRIGGER:
            # Capture subsequent gene(s) as payload
            payload: List[Gene] = []
            if genes_evaluated < num_genes:
                next_idx = sequence[pointer]
                payload.append(active_genes[next_idx])
                pointer = (pointer + 1) % num_genes
                genes_evaluated += 1

            proj = _create_projectile(
                gene,
                cast_state,
                origin_x,
                origin_y,
                base_angle,
                cannula.spread,
                owner,
                payload=payload,
            )
            spawned_projectiles.append(proj)
            projectiles_cast += 1

        # REGULAR PROJECTILE
        elif gene.gene_type == GeneType.PROJECTILE:
            proj = _create_projectile(
                gene,
                cast_state,
                origin_x,
                origin_y,
                base_angle,
                cannula.spread,
                owner,
            )
            spawned_projectiles.append(proj)
            projectiles_cast += 1

    # Update cannula cooldowns and deck pointer
    if cannula.shuffle:
        cannula.deck_pointer = 0
        cannula.start_recharge(cast_state.recharge_mod)
    else:
        cannula.deck_pointer = pointer
        # Apply cast delay
        total_delay = max(0.04, cannula.cast_delay + cast_state.cast_delay_mod)
        cannula.cast_cooldown = total_delay

        # If wrapped to the start of deck, enter recharge
        if pointer == 0 or genes_evaluated >= num_genes:
            cannula.start_recharge(cast_state.recharge_mod)

    return spawned_projectiles


def _create_projectile(
    gene: Gene,
    state: CastState,
    x: float,
    y: float,
    angle: float,
    wand_spread: float,
    owner: str,
    payload: Optional[List[Gene]] = None,
) -> Projectile:
    """Build a Projectile instance combining Gene and CastState attributes."""
    total_spread_deg = wand_spread + state.spread_add + gene.spread_mod
    spread_rad = math.radians(random.uniform(-total_spread_deg / 2.0, total_spread_deg / 2.0))
    final_angle = angle + spread_rad

    final_speed = gene.speed * state.speed_mult
    final_damage = gene.damage + state.damage_add
    final_lifetime = gene.lifetime + state.lifetime_add

    trail_mat = state.trail_mat if state.trail_mat != MAT_AIR else gene.trail_material
    impact_mat = state.impact_mat if state.impact_mat != MAT_AIR else gene.impact_material
    impact_count = max(gene.impact_material_count, state.impact_mat_count)
    exp_rad = max(gene.explosion_radius, state.explosion_radius)

    return Projectile(
        x=x,
        y=y,
        vx=math.cos(final_angle) * final_speed,
        vy=math.sin(final_angle) * final_speed,
        damage=final_damage,
        lifetime=final_lifetime,
        radius=gene.radius,
        color=gene.color,
        piercing=state.piercing or gene.piercing,
        homing=state.homing or gene.homing,
        trail_material=trail_mat,
        impact_material=impact_mat,
        impact_material_count=impact_count,
        explosion_radius=exp_rad,
        payload_genes=payload,
        owner=owner,
    )


def evaluate_payload(
    payload_genes: List[Gene],
    origin_x: float,
    origin_y: float,
    base_angle: float,
    owner: str = "PLAYER",
) -> List[Projectile]:
    """Evaluate payload genes on trigger impact or timer expiration."""
    spawned: List[Projectile] = []
    cast_state = CastState()

    for gene in payload_genes:
        if gene.gene_type == GeneType.MODIFIER:
            cast_state.apply_modifier(gene)
        elif gene.gene_type in (GeneType.PROJECTILE, GeneType.TRIGGER):
            proj = _create_projectile(
                gene,
                cast_state,
                origin_x,
                origin_y,
                base_angle,
                wand_spread=10.0,
                owner=owner,
            )
            spawned.append(proj)

    return spawned
