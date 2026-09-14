"""3D Spatial Stereo Panning & Distance Attenuation Engine.

Features:
- Equal-Power Stereo Panning Law (smooth left/right acoustic positioning based on horizontal distance)
- Exponential distance attenuation falloff with smooth threshold cutoff
- Realistic spatialization for explosions, enemy footsteps, acid sizzles, and impacts
"""

import math
from typing import Optional, Tuple
import pygame


def calculate_stereo_panning(dx: float, pan_width: float = 260.0) -> Tuple[float, float]:
    """Calculate equal-power stereo panning coefficients for a relative horizontal offset.

    Returns:
        (left_gain, right_gain) satisfying left^2 + right^2 = 1.0
    """
    pan = max(-1.0, min(1.0, dx / pan_width))
    # Map [-1.0, 1.0] -> [0.0, pi/2]
    angle = (pan + 1.0) * (math.pi / 4.0)
    left = math.cos(angle)
    right = math.sin(angle)
    return left, right


def calculate_distance_attenuation(
    distance: float,
    min_distance: float = 40.0,
    max_distance: float = 650.0,
    falloff_power: float = 1.7,
) -> float:
    """Calculate exponential distance attenuation curve with smooth fadeout at max_distance.

    Returns:
        Gain factor between 0.0 (inaudible/beyond range) and 1.0 (full volume within min_distance)
    """
    if distance <= min_distance:
        return 1.0
    if distance >= max_distance:
        return 0.0

    normalized_d = (distance - min_distance) / (max_distance - min_distance)
    # Exponential falloff with smooth hermite window at boundaries
    exp_factor = math.exp(-normalized_d * falloff_power)
    # Window to smoothly reach 0.0 at max_distance without clicking
    window = 1.0 - normalized_d
    return max(0.0, min(1.0, exp_factor * window))


def compute_spatial_volumes(
    world_x: float,
    world_y: float,
    listener_x: float,
    listener_y: float,
    base_volume: float = 1.0,
    pan_width: float = 260.0,
    min_dist: float = 40.0,
    max_dist: float = 650.0,
) -> Tuple[float, float]:
    """Compute left and right channel volumes for a world-space sound source.

    Returns:
        (left_vol, right_vol) clamped to [0.0, 1.0]
    """
    dx = world_x - listener_x
    dy = world_y - listener_y
    dist = math.hypot(dx, dy)

    attenuation = calculate_distance_attenuation(dist, min_distance=min_dist, max_distance=max_dist)
    if attenuation <= 0.001:
        return 0.0, 0.0

    left_pan, right_pan = calculate_stereo_panning(dx, pan_width=pan_width)
    total_gain = base_volume * attenuation

    left_vol = max(0.0, min(1.0, total_gain * left_pan))
    right_vol = max(0.0, min(1.0, total_gain * right_pan))
    return left_vol, right_vol


class SpatialAudioEngine:
    """Manages playing spatialized 3D sounds with stereo panning and distance attenuation."""

    def __init__(self, pan_width: float = 260.0, min_dist: float = 40.0, max_dist: float = 650.0):
        self.pan_width: float = pan_width
        self.min_dist: float = min_dist
        self.max_dist: float = max_dist

    def play_spatial(
        self,
        sound: pygame.mixer.Sound,
        world_x: float,
        world_y: float,
        listener_x: float,
        listener_y: float,
        base_volume: float = 0.8,
        ducking: float = 1.0,
        muffle: float = 1.0,
    ) -> Optional[pygame.mixer.Channel]:
        """Play a sound with spatial panning and distance attenuation on an available channel."""
        left, right = compute_spatial_volumes(
            world_x,
            world_y,
            listener_x,
            listener_y,
            base_volume=base_volume,
            pan_width=self.pan_width,
            min_dist=self.min_dist,
            max_dist=self.max_dist,
        )

        effective_left = left * ducking * muffle
        effective_right = right * ducking * muffle

        # If too quiet in both ears, discard to save channel resources
        if effective_left <= 0.01 and effective_right <= 0.01:
            return None

        # Find an available channel outside reserved music stems (0-3) and heartbeat (4)
        channel = pygame.mixer.find_channel()
        if channel:
            channel.set_volume(effective_left, effective_right)
            channel.play(sound)
            return channel
        return None
