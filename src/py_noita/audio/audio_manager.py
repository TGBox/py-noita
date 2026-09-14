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


class AudioManager:
    """Manages playing synthesized visceral audio effects with rate limiting."""

    def __init__(self):
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.cooldowns: Dict[str, float] = {}
        self.initialized: bool = False
        self._init_audio()

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

    def update(self, dt: float) -> None:
        """Tick sound cooldowns."""
        for key in list(self.cooldowns.keys()):
            self.cooldowns[key] -= dt
            if self.cooldowns[key] <= 0.0:
                del self.cooldowns[key]

    def play(self, sound_name: str, volume: float = 0.8, throttle: float = 0.06) -> None:
        """Play a sound effect if not throttled."""
        if not self.initialized or sound_name not in self.sounds:
            return

        if sound_name in self.cooldowns:
            return

        sound = self.sounds[sound_name]
        sound.set_volume(max(0.0, min(1.0, volume)))
        sound.play()
        self.cooldowns[sound_name] = throttle
