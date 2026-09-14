"""Audio Manager: Mixer control, sound cache, and sound playback throttling."""

from typing import Dict, Optional
import pygame

from py_noita.audio.sound_synth import (
    synth_acid_sizzle,
    synth_bone_crack,
    synth_explosion,
    synth_pickup,
    synth_shot,
    synth_squelch,
)
from py_noita.audio.music_engine import AdaptiveMusicEngine, THEME_INCUBATION, THEME_BOSS
from py_noita.audio.acoustics import AcousticsEngine


class AudioManager:
    """Manages playing synthesized visceral audio effects, dynamic acoustics, and adaptive soundtrack."""

    def __init__(self):
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.cooldowns: Dict[str, float] = {}
        self.initialized: bool = False
        self._init_audio()
        self.music: AdaptiveMusicEngine = AdaptiveMusicEngine()
        self.acoustics: AcousticsEngine = AcousticsEngine()

    def _init_audio(self) -> None:
        """Synthesize and pre-cache all procedural sound effects."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

            self.sounds["squelch"] = synth_squelch()
            self.sounds["acid"] = synth_acid_sizzle()
            self.sounds["explosion"] = synth_explosion()
            self.sounds["shot"] = synth_shot()
            self.sounds["bone_crack"] = synth_bone_crack()
            self.sounds["pickup"] = synth_pickup()

            self.initialized = True
        except Exception:
            # Fallback gracefully if audio hardware unavailable in headless env
            self.initialized = False

    def update(self, dt: float, player: Optional[object] = None, grid: Optional[object] = None) -> None:
        """Tick sound cooldowns, acoustic environmental filtering, and adaptive music."""
        for key in list(self.cooldowns.keys()):
            self.cooldowns[key] -= dt
            if self.cooldowns[key] <= 0.0:
                del self.cooldowns[key]

        mods = None
        if hasattr(self, "acoustics") and self.acoustics:
            self.acoustics.update(dt, player, grid)
            mods = self.acoustics.get_music_modifiers()

        if hasattr(self, "music") and self.music:
            self.music.update(dt, acoustic_modifiers=mods)

    def play(self, sound_name: str, volume: float = 0.8, throttle: float = 0.06) -> None:
        """Play a sound effect if not throttled, modulated by acoustics (ducking & muffle)."""
        if not self.initialized or sound_name not in self.sounds:
            return

        if sound_name in self.cooldowns:
            return

        # Acoustic modulation: low-HP ducking and underwater muffling
        ducking = self.acoustics.heartbeat_ducking if hasattr(self, "acoustics") else 1.0
        muffle = (1.0 - 0.55 * self.acoustics.submerged_factor) if hasattr(self, "acoustics") else 1.0

        effective_vol = max(0.0, min(1.0, volume * ducking * muffle))
        sound = self.sounds[sound_name]
        sound.set_volume(effective_vol)
        sound.play()
        self.cooldowns[sound_name] = throttle
