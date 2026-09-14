"""Multi-track, dynamically adaptive procedural bio-horror soundtrack engine.

Features:
- Multi-track stems per biome: Ambient Pad, Visceral Sub-Bass, Combat Drums, Noise Textures
- Latency-free seamless cross-fading: Combat drums trigger immediately upon enemy contact
- Tailored musical themes for all 8 Organ Biomes, the Holy Mountain (Incubation Node), and Boss Fights
- 100% procedural waveform synthesis (zero external asset dependencies)
"""

import math
from typing import Dict, Optional, Tuple
import pygame
import numpy as np

from py_noita.config import AUDIO_SAMPLE_RATE


# Biome theme constants
THEME_INCUBATION = 99
THEME_BOSS = 100

# Channel allocation for music stems
CHANNEL_AMBIENT = 0
CHANNEL_BASS = 1
CHANNEL_DRUMS = 2
CHANNEL_TEXTURE = 3


def _create_looping_sound(samples_1d: np.ndarray, duration: float, sr: int = AUDIO_SAMPLE_RATE) -> pygame.mixer.Sound:
    """Convert float samples into a clickless, perfectly looping stereo 16-bit sound."""
    num_samples = len(samples_1d)
    # Apply circular crossfade window at loop boundary to eliminate clicks
    fade_len = int(sr * 0.05)  # 50ms smooth loop transition
    window = np.ones(num_samples, dtype=np.float32)
    if fade_len > 0 and num_samples > fade_len * 2:
        ramp = np.linspace(0.0, 1.0, fade_len)
        window[:fade_len] = ramp
        window[-fade_len:] = ramp[::-1]

    clipped = np.clip(samples_1d * window, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype(np.int16)
    stereo_pcm = np.column_stack((pcm, pcm))
    return pygame.mixer.Sound(buffer=stereo_pcm.tobytes())


def synth_biome_track(
    theme_id: int,
    track_type: str,
    duration: float = 4.0,
    sr: int = AUDIO_SAMPLE_RATE,
) -> pygame.mixer.Sound:
    """Procedurally synthesize a single looping stem for a biome theme."""
    num_samples = int(sr * duration)
    t = np.linspace(0, duration, num_samples, endpoint=False)

    # Base frequencies per biome (minor, phrygian, and tritone visceral modes)
    BIOME_BASE_FREQS = {
        0: 110.0,  # Epidermis: A2 (cold, windy)
        1: 98.0,   # Vascular Muscle: G2 (throbbing pulse)
        2: 82.4,   # Acid Caverns: E2 (deep corrosive tritone)
        3: 73.4,   # Toxic Bile: D2 (murky sludge)
        4: 123.5,  # Infected Lung: B2 (breath, spores)
        5: 65.4,   # Bone Catacombs: C2 (hollow, skeletal)
        6: 146.8,  # Spine & Nerve: D3 (high-voltage bio-electricity)
        7: 55.0,   # Primordial Center: A1 (monumental abyssal drone)
        THEME_INCUBATION: 130.8,  # Incubation Node: C3 (peaceful harmonic sanctuary)
        THEME_BOSS: 61.7,         # Boss Fight: B1 (relentless, aggressive dissonance)
    }

    base_f = BIOME_BASE_FREQS.get(theme_id, 110.0)

    if track_type == "ambient":
        # Slow organic ambient pad with choir harmonics and gentle vibrato
        vibrato = np.sin(2 * np.pi * 0.4 * t) * 1.5
        chord_3rd = base_f * (1.25 if theme_id == THEME_INCUBATION else 1.20)  # Major 3rd for sanctuary, minor 3rd for horror
        chord_5th = base_f * 1.50
        octave = base_f * 2.0

        pad = (
            np.sin(2 * np.pi * (base_f + vibrato) * t) * 0.35
            + np.sin(2 * np.pi * chord_3rd * t) * 0.25
            + np.sin(2 * np.pi * chord_5th * t) * 0.20
            + np.sin(2 * np.pi * octave * t) * 0.12
        )
        # Slow atmospheric low-frequency breathing filter
        lfo = (np.sin(2 * np.pi * 0.25 * t) + 1.0) * 0.5
        samples = pad * (0.6 + 0.4 * lfo)

    elif track_type == "bass":
        # Heavy visceral sub-bass pulse synced to 120 BPM
        bpm = 140.0 if theme_id == THEME_BOSS else (90.0 if theme_id == THEME_INCUBATION else 115.0)
        beat_interval = 60.0 / bpm
        sub_carrier = np.sin(2 * np.pi * (base_f * 0.5) * t)
        # Add rich sub-harmonics
        saw_approx = 0.5 * np.sin(2 * np.pi * (base_f * 0.5) * t) + 0.25 * np.sin(2 * np.pi * base_f * t)

        # Pulse envelope on each beat
        beat_phase = (t % beat_interval) / beat_interval
        pulse_env = np.exp(-beat_phase * 4.0)
        samples = (sub_carrier * 0.7 + saw_approx * 0.3) * pulse_env * 0.65

    elif track_type == "drums":
        # Driving visceral percussion: kick pulse, bone clatter rimshot, flesh squelch
        if theme_id == THEME_INCUBATION:
            # Sanctuary has no combat drums
            samples = np.zeros(num_samples, dtype=np.float32)
        else:
            bpm = 140.0 if theme_id == THEME_BOSS else 115.0
            beat_interval = 60.0 / bpm
            samples = np.zeros(num_samples, dtype=np.float32)

            # Kick drum on quarter beats
            num_beats = int(duration / beat_interval)
            for b in range(num_beats):
                start_idx = int(b * beat_interval * sr)
                kick_len = int(sr * 0.18)
                if start_idx + kick_len <= num_samples:
                    kt = np.linspace(0, 0.18, kick_len, endpoint=False)
                    # Pitch bend down 120Hz -> 35Hz
                    k_pitch = np.linspace(130.0, 35.0, kick_len)
                    kick = np.sin(2 * np.pi * k_pitch * kt) * np.exp(-kt * 22.0)
                    samples[start_idx : start_idx + kick_len] += kick * 0.7

            # Snare / Bone clatter on off-beats
            for b in range(num_beats):
                if b % 2 == 1 or theme_id == THEME_BOSS:
                    start_idx = int((b * beat_interval + beat_interval * 0.5) * sr)
                    snare_len = int(sr * 0.12)
                    if start_idx + snare_len <= num_samples:
                        st = np.linspace(0, 0.12, snare_len, endpoint=False)
                        s_noise = np.random.uniform(-0.8, 0.8, snare_len)
                        s_tone = np.sin(2 * np.pi * 220.0 * st)
                        snare = (s_noise * 0.7 + s_tone * 0.3) * np.exp(-st * 30.0)
                        samples[start_idx : start_idx + snare_len] += snare * 0.55

    else:  # track_type == "texture"
        # Whispering bio-texture / cavern wind and bio-electrical noise
        noise = np.random.uniform(-0.5, 0.5, num_samples)
        # Resonance filter sweep
        mod = (np.sin(2 * np.pi * 0.3 * t) + 1.0) * 0.5
        # Soft ringing chime / overtone
        chime = np.sin(2 * np.pi * (base_f * 4.0) * t) * 0.15
        samples = (noise * 0.5 + chime * 0.5) * (0.3 + 0.7 * mod) * 0.35

    return _create_looping_sound(samples, duration, sr)


class AdaptiveMusicEngine:
    """Manages playback, cross-fading, and combat layers for the bio-horror soundtrack."""

    def __init__(self):
        self.initialized: bool = False
        self.current_theme: int = -1
        self.target_theme: int = 0
        self.combat_intensity: float = 0.0  # 0.0 (peaceful) to 1.0 (heavy combat)
        self.master_music_volume: float = 0.75

        # Volume state for each track
        self.vol_ambient: float = 0.8
        self.vol_bass: float = 0.7
        self.vol_drums: float = 0.0
        self.vol_texture: float = 0.5

        self.channels: Dict[str, Optional[pygame.mixer.Channel]] = {
            "ambient": None,
            "bass": None,
            "drums": None,
            "texture": None,
        }
        self.current_stems: Dict[str, pygame.mixer.Sound] = {}
        self._init_mixer()

    def _init_mixer(self) -> None:
        """Reserve and initialize dedicated audio channels."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=AUDIO_SAMPLE_RATE, size=-16, channels=2, buffer=512)
            # Reserve at least 8 channels (0-3 for music, 4+ for SFX)
            pygame.mixer.set_num_channels(16)
            self.channels["ambient"] = pygame.mixer.Channel(CHANNEL_AMBIENT)
            self.channels["bass"] = pygame.mixer.Channel(CHANNEL_BASS)
            self.channels["drums"] = pygame.mixer.Channel(CHANNEL_DRUMS)
            self.channels["texture"] = pygame.mixer.Channel(CHANNEL_TEXTURE)
            self.initialized = True
        except Exception:
            self.initialized = False

    def set_theme(self, theme_id: int) -> None:
        """Transition to a new biome or special event soundtrack."""
        if not self.initialized:
            return
        if self.current_theme == theme_id:
            return

        self.current_theme = theme_id

        # Synthesize stems for this theme
        for track in ("ambient", "bass", "drums", "texture"):
            sound = synth_biome_track(theme_id, track, duration=4.0)
            self.current_stems[track] = sound
            channel = self.channels[track]
            if channel:
                channel.play(sound, loops=-1)

        self._update_channel_volumes()

    def set_combat_intensity(self, intensity: float) -> None:
        """Set combat intensity (0.0 to 1.0) to dynamically ramp drums."""
        self.combat_intensity = max(0.0, min(1.0, intensity))

    def update(self, dt: float) -> None:
        """Smoothly interpolate track volumes based on combat and location."""
        if not self.initialized:
            return

        # Target volumes
        target_ambient = 0.8
        target_bass = 0.75 if self.combat_intensity > 0.3 else 0.5
        target_drums = self.combat_intensity  # Instant drums when in combat
        target_texture = 0.4 if self.combat_intensity > 0.5 else 0.6

        # Fast attack (0.1s) into combat, slower decay (2.0s) out of combat
        drum_fade_speed = 6.0 if target_drums > self.vol_drums else 1.2

        self.vol_ambient += (target_ambient - self.vol_ambient) * min(1.0, dt * 3.0)
        self.vol_bass += (target_bass - self.vol_bass) * min(1.0, dt * 3.0)
        self.vol_drums += (target_drums - self.vol_drums) * min(1.0, dt * drum_fade_speed)
        self.vol_texture += (target_texture - self.vol_texture) * min(1.0, dt * 2.0)

        self._update_channel_volumes()

    def _update_channel_volumes(self) -> None:
        """Apply computed volumes to the dedicated Pygame mixer channels."""
        if not self.initialized:
            return

        master = self.master_music_volume
        if self.channels["ambient"]:
            self.channels["ambient"].set_volume(self.vol_ambient * master)
        if self.channels["bass"]:
            self.channels["bass"].set_volume(self.vol_bass * master)
        if self.channels["drums"]:
            self.channels["drums"].set_volume(self.vol_drums * master)
        if self.channels["texture"]:
            self.channels["texture"].set_volume(self.vol_texture * master)

    def stop_all(self) -> None:
        """Stop all music playback."""
        if not self.initialized:
            return
        for channel in self.channels.values():
            if channel:
                channel.stop()
