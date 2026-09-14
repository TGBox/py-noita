"""Deck evaluation engine: Triggers, modifiers, multicast, formations, and wand wrapping."""

import math
import random
from typing import Any, List, Optional, Tuple

from py_noita.simulation.materials import MAT_AIR
from py_noita.weapons.cannula import OrganCannula
from py_noita.weapons.gene import Gene, GeneType
from py_noita.weapons.projectile import Projectile


class CastState:
    """Accumulated state across modifiers for the current cast burst."""

    def __init__(self):
        self.damage_add: float = 0.0
        self.damage_mult: float = 1.0
        self.speed_mult: float = 1.0
        self.lifetime_add: int = 0
        self.spread_add: float = 0.0
        self.homing: bool = False
        self.piercing: bool = False
        self.bounce_add: int = 0
        self.vampiric: bool = False
        self.gravity: float = 0.0
        self.slow_effect: bool = False
        self.trail_mat: int = MAT_AIR
        self.impact_mat: int = MAT_AIR
        self.impact_mat_count: int = 0
        self.cast_delay_mod: float = 0.0
        self.recharge_mod: float = 0.0
        self.explosion_radius: int = 0
        self.formation_type: str = "NONE"
        self.pattern: str = "NORMAL"
        self.transmute_source: Optional[List[int]] = None
        self.transmute_target: int = MAT_AIR
        self.transmute_radius: int = 0

    def apply_modifier(self, gene: Gene) -> None:
        """Apply a modifier gene to this cast state."""
        self.damage_add += gene.damage
        if gene.speed > 0:
            self.speed_mult *= gene.speed
        if getattr(gene, "critical_chance", 0.0) > 0.0:
            if random.random() < gene.critical_chance:
                self.damage_mult *= 4.0
        self.cast_delay_mod += gene.cast_delay_mod
        self.recharge_mod += gene.recharge_mod
        self.spread_add += gene.spread_mod
        self.lifetime_add += gene.lifetime
        self.bounce_add += gene.bounce
        if gene.gravity != 0.0:
            self.gravity = gene.gravity
        if gene.homing:
            self.homing = True
        if gene.piercing:
            self.piercing = True
        if getattr(gene, "vampiric", False):
            self.vampiric = True
        if getattr(gene, "slow_effect", False):
            self.slow_effect = True
        if getattr(gene, "pattern", "NORMAL") != "NORMAL":
            self.pattern = gene.pattern
        if gene.trail_material != MAT_AIR:
            self.trail_mat = gene.trail_material
        if gene.impact_material != MAT_AIR:
            self.impact_mat = gene.impact_material
            self.impact_mat_count += gene.impact_material_count
        if gene.explosion_radius > 0:
            self.explosion_radius = max(self.explosion_radius, gene.explosion_radius)
        if getattr(gene, "transmute_radius", 0) > 0 and getattr(gene, "transmute_target", MAT_AIR) != MAT_AIR:
            self.transmute_source = gene.transmute_source
            self.transmute_target = gene.transmute_target
            self.transmute_radius = max(self.transmute_radius, gene.transmute_radius)


