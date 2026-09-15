"""Audio Manager: Mixer control, sound cache, and sound playback throttling."""

import random
from typing import Dict, Optional
import pygame

from py_noita.audio.sound_synth import (
    build_full_sound_catalog,
    synth_acid_sizzle,
    synth_bone_crack,
    synth_explosion,
    synth_pickup,
    synth_shot,
    synth_squelch,
)
from py_noita.audio.music_engine import AdaptiveMusicEngine, THEME_INCUBATION, THEME_BOSS
from py_noita.audio.acoustics import AcousticsEngine
from py_noita.audio.spatial import SpatialAudioEngine
from py_noita.simulation.materials import (
    MAT_BONE,
    MAT_WALL_BONE,
    MAT_BONE_CHIP,
    MAT_CHITIN,
    MAT_BLOOD,
    MAT_ACID,
    MAT_BILE,
    MAT_LYMPH,
    MAT_PUS,
    MAT_MUTAGEN,
    MAT_GOLD,
    MAT_SPORES,
    MAT_NERVE,
    MAT_ASH,
)


class AudioManager:
    """Manages playing synthesized visceral audio effects, dynamic acoustics, and adaptive soundtrack."""

    def __init__(self):
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.cooldowns: Dict[str, float] = {}
        self.initialized: bool = False
        self.master_volume: float = 0.8
        self.music_volume: float = 0.7
        self.sfx_volume: float = 0.8
        self.ambient_volume: float = 0.7
        self._init_audio()
        self.music: AdaptiveMusicEngine = AdaptiveMusicEngine()
        self.acoustics: AcousticsEngine = AcousticsEngine()
        self.spatial: SpatialAudioEngine = SpatialAudioEngine()
        if hasattr(self, "music") and self.music:
            self.music.master_music_volume = self.master_volume * self.music_volume

    def apply_settings(self, settings) -> None:
        """Apply volume sliders from SettingsManager."""
        self.master_volume = float(getattr(settings, "master_volume", 0.8))
        self.music_volume = float(getattr(settings, "music_volume", 0.7))
        self.sfx_volume = float(getattr(settings, "sfx_volume", 0.8))
        self.ambient_volume = float(getattr(settings, "ambient_volume", 0.7))
        if hasattr(self, "music") and self.music:
            self.music.master_music_volume = self.master_volume * self.music_volume

    def _init_audio(self) -> None:
        """Synthesize and pre-cache all procedural sound effects (60+ SFX)."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

            self.sounds = build_full_sound_catalog()
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

        effective_vol = max(0.0, min(1.0, volume * self.master_volume * self.sfx_volume * ducking * muffle))
        sound = self.sounds[sound_name]
        sound.set_volume(effective_vol)
        sound.play()
        self.cooldowns[sound_name] = throttle

    def play_spatial(
        self,
        sound_name: str,
        world_x: float,
        world_y: float,
        listener_x: float,
        listener_y: float,
        volume: float = 0.8,
        throttle: float = 0.05,
    ) -> Optional[pygame.mixer.Channel]:
        """Play a sound effect located at world coordinates with 3D stereo panning and attenuation."""
        if not self.initialized or sound_name not in self.sounds:
            return None

        if sound_name in self.cooldowns:
            return None

        ducking = self.acoustics.heartbeat_ducking if hasattr(self, "acoustics") else 1.0
        muffle = (1.0 - 0.55 * self.acoustics.submerged_factor) if hasattr(self, "acoustics") else 1.0

        effective_base_vol = volume * self.master_volume * self.sfx_volume
        sound = self.sounds[sound_name]
        channel = self.spatial.play_spatial(
            sound,
            world_x=world_x,
            world_y=world_y,
            listener_x=listener_x,
            listener_y=listener_y,
            base_volume=effective_base_vol,
            ducking=ducking,
            muffle=muffle,
        )
        if channel:
            self.cooldowns[sound_name] = throttle
        return channel

    def play_footstep(
        self,
        surface_mat: int,
        world_x: float,
        world_y: float,
        listener_x: float,
        listener_y: float,
        is_crawl: bool = False,
        volume: float = 0.55,
    ) -> Optional[pygame.mixer.Channel]:
        """Play a footstep or crawl sound matched to the ground material."""
        var = random.randint(1, 3)
        if is_crawl:
            s_name = f"crawl_tentacle_{var}"
        elif surface_mat in (MAT_BONE, MAT_WALL_BONE, MAT_BONE_CHIP, MAT_CHITIN):
            s_name = f"footstep_bone_{var}"
        elif surface_mat in (MAT_BLOOD, MAT_ACID, MAT_BILE, MAT_LYMPH, MAT_PUS, MAT_MUTAGEN):
            s_name = f"footstep_slime_{var}"
        else:
            s_name = f"footstep_flesh_{var}"

        return self.play_spatial(
            s_name,
            world_x=world_x,
            world_y=world_y,
            listener_x=listener_x,
            listener_y=listener_y,
            volume=volume,
            throttle=0.18,
        )

    def play_material_impact(
        self,
        mat: int,
        world_x: float,
        world_y: float,
        listener_x: float,
        listener_y: float,
        volume: float = 0.7,
    ) -> Optional[pygame.mixer.Channel]:
        """Play a physical impact sound matching the struck material."""
        if mat in (MAT_BONE, MAT_WALL_BONE, MAT_BONE_CHIP):
            s_name = "impact_bone"
        elif mat == MAT_CHITIN:
            s_name = "impact_chitin"
        elif mat == MAT_GOLD:
            s_name = "impact_gold"
        elif mat == MAT_ACID:
            s_name = "impact_acid"
        elif mat in (MAT_BLOOD, MAT_BILE, MAT_LYMPH, MAT_PUS, MAT_MUTAGEN):
            s_name = "impact_liquid"
        elif mat == MAT_SPORES:
            s_name = "impact_spores"
        elif mat == MAT_NERVE:
            s_name = "impact_nerve"
        elif mat == MAT_ASH:
            s_name = "impact_ash"
        else:
            s_name = "impact_flesh"

        return self.play_spatial(
            s_name,
            world_x=world_x,
            world_y=world_y,
            listener_x=listener_x,
            listener_y=listener_y,
            volume=volume,
            throttle=0.06,
        )
