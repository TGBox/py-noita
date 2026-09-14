"""Procedural Inverse Kinematics (IK), Tentacle Physics & Amoeboid Deformation.

Features:
- Analytical 2-Segment IK Solver for articulated limbs (knees / spider legs)
- Multi-segment FABRIK IK Solver for flexible organic tentacles
- Procedural gripping and crawling tentacles with terrain adhesion
- Walking arthropod / beetle / spider leg gait controller
- Organic amoeboid squeeze deformation for narrow cavern crevices
"""

import math
from typing import List, Optional, Tuple
import pygame
import numpy as np

from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import PROP_STATE, STATE_SOLID


def solve_2segment_ik(
    r_x: float,
    r_y: float,
    t_x: float,
    t_y: float,
    l1: float,
    l2: float,
    bend_sign: float = 1.0,
) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """Analytically solve 2-segment Inverse Kinematics (Root -> Joint -> Tip).
    Returns ((joint_x, joint_y), (tip_x, tip_y)).
    """
    dx = t_x - r_x
    dy = t_y - r_y
    d = math.hypot(dx, dy)
    # Prevent numerical breakdown when target is unreachable or at root
    d = max(0.001, min(d, l1 + l2 - 0.001))

    # Law of Cosines for knee joint angle
    cos_q2 = (d * d - l1 * l1 - l2 * l2) / (2.0 * l1 * l2)
    cos_q2 = max(-1.0, min(1.0, cos_q2))
    q2 = bend_sign * math.acos(cos_q2)

    # Base angle towards target
    base_angle = math.atan2(dy, dx)
    cos_q1 = (l1 * l1 + d * d - l2 * l2) / (2.0 * l1 * d)
    cos_q1 = max(-1.0, min(1.0, cos_q1))
    q1 = base_angle - bend_sign * math.acos(cos_q1)

    j_x = r_x + math.cos(q1) * l1
    j_y = r_y + math.sin(q1) * l1

    # End effector reached position
    tip_x = j_x + math.cos(q1 + q2) * l2
    tip_y = j_y + math.sin(q1 + q2) * l2
    return ((j_x, j_y), (tip_x, tip_y))


def solve_chain_fabrik(
    points: List[Tuple[float, float]],
    lengths: List[float],
    target_x: float,
    target_y: float,
    max_iters: int = 4,
    tolerance: float = 0.5,
) -> List[Tuple[float, float]]:
    """Solve multi-segment chain IK using Forward And Backward Reaching Inverse Kinematics (FABRIK)."""
    total_len = sum(lengths)
    r_x, r_y = points[0]
    dist_to_target = math.hypot(target_x - r_x, target_y - r_y)

    # If target is out of reach, stretch completely in target direction
    if dist_to_target >= total_len:
        ang = math.atan2(target_y - r_y, target_x - r_x)
        cur_x, cur_y = r_x, r_y
        for i in range(len(lengths)):
            cur_x += math.cos(ang) * lengths[i]
            cur_y += math.sin(ang) * lengths[i]
            points[i + 1] = (cur_x, cur_y)
        return points

    # FABRIK alternating passes
    for _ in range(max_iters):
        # Backward pass (from tip to root)
        points[-1] = (target_x, target_y)
        for i in range(len(lengths) - 1, -1, -1):
            p_next = points[i + 1]
            p_cur = points[i]
            dx = p_cur[0] - p_next[0]
            dy = p_cur[1] - p_next[1]
            d = max(0.0001, math.hypot(dx, dy))
            ratio = lengths[i] / d
            points[i] = (p_next[0] + dx * ratio, p_next[1] + dy * ratio)

        # Forward pass (from root to tip)
        points[0] = (r_x, r_y)
        for i in range(len(lengths)):
            p_cur = points[i]
            p_next = points[i + 1]
            dx = p_next[0] - p_cur[0]
            dy = p_next[1] - p_cur[1]
            d = max(0.0001, math.hypot(dx, dy))
            ratio = lengths[i] / d
            points[i + 1] = (p_cur[0] + dx * ratio, p_cur[1] + dy * ratio)

        tip_dist = math.hypot(points[-1][0] - target_x, points[-1][1] - target_y)
        if tip_dist <= tolerance:
            break

    return points


