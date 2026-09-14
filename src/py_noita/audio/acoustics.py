"""Dynamic Environmental Acoustics & Audio DSP Filters.

Features:
- Liquid Submergence Low-Pass Filter (Muffling of all sounds and music when submerged in blood/acid/water/slime)
- Dynamic Cave Reverb & Echo calculated from surrounding hollow cavern airspace
- Visceral low-HP heartbeat pulse (<25% HP) with sidechain ducking of background music and SFX
- Numba-accelerated 1-pole IIR lowpass filter and multi-tap comb delay line
"""

import math
from typing import Optional, Tuple
import numpy as np
from numba import njit
import pygame

from py_noita.config import AUDIO_SAMPLE_RATE
from py_noita.simulation.materials import (
    MAT_AIR,
    MAT_BLOOD,
    MAT_ACID,
    MAT_BILE,
    MAT_LYMPH,
    MAT_PUS,
    MAT_MUTAGEN,
    PROP_STATE,
    STATE_EMPTY,
    STATE_GAS,
)

CHANNEL_HEARTBEAT = 4

LIQUID_MATERIALS = (MAT_BLOOD, MAT_ACID, MAT_BILE, MAT_LYMPH, MAT_PUS, MAT_MUTAGEN)


@njit(fastmath=True)
def iir_lowpass_filter_1d(samples: np.ndarray, alpha: float) -> np.ndarray:
    """Fast single-pole IIR low-pass filter: y[n] = y[n-1] + alpha * (x[n] - y[n-1])."""
    n = len(samples)
    out = np.empty(n, dtype=np.float32)
    if n == 0:
        return out
    out[0] = samples[0]
    for i in range(1, n):
        out[i] = out[i - 1] + alpha * (samples[i] - out[i - 1])
    return out


@njit(fastmath=True)
def comb_reverb_filter_1d(samples: np.ndarray, delay_samples: int, feedback: float, wet: float) -> np.ndarray:
    """Fast multi-tap delay line producing smooth cavern reverberation tails."""
    n = len(samples)
    if n == 0 or delay_samples <= 0:
        return samples.copy()

    delayed_buf = np.empty(n, dtype=np.float32)
    for i in range(n):
        d_val = delayed_buf[i - delay_samples] if i >= delay_samples else 0.0
        delayed_buf[i] = samples[i] + d_val * feedback

    # Dry/wet mix
    res = np.empty(n, dtype=np.float32)
    dry = 1.0 - wet
    for i in range(n):
        res[i] = dry * samples[i] + wet * delayed_buf[i]
    return res


