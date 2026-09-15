"""Procedural synthesis of visceral organic sound effects using NumPy.

Generates 60+ unique organic sound effects across 6 distinct categories:
1. Footsteps by terrain type (Flesh, Bone, Slime, Tentacle crawl)
2. Projectile launches & attacks (16 weapon variants)
3. Material impacts (12 surface-specific collisions)
4. Corrosion, combustion & transmutations (8 chemical processes)
5. Enemy vocalizations & boss acoustics (8 biological cries)
6. UI, implants, and environmental triggers (8 feedback cues)
"""

import math
import random
from typing import Dict
import numpy as np
import pygame

from py_noita.config import AUDIO_SAMPLE_RATE


def create_sound_from_array(samples: np.ndarray) -> pygame.mixer.Sound:
    """Convert float32 NumPy audio samples (-1.0 to 1.0) into a 16-bit stereo Pygame Sound."""
    clipped = np.clip(samples, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype(np.int16)
    if pcm.ndim == 1:
        stereo_pcm = np.column_stack((pcm, pcm))
    else:
        stereo_pcm = pcm
    return pygame.mixer.Sound(buffer=stereo_pcm.tobytes())


# -----------------------------------------------------------------------------
# Primitive Procedural Generators (Fast, vectorized NumPy synthesis)
# -----------------------------------------------------------------------------

def _synth_fm_pulse(f_c: float, f_m: float, mod_idx: float, duration: float, decay_rate: float) -> np.ndarray:
    """Frequency modulation carrier with exponential decay."""
    sr = AUDIO_SAMPLE_RATE
    num_samples = max(64, int(sr * duration))
    t = np.linspace(0, duration, num_samples, endpoint=False)
    modulator = np.sin(2 * np.pi * f_m * t) * mod_idx
    carrier = np.sin(2 * np.pi * f_c * t + modulator)
    envelope = np.exp(-t * decay_rate)
    return (carrier * envelope).astype(np.float32)


def _synth_noise_burst(duration: float, decay_rate: float, tone_mix: float = 0.0, tone_f: float = 200.0) -> np.ndarray:
    """Filtered noise transient with optional harmonic tone mix."""
    sr = AUDIO_SAMPLE_RATE
    num_samples = max(64, int(sr * duration))
    t = np.linspace(0, duration, num_samples, endpoint=False)
    noise = np.random.uniform(-0.9, 0.9, num_samples)
    if tone_mix > 0.0:
        tone = np.sin(2 * np.pi * tone_f * t)
        signal = noise * (1.0 - tone_mix) + tone * tone_mix
    else:
        signal = noise
    envelope = np.exp(-t * decay_rate)
    return (signal * envelope).astype(np.float32)


def _synth_pitch_bend(f_start: float, f_end: float, duration: float, decay_rate: float) -> np.ndarray:
    """Swept sine wave transient."""
    sr = AUDIO_SAMPLE_RATE
    num_samples = max(64, int(sr * duration))
    t = np.linspace(0, duration, num_samples, endpoint=False)
    freq = np.linspace(f_start, f_end, num_samples)
    carrier = np.sin(2 * np.pi * freq * t)
    envelope = np.exp(-t * decay_rate)
    return (carrier * envelope).astype(np.float32)


# -----------------------------------------------------------------------------
# 1. Footsteps by Terrain Type (12 SFX)
# -----------------------------------------------------------------------------

def synth_footstep_flesh(variant: int = 1) -> pygame.mixer.Sound:
    """Wet, squelching footsteps on raw tissue walls."""
    base_f = 220.0 + variant * 35.0
    arr = _synth_fm_pulse(base_f, 65.0, 3.0, 0.09, 38.0) * 0.7
    noise = _synth_noise_burst(0.09, 45.0) * 0.35
    return create_sound_from_array(arr + noise)


def synth_footstep_bone(variant: int = 1) -> pygame.mixer.Sound:
    """Snappy clattering tap on calcified bone or chitin."""
    base_f = 650.0 + variant * 90.0
    arr = _synth_pitch_bend(base_f, base_f * 0.3, 0.06, 55.0) * 0.6
    noise = _synth_noise_burst(0.06, 65.0) * 0.5
    return create_sound_from_array(arr + noise)


def synth_footstep_slime(variant: int = 1) -> pygame.mixer.Sound:
    """Viscous, sticky bubbling squish on bile/mucus pools."""
    base_f = 140.0 + variant * 20.0
    arr = _synth_fm_pulse(base_f, 25.0, 5.0, 0.14, 24.0) * 0.75
    return create_sound_from_array(arr)


def synth_crawl_tentacle(variant: int = 1) -> pygame.mixer.Sound:
    """Organic suction and peeling release of gripping tentacles."""
    arr = _synth_pitch_bend(340.0 + variant * 40.0, 110.0, 0.11, 28.0) * 0.55
    noise = _synth_noise_burst(0.11, 35.0) * 0.3
    return create_sound_from_array(arr + noise)


# -----------------------------------------------------------------------------
# 2. Weapon Launches & Projectile Attacks (16 SFX)
# -----------------------------------------------------------------------------

def synth_shot(duration: float = 0.10) -> pygame.mixer.Sound:
    """Punchy visceral bio-projectile launch."""
    arr = _synth_pitch_bend(440.0, 85.0, duration, 32.0) * 0.6
    noise = _synth_noise_burst(duration, 35.0) * 0.4
    return create_sound_from_array(arr + noise)


def synth_proj_cartilage_shot() -> pygame.mixer.Sound:
    """Sharp shotgun-like snapping cartilage burst."""
    arr = _synth_noise_burst(0.12, 28.0, tone_mix=0.4, tone_f=380.0) * 0.8
    sub = _synth_pitch_bend(220.0, 50.0, 0.12, 22.0) * 0.5
    return create_sound_from_array(arr + sub)


def synth_proj_cytokine_laser() -> pygame.mixer.Sound:
    """High-pitched bio-electric searing beam."""
    sr = AUDIO_SAMPLE_RATE
    t = np.linspace(0, 0.18, int(sr * 0.18), endpoint=False)
    freq = np.linspace(1600.0, 750.0, len(t))
    mod = np.sin(2 * np.pi * 120.0 * t) * 0.3
    laser = np.sin(2 * np.pi * freq * t) * (0.7 + mod) * np.exp(-t * 14.0)
    return create_sound_from_array(laser.astype(np.float32))


def synth_proj_plasma_tendril() -> pygame.mixer.Sound:
    """Crackling high-voltage plasma tendril discharge."""
    arr = _synth_fm_pulse(720.0, 180.0, 4.5, 0.15, 20.0) * 0.7
    noise = _synth_noise_burst(0.15, 25.0) * 0.4
    return create_sound_from_array(arr + noise)


def synth_proj_spore_mortar() -> pygame.mixer.Sound:
    """Deep hollow spore launch cough."""
    sub = _synth_pitch_bend(180.0, 45.0, 0.22, 12.0) * 0.8
    poof = _synth_noise_burst(0.22, 18.0) * 0.3
    return create_sound_from_array(sub + poof)


def synth_proj_bone_boomerang() -> pygame.mixer.Sound:
    """Whirring, spinning bone blade."""
    sr = AUDIO_SAMPLE_RATE
    t = np.linspace(0, 0.25, int(sr * 0.25), endpoint=False)
    whir = np.sin(2 * np.pi * 540.0 * t) * (np.sin(2 * np.pi * 18.0 * t) * 0.5 + 0.5) * np.exp(-t * 8.0)
    return create_sound_from_array(whir.astype(np.float32))


def synth_proj_slime_glob() -> pygame.mixer.Sound:
    """Heavy viscous mucus mass launch."""
    return create_sound_from_array(_synth_fm_pulse(160.0, 32.0, 6.0, 0.16, 18.0) * 0.8)


def synth_proj_acid_dart() -> pygame.mixer.Sound:
    """Hissing aerodynamic corrosive needle."""
    noise = _synth_noise_burst(0.12, 22.0) * 0.6
    whistle = _synth_pitch_bend(950.0, 450.0, 0.12, 26.0) * 0.4
    return create_sound_from_array(noise + whistle)


def synth_proj_nerve_jolt() -> pygame.mixer.Sound:
    """Buzzing synapse zap."""
    return create_sound_from_array(_synth_fm_pulse(880.0, 60.0, 5.0, 0.12, 25.0) * 0.7)


def synth_proj_macrophage_maw() -> pygame.mixer.Sound:
    """Snapping visceral bio-jaw chomp."""
    snap = _synth_pitch_bend(520.0, 70.0, 0.10, 35.0) * 0.7
    noise = _synth_noise_burst(0.10, 40.0) * 0.4
    return create_sound_from_array(snap + noise)


def synth_proj_blood_surge() -> pygame.mixer.Sound:
    """Hydraulic arterial jet squirt."""
    return create_sound_from_array(_synth_fm_pulse(280.0, 42.0, 4.0, 0.18, 16.0) * 0.75)


def synth_proj_chitin_spike() -> pygame.mixer.Sound:
    """Dense high-velocity needle thrust."""
    return create_sound_from_array(_synth_pitch_bend(1100.0, 240.0, 0.08, 45.0) * 0.7)


def synth_proj_biogas_jet() -> pygame.mixer.Sound:
    """Pressurized vent hiss."""
    return create_sound_from_array(_synth_noise_burst(0.20, 14.0) * 0.65)


def synth_proj_parasite_needle() -> pygame.mixer.Sound:
    """Piercing high-pitched chitin probe."""
    return create_sound_from_array(_synth_pitch_bend(1400.0, 600.0, 0.09, 32.0) * 0.6)


def synth_proj_mutagen_pulse() -> pygame.mixer.Sound:
    """Eerie ascending alien frequency warble."""
    sr = AUDIO_SAMPLE_RATE
    t = np.linspace(0, 0.20, int(sr * 0.20), endpoint=False)
    freq = np.linspace(300.0, 780.0, len(t))
    warble = np.sin(2 * np.pi * freq * t) * (np.sin(2 * np.pi * 35.0 * t) * 0.4 + 0.6) * np.exp(-t * 10.0)
    return create_sound_from_array(warble.astype(np.float32))


def synth_proj_vacuum_suck() -> pygame.mixer.Sound:
    """Reverse air/liquid intake."""
    arr = _synth_pitch_bend(80.0, 360.0, 0.16, 8.0) * 0.6
    return create_sound_from_array(arr)


# -----------------------------------------------------------------------------
# 3. Material Impacts & Collisions (12 SFX)
# -----------------------------------------------------------------------------

def synth_impact_flesh() -> pygame.mixer.Sound:
    """Heavy blunt meat thud."""
    sub = _synth_pitch_bend(180.0, 45.0, 0.12, 28.0) * 0.8
    noise = _synth_noise_burst(0.12, 35.0) * 0.3
    return create_sound_from_array(sub + noise)


def synth_impact_bone() -> pygame.mixer.Sound:
    """Hard calcified fracture snap."""
    return create_sound_from_array(_synth_pitch_bend(750.0, 160.0, 0.07, 50.0) * 0.8)


def synth_impact_chitin() -> pygame.mixer.Sound:
    """Armored carapace ricochet ping."""
    return create_sound_from_array(_synth_fm_pulse(920.0, 310.0, 2.5, 0.08, 42.0) * 0.75)


def synth_impact_liquid() -> pygame.mixer.Sound:
    """Visceral liquid splatter and ripple."""
    return create_sound_from_array(_synth_fm_pulse(310.0, 55.0, 3.8, 0.14, 22.0) * 0.7)


def synth_impact_acid() -> pygame.mixer.Sound:
    """Corrosive sizzle splatter."""
    noise = _synth_noise_burst(0.16, 20.0) * 0.65
    sizzle = _synth_fm_pulse(640.0, 80.0, 3.0, 0.16, 24.0) * 0.35
    return create_sound_from_array(noise + sizzle)


def synth_impact_ash() -> pygame.mixer.Sound:
    """Soft dusty powder puff."""
    return create_sound_from_array(_synth_noise_burst(0.14, 26.0) * 0.5)


def synth_impact_gold() -> pygame.mixer.Sound:
    """Resonant metallic cellular chime."""
    sr = AUDIO_SAMPLE_RATE
    t = np.linspace(0, 0.22, int(sr * 0.22), endpoint=False)
    bell = (np.sin(2 * np.pi * 1250.0 * t) * 0.5 + np.sin(2 * np.pi * 2500.0 * t) * 0.3) * np.exp(-t * 15.0)
    return create_sound_from_array(bell.astype(np.float32))


def synth_impact_spores() -> pygame.mixer.Sound:
    """Powdery spore burst pop."""
    return create_sound_from_array(_synth_noise_burst(0.15, 22.0, tone_mix=0.3, tone_f=280.0) * 0.6)


def synth_impact_membrane() -> pygame.mixer.Sound:
    """Elastic rubbery bounce."""
    return create_sound_from_array(_synth_fm_pulse(190.0, 45.0, 4.0, 0.15, 20.0) * 0.7)


def synth_impact_nerve() -> pygame.mixer.Sound:
    """High-voltage electric spark snap."""
    return create_sound_from_array(_synth_fm_pulse(1100.0, 120.0, 3.5, 0.09, 40.0) * 0.7)


def synth_impact_wood_cartilage() -> pygame.mixer.Sound:
    """Fibrous splintering crunch."""
    arr = _synth_pitch_bend(420.0, 95.0, 0.11, 32.0) * 0.5
    noise = _synth_noise_burst(0.11, 38.0) * 0.5
    return create_sound_from_array(arr + noise)


def synth_impact_void() -> pygame.mixer.Sound:
    """Abyssal low-frequency rumble."""
    return create_sound_from_array(_synth_pitch_bend(95.0, 25.0, 0.35, 9.0) * 0.85)


# -----------------------------------------------------------------------------
# 4. Corrosion, Dissolution & Transmutation (8 SFX)
# -----------------------------------------------------------------------------

def synth_acid_sizzle(duration: float = 0.25) -> pygame.mixer.Sound:
    """Fizzing, bubbling corrosive reaction."""
    noise = _synth_noise_burst(duration, 14.0) * 0.6
    mod = _synth_fm_pulse(420.0, 35.0, 4.0, duration, 16.0) * 0.4
    return create_sound_from_array(noise + mod)


def synth_dissolve_flesh() -> pygame.mixer.Sound:
    """Foaming digestive acid hiss on soft tissue."""
    return create_sound_from_array(_synth_noise_burst(0.28, 12.0) * 0.6)


def synth_dissolve_bone() -> pygame.mixer.Sound:
    """Brittle porous bubbling dissolution."""
    noise = _synth_noise_burst(0.22, 16.0) * 0.5
    crackle = _synth_pitch_bend(780.0, 210.0, 0.22, 18.0) * 0.4
    return create_sound_from_array(noise + crackle)


def synth_transmute_midas() -> pygame.mixer.Sound:
    """Ascending golden chime glissando."""
    sr = AUDIO_SAMPLE_RATE
    t = np.linspace(0, 0.35, int(sr * 0.35), endpoint=False)
    freq = np.linspace(500.0, 1800.0, len(t))
    chime = np.sin(2 * np.pi * freq * t) * np.exp(-t * 8.0) * 0.7
    return create_sound_from_array(chime.astype(np.float32))


def synth_transmute_mutagen() -> pygame.mixer.Sound:
    """Warbling unstable mutagen reaction."""
    return create_sound_from_array(_synth_fm_pulse(320.0, 28.0, 7.0, 0.30, 10.0) * 0.7)


def synth_fire_ignite() -> pygame.mixer.Sound:
    """Whoosh of sudden biogas ignition."""
    noise = _synth_noise_burst(0.24, 15.0) * 0.7
    sub = _synth_pitch_bend(140.0, 40.0, 0.24, 16.0) * 0.5
    return create_sound_from_array(noise + sub)


def synth_fire_crackle() -> pygame.mixer.Sound:
    """Continuous burning sizzle crackle."""
    return create_sound_from_array(_synth_noise_burst(0.20, 20.0) * 0.5)


def synth_freeze_cyst() -> pygame.mixer.Sound:
    """Rapid calcification crack."""
    return create_sound_from_array(_synth_pitch_bend(1200.0, 300.0, 0.12, 30.0) * 0.65)


# -----------------------------------------------------------------------------
# 5. Entity Voices, AI & Organic Cries (8 SFX)
# -----------------------------------------------------------------------------

def synth_enemy_spider_skitter() -> pygame.mixer.Sound:
    """Chittering multi-legged chitin clicks."""
    return create_sound_from_array(_synth_noise_burst(0.08, 48.0, tone_mix=0.5, tone_f=850.0) * 0.6)


def synth_enemy_beetle_screech() -> pygame.mixer.Sound:
    """Abrasive grating chitin rasp."""
    return create_sound_from_array(_synth_fm_pulse(720.0, 140.0, 6.0, 0.18, 16.0) * 0.7)


def synth_enemy_tcell_hum() -> pygame.mixer.Sound:
    """Throbbing cellular patrol vibration."""
    return create_sound_from_array(_synth_fm_pulse(110.0, 12.0, 4.0, 0.30, 8.0) * 0.7)


def synth_enemy_worm_burrow() -> pygame.mixer.Sound:
    """Deep subterranean flesh displacement."""
    sub = _synth_pitch_bend(85.0, 30.0, 0.40, 7.0) * 0.8
    crunch = _synth_noise_burst(0.40, 9.0) * 0.4
    return create_sound_from_array(sub + crunch)


def synth_enemy_macrophage_groan() -> pygame.mixer.Sound:
    """Amoeboid guttural suction."""
    return create_sound_from_array(_synth_fm_pulse(160.0, 22.0, 5.0, 0.28, 10.0) * 0.75)


def synth_boss_roar() -> pygame.mixer.Sound:
    """Colossal guttural bio-titan roar."""
    sr = AUDIO_SAMPLE_RATE
    duration = 0.65
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    roar = np.sin(2 * np.pi * 58.0 * t) * 0.5 + np.random.uniform(-0.8, 0.8, len(t)) * 0.5
    mod = (np.sin(2 * np.pi * 14.0 * t) + 1.0) * 0.5
    env = np.exp(-t * 4.5)
    return create_sound_from_array((roar * mod * env * 0.85).astype(np.float32))


def synth_boss_teleport() -> pygame.mixer.Sound:
    """Synaptic spatial distortion snap."""
    return create_sound_from_array(_synth_pitch_bend(1500.0, 120.0, 0.18, 20.0) * 0.7)


def synth_player_hurt() -> pygame.mixer.Sound:
    """Visceral organ trauma spasm."""
    arr = _synth_pitch_bend(290.0, 65.0, 0.14, 25.0) * 0.7
    noise = _synth_noise_burst(0.14, 30.0) * 0.4
    return create_sound_from_array(arr + noise)


# -----------------------------------------------------------------------------
# 6. UI, Pickups & World Triggers (8 SFX)
# -----------------------------------------------------------------------------

def synth_pickup(duration: float = 0.18) -> pygame.mixer.Sound:
    """Bioluminescent cellular absorption chime."""
    sr = AUDIO_SAMPLE_RATE
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    chord = (
        np.sin(2 * np.pi * 440.0 * t) * 0.4
        + np.sin(2 * np.pi * 554.3 * t) * 0.35
        + np.sin(2 * np.pi * 659.2 * t) * 0.3
    )
    return create_sound_from_array((chord * np.exp(-t * 12.0) * 0.6).astype(np.float32))


def synth_pickup_gene_orb() -> pygame.mixer.Sound:
    """Sacred harmonic organ chord resonance."""
    sr = AUDIO_SAMPLE_RATE
    t = np.linspace(0, 0.45, int(sr * 0.45), endpoint=False)
    # C major chord with octave shimmer
    c = np.sin(2 * np.pi * 523.2 * t) * 0.35
    e = np.sin(2 * np.pi * 659.2 * t) * 0.30
    g = np.sin(2 * np.pi * 783.9 * t) * 0.25
    c2 = np.sin(2 * np.pi * 1046.5 * t) * 0.15
    return create_sound_from_array(((c + e + g + c2) * np.exp(-t * 6.0) * 0.8).astype(np.float32))


def synth_perk_implant() -> pygame.mixer.Sound:
    """Surgical organ graft squelch and power-up bell."""
    squelch = _synth_fm_pulse(220.0, 45.0, 4.0, 0.24, 15.0) * 0.5
    bell = _synth_pitch_bend(440.0, 880.0, 0.24, 12.0) * 0.4
    return create_sound_from_array(squelch + bell)


def synth_portal_ambient() -> pygame.mixer.Sound:
    """Pulsing spatial gateway drone."""
    return create_sound_from_array(_synth_fm_pulse(75.0, 4.0, 3.0, 0.40, 5.0) * 0.6)


def synth_portal_enter() -> pygame.mixer.Sound:
    """Inter-organ dimensional warp vortex."""
    return create_sound_from_array(_synth_pitch_bend(950.0, 45.0, 0.35, 7.5) * 0.8)


def synth_wand_reload() -> pygame.mixer.Sound:
    """Pneumatic organ recharge gasp."""
    return create_sound_from_array(_synth_pitch_bend(120.0, 310.0, 0.16, 16.0) * 0.6)


def synth_explosion(duration: float = 0.55) -> pygame.mixer.Sound:
    """Low rumbling biogas explosion with crunchy transient."""
    sub = _synth_pitch_bend(90.0, 25.0, duration, 6.5) * 0.6
    noise = _synth_noise_burst(duration, 7.0) * 0.5
    return create_sound_from_array(sub + noise)


def synth_squelch(duration: float = 0.12) -> pygame.mixer.Sound:
    """Classic wet squelch."""
    return synth_footstep_flesh(1)


def synth_bone_crack(duration: float = 0.08) -> pygame.mixer.Sound:
    """Classic bone fracture."""
    return synth_impact_bone()


# -----------------------------------------------------------------------------
# Master Sound Arsenal Catalog Builder (60+ SFX)
# -----------------------------------------------------------------------------

def build_full_sound_catalog() -> Dict[str, pygame.mixer.Sound]:
    """Pre-render the complete procedural catalog of 60+ SFX for instant zero-latency playback."""
    catalog: Dict[str, pygame.mixer.Sound] = {}

    # Category 1: Footsteps & Crawling (12)
    for i in (1, 2, 3):
        catalog[f"footstep_flesh_{i}"] = synth_footstep_flesh(i)
        catalog[f"footstep_bone_{i}"] = synth_footstep_bone(i)
        catalog[f"footstep_slime_{i}"] = synth_footstep_slime(i)
        catalog[f"crawl_tentacle_{i}"] = synth_crawl_tentacle(i)

    # Category 2: Weapon Launches & Projectiles (16)
    catalog["shot"] = synth_shot()
    catalog["proj_cartilage_shot"] = synth_proj_cartilage_shot()
    catalog["proj_cytokine_laser"] = synth_proj_cytokine_laser()
    catalog["proj_plasma_tendril"] = synth_proj_plasma_tendril()
    catalog["proj_spore_mortar"] = synth_proj_spore_mortar()
    catalog["proj_bone_boomerang"] = synth_proj_bone_boomerang()
    catalog["proj_slime_glob"] = synth_proj_slime_glob()
    catalog["proj_acid_dart"] = synth_proj_acid_dart()
    catalog["proj_nerve_jolt"] = synth_proj_nerve_jolt()
    catalog["proj_macrophage_maw"] = synth_proj_macrophage_maw()
    catalog["proj_blood_surge"] = synth_proj_blood_surge()
    catalog["proj_chitin_spike"] = synth_proj_chitin_spike()
    catalog["proj_biogas_jet"] = synth_proj_biogas_jet()
    catalog["proj_parasite_needle"] = synth_proj_parasite_needle()
    catalog["proj_mutagen_pulse"] = synth_proj_mutagen_pulse()
    catalog["proj_vacuum_suck"] = synth_proj_vacuum_suck()

    # Category 3: Material Impacts (12)
    catalog["impact_flesh"] = synth_impact_flesh()
    catalog["impact_bone"] = synth_impact_bone()
    catalog["impact_chitin"] = synth_impact_chitin()
    catalog["impact_liquid"] = synth_impact_liquid()
    catalog["impact_acid"] = synth_impact_acid()
    catalog["impact_ash"] = synth_impact_ash()
    catalog["impact_gold"] = synth_impact_gold()
    catalog["impact_spores"] = synth_impact_spores()
    catalog["impact_membrane"] = synth_impact_membrane()
    catalog["impact_nerve"] = synth_impact_nerve()
    catalog["impact_wood_cartilage"] = synth_impact_wood_cartilage()
    catalog["impact_void"] = synth_impact_void()

    # Category 4: Corrosion & Transmutation (8)
    catalog["acid"] = synth_acid_sizzle()
    catalog["dissolve_flesh"] = synth_dissolve_flesh()
    catalog["dissolve_bone"] = synth_dissolve_bone()
    catalog["transmute_midas"] = synth_transmute_midas()
    catalog["transmute_mutagen"] = synth_transmute_mutagen()
    catalog["fire_ignite"] = synth_fire_ignite()
    catalog["fire_crackle"] = synth_fire_crackle()
    catalog["freeze_cyst"] = synth_freeze_cyst()

    # Category 5: Entity & Boss Sounds (8)
    catalog["enemy_spider_skitter"] = synth_enemy_spider_skitter()
    catalog["enemy_beetle_screech"] = synth_enemy_beetle_screech()
    catalog["enemy_tcell_hum"] = synth_enemy_tcell_hum()
    catalog["enemy_worm_burrow"] = synth_enemy_worm_burrow()
    catalog["enemy_macrophage_groan"] = synth_enemy_macrophage_groan()
    catalog["boss_roar"] = synth_boss_roar()
    catalog["boss_teleport"] = synth_boss_teleport()
    catalog["player_hurt"] = synth_player_hurt()

    # Category 6: UI, Pickups & World (8)
    catalog["pickup"] = synth_pickup()
    catalog["pickup_gene_orb"] = synth_pickup_gene_orb()
    catalog["perk_implant"] = synth_perk_implant()
    catalog["portal_ambient"] = synth_portal_ambient()
    catalog["portal_enter"] = synth_portal_enter()
    catalog["wand_reload"] = synth_wand_reload()
    catalog["explosion"] = synth_explosion()
    catalog["squelch"] = synth_squelch()
    catalog["bone_crack"] = synth_bone_crack()

    return catalog
