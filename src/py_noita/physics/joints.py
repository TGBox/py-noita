"""Joint, chain, tendon, and hanging object physics for Py-Noita."""

import math
import random
from typing import Any, List, Optional, Tuple
import pygame
import pymunk

from py_noita.physics.rigid_body import BioRigidBody
from py_noita.simulation.explosion import create_explosion
from py_noita.simulation.materials import (
    MAT_AIR,
    MAT_BILE,
    MAT_BIOGAS,
    MAT_BLOOD,
    MAT_FIRE,
    MAT_TISSUE,
)


class CartilageTendon:
    """An organic fibrous tendon connecting an anchor (e.g. cavern ceiling) to a hanging rigid body."""

    def __init__(
        self,
        space: pymunk.Space,
        anchor_x: float,
        anchor_y: float,
        target_body: BioRigidBody,
        length: Optional[float] = None,
        health: float = 20.0,
    ):
        self.space = space
        self.anchor_x = anchor_x
        self.anchor_y = anchor_y
        self.target_body = target_body
        self.health = health
        self.max_health = health
        self.severed = False

        # Attach via Pymunk SlideJoint
        anchor_b = (
            (0.0, -target_body.height * 0.45)
            if target_body.shape_type != "circle"
            else (0.0, -target_body.radius * 0.8)
        )
        world_b = target_body.body.local_to_world(anchor_b)
        dx = world_b.x - anchor_x
        dy = world_b.y - anchor_y
        self.length = length if length is not None else max(5.0, math.hypot(dx, dy))

        self.joint = pymunk.SlideJoint(
            space.static_body,
            target_body.body,
            (anchor_x, anchor_y),
            anchor_b,
            0.0,
            self.length,
        )
        self.space.add(self.joint)

    def sever(self) -> None:
        """Sever the tendon, releasing the attached body."""
        if not self.severed:
            self.severed = True
            if self.joint in self.space.constraints:
                self.space.remove(self.joint)
            if hasattr(self.target_body, "on_tendon_severed"):
                self.target_body.on_tendon_severed()

    def take_damage(self, amount: float) -> None:
        """Apply damage to the tendon strand; severs when health <= 0."""
        if self.severed:
            return
        self.health -= amount
        if self.health <= 0:
            self.sever()

    def distance_to(self, px: float, py: float) -> float:
        """Calculate the shortest distance between point (px, py) and the tendon segment."""
        ax, ay = self.anchor_x, self.anchor_y
        bx, by = self.target_body.x, self.target_body.y
        abx = bx - ax
        aby = by - ay
        seg_len_sq = abx * abx + aby * aby
        if seg_len_sq < 0.001:
            return math.hypot(px - ax, py - ay)
        apx = px - ax
        apy = py - ay
        t = max(0.0, min(1.0, (apx * abx + apy * aby) / seg_len_sq))
        proj_x = ax + t * abx
        proj_y = ay + t * aby
        return math.hypot(px - proj_x, py - proj_y)

    def check_hit(self, px: float, py: float, radius: float = 4.0) -> bool:
        """Check if a projectile or ray hits the tendon segment."""
        if self.severed or not self.target_body.alive:
            return False
        return self.distance_to(px, py) <= radius

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        """Render the fibrous cartilage tendon with organic nodules."""
        ax = int(round(self.anchor_x - cam_x))
        ay = int(round(self.anchor_y - cam_y))
        target_top_offset = (
            self.target_body.height * 0.45
            if self.target_body.shape_type != "circle"
            else self.target_body.radius * 0.8
        )
        bx = int(round(self.target_body.x - cam_x))
        by = int(round(self.target_body.y - target_top_offset - cam_y))

        if self.severed:
            # Draw severed tendon stump dangling from anchor
            stump_len = min(8, int(self.length * 0.3))
            pygame.draw.line(surface, (180, 160, 150), (ax, ay), (ax, ay + stump_len), 2)
            pygame.draw.circle(surface, (150, 60, 60), (ax, ay + stump_len), 2)
            return

        # Main tendon strand
        pygame.draw.line(surface, (195, 180, 165), (ax, ay), (bx, by), 2)
        pygame.draw.line(surface, (140, 100, 95), (ax, ay), (bx, by), 1)

        # Draw small cartilage nodes along the tendon
        dist = math.hypot(bx - ax, by - ay)
        if dist > 8:
            steps = max(1, int(dist // 10))
            for i in range(1, steps):
                t = i / steps
                nx = int(ax + t * (bx - ax))
                ny = int(ay + t * (by - ay))
                pygame.draw.circle(surface, (220, 205, 190), (nx, ny), 2)


class NerveLantern(BioRigidBody):
    """Glowing bioluminescent nerve organ hanging from cartilage tendons.
    Sheds bright warm light. When shot down or crashing to the ground, it bursts
    and ignites the floor with bio-plasma fire.
    """

    def __init__(
        self,
        space: pymunk.Space,
        x: float,
        y: float,
        anchor_y: Optional[float] = None,
    ):
        super().__init__(
            space=space,
            x=x,
            y=y,
            shape_type="circle",
            radius=8.0,
            mass=3.5,
            friction=0.6,
            elasticity=0.45,
            color=(255, 220, 70),
            outline_color=(190, 130, 20),
            name="Nerven-Lampion",
            health=14.0,
            destructible=True,
        )
        self.emits_light: bool = True
        self.light_radius: float = 68.0
        self.light_color: Tuple[int, int, int] = (255, 230, 85)
        self.light_intensity: float = 0.9
        self.is_hanging: bool = True
        self.ignited_ground: bool = False
        self.tendon: Optional[CartilageTendon] = None

        if anchor_y is not None and anchor_y < y:
            self.tendon = CartilageTendon(space, x, anchor_y, self)

    def on_tendon_severed(self) -> None:
        """Triggered when the suspended tendon is cut."""
        self.is_hanging = False

    def on_break(self, grid, physics_world) -> None:
        """Burst into bio-plasma fire that ignites the floor."""
        self._ignite_floor(grid, physics_world)

    def _ignite_floor(self, grid, physics_world) -> None:
        """Set floor and surroundings ablaze with fire pixels and explosion shockwave."""
        if self.ignited_ground:
            return
        self.ignited_ground = True

        ix = int(round(self.x))
        iy = int(round(self.y))

        # Detonate fiery shockwave
        create_explosion(
            grid,
            ix,
            iy,
            radius=16,
            power=30.0,
            spawn_fire=True,
            physics_world=physics_world,
        )

        # Blanket surface in persistent fire pixels
        for dy in range(-3, 4):
            for dx in range(-6, 7):
                tx = ix + dx
                ty = iy + dy
                if 1 <= tx < grid.width - 1 and 1 <= ty < grid.height - 1:
                    if grid.is_empty(tx, ty):
                        # Place fire if ground beneath or adjacent is solid/flammable
                        if grid.is_solid(tx, ty + 1) or (
                            grid.grid[ty + 1, tx] in (MAT_TISSUE, MAT_BILE, MAT_BIOGAS)
                        ):
                            grid.set_pixel(tx, ty, MAT_FIRE)
                            grid.life[ty, tx] = random.randint(40, 100)

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        """Draw luminous organic lantern with pulsating bioluminescent membrane."""
        super().draw(surface, cam_x, cam_y)
        if not self.alive:
            return

        sx = int(round(self.x - cam_x))
        sy = int(round(self.y - cam_y))

        # Core nerve nodes
        pygame.draw.circle(surface, (255, 255, 200), (sx, sy), 4)
        # Top anchor cartilage cap
        pygame.draw.circle(surface, (160, 130, 110), (sx, sy - 6), 3)


class SwingingMeatChunk(BioRigidBody):
    """Heavy mass of muscular bio-tissue hanging from a ceiling tendon.
    Swings pendulum-style. When dropped, it crushes enemies underneath
    and splatters into blood and tissue when destroyed.
    """

    def __init__(
        self,
        space: pymunk.Space,
        x: float,
        y: float,
        anchor_y: Optional[float] = None,
    ):
        super().__init__(
            space=space,
            x=x,
            y=y,
            shape_type="box",
            width=16.0,
            height=20.0,
            mass=32.0,
            friction=0.7,
            elasticity=0.2,
            color=(165, 45, 45),
            outline_color=(90, 20, 25),
            name="Fleischklumpen",
            health=140.0,
            destructible=True,
        )
        self.is_hanging: bool = True
        self.tendon: Optional[CartilageTendon] = None

        if anchor_y is not None and anchor_y < y:
            self.tendon = CartilageTendon(space, x, anchor_y, self)

    def on_tendon_severed(self) -> None:
        self.is_hanging = False

    def on_break(self, grid, physics_world) -> None:
        """Splatters into muscle tissue chunks and blood."""
        ix = int(round(self.x))
        iy = int(round(self.y))
        grid.spray_circle(ix, iy, radius=10, mat=MAT_BLOOD, density=0.85)
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                if dx * dx + dy * dy <= 9:
                    tx = ix + dx
                    ty = iy + dy
                    if (
                        1 <= tx < grid.width - 1
                        and 1 <= ty < grid.height - 1
                        and grid.is_empty(tx, ty)
                    ):
                        grid.set_pixel(tx, ty, MAT_TISSUE)

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        super().draw(surface, cam_x, cam_y)
        if not self.alive:
            return

        sx = int(round(self.x - cam_x))
        sy = int(round(self.y - cam_y))
        # Top bone hook
        pygame.draw.arc(
            surface,
            (210, 200, 185),
            pygame.Rect(sx - 4, sy - 14, 8, 8),
            0,
            math.pi,
            2,
        )
        # Fibrous muscle striations
        pygame.draw.line(surface, (190, 70, 70), (sx - 4, sy - 4), (sx + 4, sy + 4), 1)
        pygame.draw.line(surface, (130, 25, 25), (sx - 4, sy + 2), (sx + 3, sy - 5), 1)


class TentacleSegment(BioRigidBody):
    """An individual segment of a ceiling-hanging tentacle."""

    def __init__(
        self,
        space: pymunk.Space,
        x: float,
        y: float,
        radius: float,
        index: int,
        parent_tentacle: "CeilingTentacle",
    ):
        super().__init__(
            space=space,
            x=x,
            y=y,
            shape_type="circle",
            radius=radius,
            mass=2.0 + radius * 0.5,
            friction=0.8,
            elasticity=0.1,
            color=(115, 35, 90),
            outline_color=(60, 15, 45),
            name="Decken-Tentakel",
            health=25.0,
            destructible=True,
        )
        self.index = index
        self.parent_tentacle = parent_tentacle

    def on_break(self, grid, physics_world) -> None:
        """Severing this segment detaches lower segments and sprays blood."""
        ix = int(round(self.x))
        iy = int(round(self.y))
        grid.spray_circle(ix, iy, radius=6, mat=MAT_BLOOD, density=0.7)
        self.parent_tentacle.on_segment_destroyed(self.index)


class CeilingTentacle:
    """Multi-jointed living organic tentacle hanging from the cavern ceiling.
    Writhes dynamically with muscle torques and lashes out at approaching prey.
    Can be severed by shooting intermediate segments.
    """

    def __init__(
        self,
        physics_world,
        anchor_x: float,
        anchor_y: float,
        num_segments: int = 5,
        segment_length: float = 7.0,
    ):
        self.world = physics_world
        self.anchor_x = anchor_x
        self.anchor_y = anchor_y
        self.num_segments = num_segments
        self.segments: List[TentacleSegment] = []
        self.joints: List[pymunk.Constraint] = []
        self.springs: List[pymunk.Constraint] = []
        self.phase: float = random.uniform(0.0, math.pi * 2)
        self.alive: bool = True
        self.attack_cooldown: float = 0.0

        # Build segments from ceiling anchor downwards
        prev_body = self.world.space.static_body
        cur_y = anchor_y

        for i in range(num_segments):
            cur_y += segment_length
            # Segments taper towards the tip
            radius = max(3.5, 6.5 - i * 0.7)
            seg = TentacleSegment(self.world.space, anchor_x, cur_y, radius, i, self)
            self.segments.append(seg)
            self.world.add_body(seg)

            # PivotJoint connecting prev to current
            joint_pt = (anchor_x, cur_y - segment_length * 0.5)
            if i == 0:
                joint = pymunk.PivotJoint(prev_body, seg.body, (anchor_x, anchor_y))
            else:
                joint = pymunk.PivotJoint(prev_body, seg.body, joint_pt)
            self.world.space.add(joint)
            self.joints.append(joint)

            # Muscle spring giving flexible structural stiffness
            if i > 0:
                spring = pymunk.DampedRotarySpring(
                    prev_body, seg.body, rest_angle=0.0, stiffness=1400.0, damping=45.0
                )
                self.world.space.add(spring)
                self.springs.append(spring)

            prev_body = seg.body

    def on_segment_destroyed(self, seg_index: int) -> None:
        """When segment at seg_index breaks, break joints holding lower segments."""
        for idx in range(seg_index, len(self.joints)):
            j = self.joints[idx]
            if j in self.world.space.constraints:
                self.world.space.remove(j)
        for idx in range(max(0, seg_index - 1), len(self.springs)):
            s = self.springs[idx]
            if s in self.world.space.constraints:
                self.world.space.remove(s)

    def update(
        self,
        dt: float,
        player: Optional[Any] = None,
        enemies: Optional[List[Any]] = None,
    ) -> None:
        """Apply living sinusoidal undulating muscle forces and attack prey."""
        if not self.alive:
            return

        self.phase += dt * 3.2
        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt

        # Alive segments
        alive_segs = [s for s in self.segments if s.alive]
        if not alive_segs:
            self.alive = False
            return

        tip = alive_segs[-1]

        # Prey detection
        prey = None
        min_dist = 40.0
        if player and getattr(player, "alive", False):
            d = math.hypot(player.center_x - tip.x, player.center_y - tip.y)
            if d < min_dist:
                min_dist = d
                prey = player

        if enemies:
            for e in enemies:
                if getattr(e, "alive", False):
                    d = math.hypot(e.center_x - tip.x, e.center_y - tip.y)
                    if d < min_dist:
                        min_dist = d
                        prey = e

        # Undulation torques
        for i, seg in enumerate(alive_segs):
            # Base sinusoidal writhing
            wiggle = math.sin(self.phase + i * 0.85) * (180.0 + i * 80.0)
            seg.body.apply_force_at_local_point(pymunk.Vec2d(wiggle, 0.0), (0, 0))

            if prey:
                # Lash out towards prey
                p_dx = prey.center_x - seg.x
                p_dy = prey.center_y - seg.y
                p_dist = max(1.0, math.hypot(p_dx, p_dy))
                reach_force = 450.0
                seg.body.apply_force_at_world_point(
                    pymunk.Vec2d((p_dx / p_dist) * reach_force, (p_dy / p_dist) * reach_force),
                    seg.body.position,
                )

        # Contact damage with tip
        if prey and min_dist < (tip.radius + 10.0) and self.attack_cooldown <= 0:
            prey.take_damage(10.0, "ACID")
            self.attack_cooldown = 0.8
            # Whipping reaction force
            tip.body.apply_impulse_at_world_point(pymunk.Vec2d(0, -60.0), tip.body.position)

    def draw(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        """Render connected organic tentacle with suction cups."""
        alive_segs = [s for s in self.segments if s.alive]
        if not alive_segs:
            return

        # Draw sinew connections between segments
        pts = [(int(self.anchor_x - cam_x), int(self.anchor_y - cam_y))]
        for s in alive_segs:
            pts.append((int(round(s.x - cam_x)), int(round(s.y - cam_y))))

        if len(pts) >= 2:
            pygame.draw.lines(surface, (90, 25, 70), False, pts, 4)
            pygame.draw.lines(surface, (140, 45, 110), False, pts, 2)

        # Suction cup nubs along nodes
        for i, s in enumerate(alive_segs):
            sx = int(round(s.x - cam_x))
            sy = int(round(s.y - cam_y))
            # Side suction cups
            pygame.draw.circle(surface, (170, 70, 130), (sx - 4, sy), 2)
            pygame.draw.circle(surface, (170, 70, 130), (sx + 4, sy), 2)

        # Stinger / barb on tip
        if alive_segs:
            tip = alive_segs[-1]
            tx = int(round(tip.x - cam_x))
            ty = int(round(tip.y - cam_y))
            pygame.draw.circle(surface, (230, 80, 160), (tx, ty + 2), 3)