class ProceduralTentacle:
    """Organic parasite tentacle that clings to nearby walls and crawls dynamically."""

    def __init__(
        self,
        rel_root_x: float,
        rel_root_y: float,
        preferred_angle: float,
        segment_lengths: Optional[List[float]] = None,
    ):
        self.rel_root_x = rel_root_x
        self.rel_root_y = rel_root_y
        self.preferred_angle = preferred_angle
        self.segment_lengths = segment_lengths if segment_lengths else [5.0, 5.0, 5.0, 4.0]
        self.total_reach = sum(self.segment_lengths)

        # Node positions
        self.nodes: List[Tuple[float, float]] = [(0.0, 0.0) for _ in range(len(self.segment_lengths) + 1)]

        # Wall gripping / anchor state
        self.anchored: bool = False
        self.anchor_x: float = 0.0
        self.anchor_y: float = 0.0
        self.step_timer: float = 0.0
        self.anim_phase: float = np.random.uniform(0.0, math.pi * 2)

    def update(
        self,
        entity_center_x: float,
        entity_center_y: float,
        grid: SimulationGrid,
        dt: float,
        vx: float,
        vy: float,
        facing_dir: float = 1.0,
    ) -> None:
        """Update tentacle physics, search for wall grip, and solve IK."""
        self.anim_phase += dt * 3.0

        root_x = entity_center_x + self.rel_root_x * facing_dir
        root_y = entity_center_y + self.rel_root_y
        self.nodes[0] = (root_x, root_y)

        # If currently anchored to terrain, check if anchor is still valid
        if self.anchored:
            dist = math.hypot(self.anchor_x - root_x, self.anchor_y - root_y)
            # Detach if entity moved too far away or terrain destroyed
            ix, iy = int(self.anchor_x), int(self.anchor_y)
            terrain_destroyed = not (0 <= ix < grid.width and 0 <= iy < grid.height and grid.is_solid(ix, iy))
            if dist > self.total_reach * 0.95 or terrain_destroyed:
                self.anchored = False

        # If not anchored, look for solid terrain in preferred direction to grip
        if not self.anchored:
            self.step_timer += dt
            # Raycast in small cone around preferred angle
            found_anchor = False
            base_angle = self.preferred_angle if facing_dir > 0 else (math.pi - self.preferred_angle)

            # Check slightly ahead in motion direction
            search_angle = base_angle + (0.3 if vx > 0.1 else (-0.3 if vx < -0.1 else 0.0))

            for r in range(4, int(self.total_reach * 0.9), 2):
                scan_x = int(root_x + math.cos(search_angle) * r)
                scan_y = int(root_y + math.sin(search_angle) * r)
                if 0 <= scan_x < grid.width and 0 <= scan_y < grid.height:
                    if grid.is_solid(scan_x, scan_y):
                        self.anchor_x = float(scan_x)
                        self.anchor_y = float(scan_y)
                        self.anchored = True
                        found_anchor = True
                        break

            if not found_anchor:
                # Undulate freely in fluid/air drag
                idle_wave = math.sin(self.anim_phase) * 0.35
                cur_ang = base_angle + idle_wave - (vx * 0.1)
                target_x = root_x + math.cos(cur_ang) * (self.total_reach * 0.75)
                target_y = root_y + math.sin(cur_ang) * (self.total_reach * 0.75) - (vy * 0.2)
            else:
                target_x = self.anchor_x
                target_y = self.anchor_y
        else:
            target_x = self.anchor_x
            target_y = self.anchor_y

        # Solve FABRIK IK chain
        solve_chain_fabrik(self.nodes, self.segment_lengths, target_x, target_y)

    def draw(
        self,
        surface: pygame.Surface,
        cam_x: int,
        cam_y: int,
        base_color: Tuple[int, int, int] = (150, 25, 45),
        tip_color: Tuple[int, int, int] = (225, 60, 80),
    ) -> None:
        """Render tapered organic tentacle with suckers and joints."""
        num_segments = len(self.segment_lengths)
        for i in range(num_segments):
            p1 = self.nodes[i]
            p2 = self.nodes[i + 1]

            x1, y1 = int(p1[0] - cam_x), int(p1[1] - cam_y)
            x2, y2 = int(p2[0] - cam_x), int(p2[1] - cam_y)

            # Taper thickness from 3px down to 1px
            width = max(1, 3 - i // 2)
            # Smooth color transition from root to tip
            t = i / max(1, num_segments)
            col = (
                int(base_color[0] * (1 - t) + tip_color[0] * t),
                int(base_color[1] * (1 - t) + tip_color[1] * t),
                int(base_color[2] * (1 - t) + tip_color[2] * t),
            )
            pygame.draw.line(surface, col, (x1, y1), (x2, y2), width)

        # Draw sucker / anchor tip
        tip = self.nodes[-1]
        tx, ty = int(tip[0] - cam_x), int(tip[1] - cam_y)
        pygame.draw.circle(surface, tip_color, (tx, ty), 2 if self.anchored else 1)


class ProceduralLeg:
    """2-Segment IK walking leg for scuttling chitin beetles and parasite spiders."""

    def __init__(
        self,
        coxa_offset_x: float,
        coxa_offset_y: float,
        l1: float = 6.0,
        l2: float = 7.0,
        gait_phase: float = 0.0,
        bend_sign: float = -1.0,
    ):
        self.coxa_offset_x = coxa_offset_x
        self.coxa_offset_y = coxa_offset_y
        self.l1 = l1
        self.l2 = l2
        self.gait_phase = gait_phase
        self.bend_sign = bend_sign

        self.foot_x: float = 0.0
        self.foot_y: float = 0.0
        self.step_start_x: float = 0.0
        self.step_start_y: float = 0.0
        self.step_target_x: float = 0.0
        self.step_target_y: float = 0.0
        self.is_stepping: bool = False
        self.step_progress: float = 1.0

    def update(
        self,
        body_x: float,
        body_y: float,
        facing_dir: float,
        grid: SimulationGrid,
        dt: float,
        vx: float,
    ) -> None:
        """Update leg stepping cycle and stick to ground terrain."""
        root_x = body_x + self.coxa_offset_x * facing_dir
        root_y = body_y + self.coxa_offset_y

        # Initialize foot on first tick
        if self.foot_x == 0.0 and self.foot_y == 0.0:
            self.foot_x = root_x + (self.coxa_offset_x * 0.8 * facing_dir)
            self.foot_y = root_y + self.l1 + self.l2 - 2.0

        # Desired neutral ground rest position
        ideal_target_x = root_x + (self.coxa_offset_x * 0.7 * facing_dir) + (vx * 4.0)

        # Raycast down from above ground to find solid footing
        ground_y = root_y + self.l1 + self.l2 - 2.0
        for test_y in range(int(root_y - 2), int(root_y + self.l1 + self.l2 + 6)):
            gx, gy = int(ideal_target_x), int(test_y)
            if 0 <= gx < grid.width and 0 <= gy < grid.height:
                if grid.is_solid(gx, gy):
                    ground_y = float(test_y - 1)
                    break
        ideal_target_y = ground_y

        # Check if foot is stretched too far
        dist = math.hypot(self.foot_x - ideal_target_x, self.foot_y - ideal_target_y)
        max_stretch = (self.l1 + self.l2) * 0.7

        if not self.is_stepping and dist > max_stretch:
            # Start step
            self.is_stepping = True
            self.step_progress = 0.0
            self.step_start_x = self.foot_x
            self.step_start_y = self.foot_y
            self.step_target_x = ideal_target_x
            self.step_target_y = ideal_target_y

        if self.is_stepping:
            step_speed = 8.0 + abs(vx) * 3.0
            self.step_progress = min(1.0, self.step_progress + dt * step_speed)
            t = self.step_progress
            # Horizontal smooth interpolation
            self.foot_x = self.step_start_x + (self.step_target_x - self.step_start_x) * t
            # Parabolic lift arc
            lift = math.sin(t * math.pi) * 3.5
            self.foot_y = self.step_start_y + (self.step_target_y - self.step_start_y) * t - lift

            if self.step_progress >= 1.0:
                self.is_stepping = False

    def draw(
        self,
        surface: pygame.Surface,
        body_x: float,
        body_y: float,
        facing_dir: float,
        cam_x: int,
        cam_y: int,
        chitin_color: Tuple[int, int, int] = (65, 52, 75),
    ) -> None:
        """Render 2-segment articulated chitin leg with knee and claw."""
        root_x = body_x + self.coxa_offset_x * facing_dir
        root_y = body_y + self.coxa_offset_y

        joint, tip = solve_2segment_ik(
            root_x, root_y, self.foot_x, self.foot_y,
            self.l1, self.l2, bend_sign=self.bend_sign * (1.0 if facing_dir > 0 else -1.0)
        )

        rx, ry = int(root_x - cam_x), int(root_y - cam_y)
        jx, jy = int(joint[0] - cam_x), int(joint[1] - cam_y)
        fx, fy = int(tip[0] - cam_x), int(tip[1] - cam_y)

        # Upper leg (Femur)
        pygame.draw.line(surface, chitin_color, (rx, ry), (jx, jy), 2)
        # Lower leg (Tibia)
        pygame.draw.line(surface, chitin_color, (jx, jy), (fx, fy), 1)
        # Joint knob
        pygame.draw.circle(surface, (95, 80, 110), (jx, jy), 1)
        # Sharp foot claw
        pygame.draw.circle(surface, (35, 28, 42), (fx, fy), 1)


class AmoeboidDeformation:
    """Dynamic cellular squish & stretch deformation for crawling through tight crevices."""

    def __init__(self, base_radius: float = 7.0, num_vertices: int = 14):
        self.base_radius = base_radius
        self.num_vertices = num_vertices
        self.squeeze_x: float = 1.0
        self.squeeze_y: float = 1.0
        self.phase: float = np.random.uniform(0, math.pi * 2)

    def update(
        self,
        center_x: float,
        center_y: float,
        grid: SimulationGrid,
        dt: float,
        vx: float,
        vy: float,
    ) -> None:
        """Calculate spatial restriction in cavern and adjust amoeba squeeze factor."""
        self.phase += dt * 2.5

        # Raycast horizontal clearance across 3 vertical slices for robust gap detection
        max_scan = int(self.base_radius * 2)
        left_clear = max_scan
        right_clear = max_scan

        for offset_y in (-2, 0, 2):
            test_cy = int(center_y + offset_y)
            if not (0 <= test_cy < grid.height):
                continue
            lc = 0
            for dx in range(1, max_scan):
                gx = int(center_x - dx)
                if 0 <= gx < grid.width and grid.is_solid(gx, test_cy):
                    break
                lc += 1
            left_clear = min(left_clear, lc)

            rc = 0
            for dx in range(1, max_scan):
                gx = int(center_x + dx)
                if 0 <= gx < grid.width and grid.is_solid(gx, test_cy):
                    break
                rc += 1
            right_clear = min(right_clear, rc)

        horiz_span = left_clear + right_clear
        target_squeeze_x = 1.0
        target_squeeze_y = 1.0

        # Narrow vertical shaft: squish horizontal, elongate vertical
        if horiz_span < self.base_radius * 1.8:
            target_squeeze_x = max(0.4, horiz_span / (self.base_radius * 2.0))
            target_squeeze_y = 1.0 / target_squeeze_x
        elif abs(vy) > 0.8:
            # Elongate in fall/leap direction
            target_squeeze_y = 1.25
            target_squeeze_x = 0.8
        elif abs(vx) > 0.8:
            # Flatten low and stretch forward while scurrying
            target_squeeze_x = 1.3
            target_squeeze_y = 0.75

        # Smooth spring dampening
        self.squeeze_x += (target_squeeze_x - self.squeeze_x) * 0.35
        self.squeeze_y += (target_squeeze_y - self.squeeze_y) * 0.35

    def get_contour_points(
        self,
        center_x: float,
        center_y: float,
        cam_x: int,
        cam_y: int,
    ) -> List[Tuple[int, int]]:
        """Generate animated smooth organic perimeter vertices with harmonic pseudopodia."""
        points: List[Tuple[int, int]] = []
        for i in range(self.num_vertices):
            angle = (i / self.num_vertices) * math.pi * 2.0
            # Harmonic pseudopodia wave oscillation
            wave = (
                math.sin(angle * 3.0 + self.phase) * 1.2
                + math.cos(angle * 5.0 - self.phase * 1.3) * 0.8
            )
            r = max(2.0, self.base_radius + wave)

            # Apply cavern squeeze factors
            px = center_x + math.cos(angle) * r * self.squeeze_x - cam_x
            py = center_y + math.sin(angle) * r * self.squeeze_y - cam_y
            points.append((int(px), int(py)))
        return points