def evaluate_cannula_fire(
    cannula: OrganCannula,
    origin_x: float,
    origin_y: float,
    base_angle: float,
    owner: str = "PLAYER",
    shooter: Optional[Any] = None,
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
            continue

        cast_state.cast_delay_mod += gene.cast_delay_mod
        cast_state.recharge_mod += gene.recharge_mod

        # MODIFIER
        if gene.gene_type == GeneType.MODIFIER:
            cast_state.apply_modifier(gene)

        # MULTICAST / FORMATION
        elif gene.gene_type == GeneType.MULTICAST:
            if getattr(gene, "formation_type", "NONE") != "NONE":
                cast_state.formation_type = gene.formation_type
            needed_projectiles += gene.multicast_count - 1
            cast_state.spread_add += gene.spread_mod

        # TRIGGER
        elif gene.gene_type == GeneType.TRIGGER:
            payload: List[Gene] = []
            if genes_evaluated < num_genes:
                next_idx = sequence[pointer]
                payload.append(active_genes[next_idx])
                pointer = (pointer + 1) % num_genes
                genes_evaluated += 1

            new_projs = _dispatch_formation_projectiles(
                gene,
                cast_state,
                origin_x,
                origin_y,
                base_angle,
                cannula.spread,
                owner,
                payload=payload,
                shooter=shooter,
            )
            spawned_projectiles.extend(new_projs)
            projectiles_cast += max(1, len(new_projs))

        # REGULAR PROJECTILE
        elif gene.gene_type == GeneType.PROJECTILE:
            new_projs = _dispatch_formation_projectiles(
                gene,
                cast_state,
                origin_x,
                origin_y,
                base_angle,
                cannula.spread,
                owner,
                payload=None,
                shooter=shooter,
            )
            spawned_projectiles.extend(new_projs)
            projectiles_cast += max(1, len(new_projs))

        # META-GENES (Polymerase Duplicators, RNA Loop, Ribosome Catalyst, Ur-Code Alpha/Omega)
        elif gene.gene_type == GeneType.META:
            m_type = getattr(gene, "meta_type", "NONE")
            if m_type.startswith("DIVIDE_"):
                mult = getattr(gene, "meta_multiplier", 1)
                # Look ahead for target gene
                if genes_evaluated < num_genes:
                    target_idx = sequence[pointer]
                    target_gene = active_genes[target_idx]
                    pointer = (pointer + 1) % num_genes
                    genes_evaluated += 1

                    # Apply recursion brake: if chaining multiple Divide By, cap multiplier
                    polymerase_chains = [g for g in active_genes if getattr(g, "meta_type", "").startswith("DIVIDE_")]
                    if len(polymerase_chains) > 3:
                        mult = min(mult, 4)

                    if target_gene.gene_type == GeneType.MODIFIER:
                        for _ in range(mult):
                            cast_state.apply_modifier(target_gene)
                    elif target_gene.gene_type == GeneType.MULTICAST:
                        needed_projectiles += (target_gene.multicast_count - 1) * mult
                    elif target_gene.gene_type in (GeneType.PROJECTILE, GeneType.TRIGGER):
                        for _ in range(mult):
                            sub_projs = _dispatch_formation_projectiles(
                                target_gene,
                                cast_state,
                                origin_x,
                                origin_y,
                                base_angle,
                                cannula.spread,
                                owner,
                                payload=None,
                                shooter=shooter,
                            )
                            spawned_projectiles.extend(sub_projs)
                            projectiles_cast += max(1, len(sub_projs))

            elif m_type == "COPY_FIRST":
                first_gene = next((g for g in cannula.genes if g.gene_type != GeneType.META), None)
                if first_gene:
                    if first_gene.gene_type == GeneType.MODIFIER:
                        cast_state.apply_modifier(first_gene)
                    elif first_gene.gene_type in (GeneType.PROJECTILE, GeneType.TRIGGER):
                        sub_projs = _dispatch_formation_projectiles(
                            first_gene, cast_state, origin_x, origin_y, base_angle, cannula.spread, owner, payload=None, shooter=shooter
                        )
                        spawned_projectiles.extend(sub_projs)
                        projectiles_cast += max(1, len(sub_projs))
                    elif first_gene.gene_type == GeneType.MULTICAST:
                        needed_projectiles += first_gene.multicast_count - 1

            elif m_type == "COPY_LAST":
                last_gene = next((g for g in reversed(cannula.genes) if g.gene_type != GeneType.META), None)
                if last_gene:
                    if last_gene.gene_type == GeneType.MODIFIER:
                        cast_state.apply_modifier(last_gene)
                    elif last_gene.gene_type in (GeneType.PROJECTILE, GeneType.TRIGGER):
                        sub_projs = _dispatch_formation_projectiles(
                            last_gene, cast_state, origin_x, origin_y, base_angle, cannula.spread, owner, payload=None, shooter=shooter
                        )
                        spawned_projectiles.extend(sub_projs)
                        projectiles_cast += max(1, len(sub_projs))
                    elif last_gene.gene_type == GeneType.MULTICAST:
                        needed_projectiles += last_gene.multicast_count - 1

            elif m_type == "LOOP_FIRST":
                if cannula.genes:
                    fg = cannula.genes[0]
                    if fg.gene_type == GeneType.MODIFIER:
                        cast_state.apply_modifier(fg)
                    elif fg.gene_type in (GeneType.PROJECTILE, GeneType.TRIGGER):
                        sub_projs = _dispatch_formation_projectiles(
                            fg, cast_state, origin_x, origin_y, base_angle, cannula.spread, owner, payload=None, shooter=shooter
                        )
                        spawned_projectiles.extend(sub_projs)
                        projectiles_cast += max(1, len(sub_projs))

            elif m_type == "RANDOM_DISCARD":
                candidates = [g for g in cannula.genes if g.gene_type != GeneType.META]
                if candidates:
                    rand_gene = random.choice(candidates)
                    if cannula.current_biomass < rand_gene.biomass_cost and shooter is not None:
                        if hasattr(shooter, "hp"):
                            shooter.hp = max(1.0, shooter.hp - 2.0)
                    if rand_gene.gene_type == GeneType.MODIFIER:
                        cast_state.apply_modifier(rand_gene)

                    elif rand_gene.gene_type in (GeneType.PROJECTILE, GeneType.TRIGGER):
                        sub_projs = _dispatch_formation_projectiles(
                            rand_gene, cast_state, origin_x, origin_y, base_angle, cannula.spread, owner, payload=None, shooter=shooter
                        )
                        spawned_projectiles.extend(sub_projs)
                        projectiles_cast += max(1, len(sub_projs))


    # Update cannula cooldowns and deck pointer
    if cannula.shuffle:
        cannula.deck_pointer = 0
        cannula.start_recharge(cast_state.recharge_mod)
    else:
        cannula.deck_pointer = pointer
        total_delay = max(0.04, cannula.cast_delay + cast_state.cast_delay_mod)
        cannula.cast_cooldown = total_delay

        if pointer == 0 or genes_evaluated >= num_genes:
            cannula.start_recharge(cast_state.recharge_mod)

    return spawned_projectiles


def _dispatch_formation_projectiles(
    gene: Gene,
    state: CastState,
    x: float,
    y: float,
    base_angle: float,
    wand_spread: float,
    owner: str,
    payload: Optional[List[Gene]] = None,
    shooter: Optional[Any] = None,
) -> List[Projectile]:
    """Emit one or multiple projectiles according to active multicast/formation layout."""
    fmt = state.formation_type

    if fmt == "DOUBLE_HELIX":
        p1 = _create_projectile(gene, state, x, y, base_angle, wand_spread, owner, payload, shooter, forced_pattern="HELIX_A")
        p2 = _create_projectile(gene, state, x, y, base_angle, wand_spread, owner, payload, shooter, forced_pattern="HELIX_B")
        return [p1, p2]

    elif fmt == "FAN_3":
        offsets = [-math.radians(15.0), 0.0, math.radians(15.0)]
        return [_create_projectile(gene, state, x, y, base_angle, wand_spread, owner, payload, shooter, angle_offset=off) for off in offsets]

    elif fmt == "FAN_5":
        offsets = [-math.radians(30.0), -math.radians(15.0), 0.0, math.radians(15.0), math.radians(30.0)]
        return [_create_projectile(gene, state, x, y, base_angle, wand_spread, owner, payload, shooter, angle_offset=off) for off in offsets]

    elif fmt == "RADIAL_8":
        offsets = [(i / 8.0) * math.pi * 2.0 for i in range(8)]
        return [_create_projectile(gene, state, x, y, 0.0, 0.0, owner, payload, shooter, angle_offset=off) for off in offsets]

    elif fmt == "RADIAL_12":
        offsets = [(i / 12.0) * math.pi * 2.0 for i in range(12)]
        return [_create_projectile(gene, state, x, y, 0.0, 0.0, owner, payload, shooter, angle_offset=off) for off in offsets]

    elif fmt == "ORBITAL_2":
        return [
            _create_projectile(gene, state, x, y, 0.0, 0.0, owner, payload, shooter, forced_pattern="ORBIT", orbit_angle=0.0),
            _create_projectile(gene, state, x, y, 0.0, 0.0, owner, payload, shooter, forced_pattern="ORBIT", orbit_angle=math.pi),
        ]

    elif fmt == "ORBITAL_4":
        return [
            _create_projectile(gene, state, x, y, 0.0, 0.0, owner, payload, shooter, forced_pattern="ORBIT", orbit_angle=(i / 4.0) * math.pi * 2.0)
            for i in range(4)
        ]

    elif fmt == "FRONT_BACK":
        offsets = [0.0, math.pi]
        return [_create_projectile(gene, state, x, y, base_angle, wand_spread, owner, payload, shooter, angle_offset=off) for off in offsets]

    elif fmt == "TRI_DIRECTIONAL":
        offsets = [0.0, (2.0 * math.pi / 3.0), (4.0 * math.pi / 3.0)]
        return [_create_projectile(gene, state, x, y, base_angle, 0.0, owner, payload, shooter, angle_offset=off) for off in offsets]

    elif fmt == "QUAD_CARDINAL":
        offsets = [0.0, math.pi / 2.0, math.pi, 3.0 * math.pi / 2.0]
        return [_create_projectile(gene, state, x, y, base_angle, 0.0, owner, payload, shooter, angle_offset=off) for off in offsets]

    elif fmt == "HEX_BURST":
        offsets = [(i / 6.0) * math.pi * 2.0 for i in range(6)]
        return [_create_projectile(gene, state, x, y, 0.0, 0.0, owner, payload, shooter, angle_offset=off) for off in offsets]

    elif fmt == "LINE_STREAM":
        # Staggered 3 bullets in a line
        return [
            _create_projectile(gene, state, x - math.cos(base_angle) * i * 6.0, y - math.sin(base_angle) * i * 6.0, base_angle, wand_spread, owner, payload, shooter)
            for i in range(3)
        ]

    # Standard single projectile
    return [_create_projectile(gene, state, x, y, base_angle, wand_spread, owner, payload, shooter)]


def _create_projectile(
    gene: Gene,
    state: CastState,
    x: float,
    y: float,
    angle: float,
    wand_spread: float,
    owner: str,
    payload: Optional[List[Gene]] = None,
    shooter: Optional[Any] = None,
    angle_offset: float = 0.0,
    orbit_angle: float = 0.0,
    forced_pattern: Optional[str] = None,
) -> Projectile:
    """Build a Projectile instance combining Gene and CastState attributes."""
    total_spread_deg = wand_spread + state.spread_add + gene.spread_mod
    spread_rad = math.radians(random.uniform(-total_spread_deg / 2.0, total_spread_deg / 2.0))
    final_angle = angle + angle_offset + spread_rad

    final_speed = gene.speed * state.speed_mult
    final_damage = (gene.damage + state.damage_add) * state.damage_mult
    final_lifetime = max(5, gene.lifetime + state.lifetime_add)

    trail_mat = state.trail_mat if state.trail_mat != MAT_AIR else gene.trail_material
    impact_mat = state.impact_mat if state.impact_mat != MAT_AIR else gene.impact_material
    impact_count = max(gene.impact_material_count, state.impact_mat_count)
    exp_rad = max(gene.explosion_radius, state.explosion_radius)

    pattern = forced_pattern or (state.pattern if state.pattern != "NORMAL" else getattr(gene, "pattern", "NORMAL"))
    bounce_total = gene.bounce + state.bounce_add
    vamp = state.vampiric or getattr(gene, "vampiric", False)
    slow = state.slow_effect or getattr(gene, "slow_effect", False)
    grav = state.gravity if state.gravity != 0.0 else getattr(gene, "gravity", 0.0)

    trig_type = getattr(gene, "trigger_type", "NONE")
    prox_rad = getattr(gene, "proximity_radius", 0.0)
    pen_trig = (trig_type == "PENETRATION")

    trans_target = state.transmute_target if state.transmute_target != MAT_AIR else getattr(gene, "transmute_target", MAT_AIR)
    trans_source = state.transmute_source if state.transmute_source is not None else getattr(gene, "transmute_source", None)
    trans_rad = max(state.transmute_radius, getattr(gene, "transmute_radius", 0))

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
        trigger_type=trig_type,
        proximity_radius=prox_rad,
        penetration_trigger=pen_trig,
        pattern=pattern,
        bounce=bounce_total,
        vampiric=vamp,
        gravity=grav,
        slow_effect=slow,
        shooter=shooter,
        orbit_angle=orbit_angle,
        transmute_source=trans_source,
        transmute_target=trans_target,
        transmute_radius=trans_rad,
    )


def evaluate_payload(
    payload_genes: List[Gene],
    origin_x: float,
    origin_y: float,
    base_angle: float,
    owner: str = "PLAYER",
    shooter: Optional[Any] = None,
) -> List[Projectile]:
    """Evaluate payload genes on trigger impact or timer expiration."""
    spawned: List[Projectile] = []
    cast_state = CastState()

    for gene in payload_genes:
        if gene.gene_type == GeneType.MODIFIER:
            cast_state.apply_modifier(gene)
        elif gene.gene_type in (GeneType.PROJECTILE, GeneType.TRIGGER):
            projs = _dispatch_formation_projectiles(
                gene,
                cast_state,
                origin_x,
                origin_y,
                base_angle,
                wand_spread=10.0,
                owner=owner,
                payload=None,
                shooter=shooter,
            )
            spawned.extend(projs)

    return spawned