def synth_heartbeat_thump(pitch: float = 48.0, duration: float = 0.22, sr: int = AUDIO_SAMPLE_RATE) -> pygame.mixer.Sound:
    """Synthesize a deep, fleshy sub-bass organic heartbeat thump."""
    num_samples = int(sr * duration)
    t = np.linspace(0, duration, num_samples, endpoint=False)

    # Pitch glide downwards for visceral thump
    freq = pitch * np.exp(-t * 8.0)
    sine = np.sin(2.0 * np.pi * freq * t)
    sub = np.sin(2.0 * np.pi * (freq * 0.5) * t) * 0.4
    harmonic = np.sin(2.0 * np.pi * (freq * 2.0) * t) * 0.25

    # Organic attack-decay envelope
    envelope = np.sin(np.pi * np.clip(t / duration, 0.0, 1.0) ** 0.5) * np.exp(-t * 12.0)
    raw = (sine + sub + harmonic) * envelope

    # Gentle saturation / distortion
    saturated = np.tanh(raw * 2.2) * 0.85

    # Convert to 16-bit stereo PCM
    clipped = np.clip(saturated, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype(np.int16)
    stereo_pcm = np.column_stack((pcm, pcm))
    return pygame.mixer.Sound(buffer=stereo_pcm.tobytes())


class AcousticsEngine:
    """Processes environmental acoustics: submergence lowpass, cavern reverb, and low-HP heartbeat."""

    def __init__(self, sample_rate: int = AUDIO_SAMPLE_RATE):
        self.sample_rate: int = sample_rate
        self.submerged_factor: float = 0.0  # 0.0 (dry) to 1.0 (fully submerged)
        self.cavern_reverb_wet: float = 0.0  # 0.0 (tight tunnel) to 1.0 (vast cavern)
        self.heartbeat_ducking: float = 1.0  # 1.0 (full volume) down to 0.3 (ducked on heart thump)

        # Heartbeat state
        self.heartbeat_active: bool = False
        self.heartbeat_timer: float = 0.0
        self.heartbeat_thump1: Optional[pygame.mixer.Sound] = None
        self.heartbeat_thump2: Optional[pygame.mixer.Sound] = None
        self.channel: Optional[pygame.mixer.Channel] = None
        self.initialized: bool = False

        self._init_audio()

    def _init_audio(self) -> None:
        """Initialize mixer channel and pre-render heartbeat sounds."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=self.sample_rate, size=-16, channels=2, buffer=512)
            # Ensure channel 4 is reserved
            self.channel = pygame.mixer.Channel(CHANNEL_HEARTBEAT)
            self.heartbeat_thump1 = synth_heartbeat_thump(pitch=52.0, duration=0.22, sr=self.sample_rate)
            self.heartbeat_thump2 = synth_heartbeat_thump(pitch=68.0, duration=0.18, sr=self.sample_rate)
            self.initialized = True
        except Exception:
            self.initialized = False

    def update(self, dt: float, player: Optional[object], grid: Optional[object]) -> None:
        """Update environmental acoustic properties and heartbeat pulse."""
        self._update_submergence(dt, player, grid)
        self._update_cavern_reverb(dt, player, grid)
        self._update_heartbeat(dt, player)

    def _update_submergence(self, dt: float, player: Optional[object], grid: Optional[object]) -> None:
        """Determine if the player is submerged in liquid and update muffling factor."""
        target_submerged = 0.0
        if player is not None and grid is not None and getattr(player, "alive", True):
            px = int(player.center_x)
            py = int(player.center_y)
            top_y = int(player.y + 4)
            bottom_y = int(player.y + player.height - 4)

            # Sample top, center, and bottom of player sprite
            submerged_samples = 0
            for sample_y in (top_y, py, bottom_y):
                if 0 <= px < grid.width and 0 <= sample_y < grid.height:
                    mat = grid.get_material(px, sample_y)
                    if mat in LIQUID_MATERIALS:
                        submerged_samples += 1

            if submerged_samples >= 2:
                target_submerged = 1.0  # Fully submerged (muffling active)
            elif submerged_samples == 1:
                target_submerged = 0.5  # Partially submerged

        # Smooth interpolation to prevent abrupt audio pops
        self.submerged_factor += (target_submerged - self.submerged_factor) * min(1.0, dt * 5.0)

    def _update_cavern_reverb(self, dt: float, player: Optional[object], grid: Optional[object]) -> None:
        """Calculate cavern airspace size around player to determine dynamic reverb amount."""
        target_wet = 0.0
        if player is not None and grid is not None:
            px = int(player.center_x)
            py = int(player.center_y)

            # Sample 16 points in a grid around player (-45 to +45 pixels)
            open_count = 0
            valid_samples = 0
            radius = 45
            for dx in (-radius, -radius // 3, radius // 3, radius):
                for dy in (-radius, -radius // 3, radius // 3, radius):
                    sx = px + dx
                    sy = py + dy
                    if 0 <= sx < grid.width and 0 <= sy < grid.height:
                        valid_samples += 1
                        mat = grid.get_pixel(sx, sy)
                        if mat == MAT_AIR or PROP_STATE[mat] in (STATE_EMPTY, STATE_GAS):
                            open_count += 1

            ratio = open_count / float(max(1, valid_samples))
            # If mostly open airspace (>50%), reverb approaches 0.7 - 1.0
            target_wet = max(0.0, min(1.0, (ratio - 0.15) / 0.75))

        self.cavern_reverb_wet += (target_wet - self.cavern_reverb_wet) * min(1.0, dt * 4.0)

    def _update_heartbeat(self, dt: float, player: Optional[object]) -> None:
        """Process visceral low-HP heartbeat loop and sidechain audio ducking."""
        if player is None or not getattr(player, "alive", True):
            self.heartbeat_active = False
            self.heartbeat_ducking += (1.0 - self.heartbeat_ducking) * min(1.0, dt * 5.0)
            return

        hp_ratio = player.hp / max(1.0, player.max_hp)
        if hp_ratio < 0.25:
            self.heartbeat_active = True
            # Pulse faster as HP gets critically low (90 BPM at 25% down to 145 BPM at 2%)
            bpm = 90.0 + (0.25 - max(0.0, hp_ratio)) / 0.25 * 55.0
            period = 60.0 / bpm

            prev_timer = self.heartbeat_timer
            self.heartbeat_timer = (self.heartbeat_timer + dt) % period

            # First thump (Lub) at beginning of cycle
            if prev_timer > self.heartbeat_timer or (prev_timer < 0.02 and self.heartbeat_timer >= 0.02):
                if self.channel and self.heartbeat_thump1:
                    vol = 0.85 + (0.25 - hp_ratio) * 0.6
                    self.channel.set_volume(min(1.0, vol))
                    self.channel.play(self.heartbeat_thump1)
                self.heartbeat_ducking = 0.32  # Duck music/SFX

            # Second thump (Dub) at ~28% through cycle
            dub_time = period * 0.28
            if prev_timer < dub_time <= self.heartbeat_timer:
                if self.channel and self.heartbeat_thump2:
                    vol = 0.75 + (0.25 - hp_ratio) * 0.6
                    self.channel.set_volume(min(1.0, vol))
                    self.channel.play(self.heartbeat_thump2)
                self.heartbeat_ducking = 0.38  # Secondary duck

            # Smoothly recover ducking between thumps
            self.heartbeat_ducking += (1.0 - self.heartbeat_ducking) * min(1.0, dt * 4.2)
        else:
            self.heartbeat_active = False
            self.heartbeat_ducking += (1.0 - self.heartbeat_ducking) * min(1.0, dt * 6.0)

    def apply_lowpass_to_buffer(self, samples_1d: np.ndarray, cutoff_hz: float = 650.0) -> np.ndarray:
        """Filter an audio buffer with the lowpass filter based on submergence."""
        if self.submerged_factor <= 0.01:
            return samples_1d

        # Calculate filter alpha for cutoff
        dt = 1.0 / self.sample_rate
        rc = 1.0 / (2.0 * math.pi * cutoff_hz)
        alpha = float(dt / (rc + dt))

        # Blend dry and muffled according to submergence factor
        filtered = iir_lowpass_filter_1d(samples_1d, alpha)
        return (1.0 - self.submerged_factor) * samples_1d + self.submerged_factor * filtered

    def apply_reverb_to_buffer(self, samples_1d: np.ndarray, delay_ms: float = 65.0, feedback: float = 0.45) -> np.ndarray:
        """Apply dynamic cavern echo / reverb to an audio buffer."""
        if self.cavern_reverb_wet <= 0.01:
            return samples_1d

        delay_samples = int(self.sample_rate * (delay_ms / 1000.0))
        wet = self.cavern_reverb_wet * 0.55
        return comb_reverb_filter_1d(samples_1d, delay_samples, feedback, wet)

    def get_music_modifiers(self) -> Tuple[float, float, float, float, float]:
        """Compute modifiers for (ambient_vol, bass_vol, drums_vol, texture_vol, master_mult).

        Returns:
            (ambient_factor, bass_factor, drums_factor, texture_factor, overall_ducking)
        """
        sub = self.submerged_factor
        rev = self.cavern_reverb_wet
        duck = self.heartbeat_ducking

        # When submerged in liquid:
        # - Drums are heavily muffled / silenced (-85%)
        # - Textures are muffled (-80%)
        # - Ambient loses high end, slightly lowered (-35%)
        # - Sub-bass is amplified (+30%) for deep underwater pressure rumble!
        drums_factor = 1.0 - 0.85 * sub
        texture_factor = (1.0 - 0.80 * sub) * (1.0 + 0.35 * rev)
        ambient_factor = (1.0 - 0.35 * sub) * (1.0 + 0.15 * rev)
        bass_factor = 1.0 + 0.30 * sub

        return (ambient_factor, bass_factor, drums_factor, texture_factor, duck)
