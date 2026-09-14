"""Procedural synthesis of visceral organic sound effects using NumPy."""

import math
from typing import Dict
import pygame
import numpy as np

from py_noita.config import AUDIO_SAMPLE_RATE


def create_sound_from_array(samples: np.ndarray) -> pygame.mixer.Sound:
    """Convert float32/int16 NumPy audio samples (-1.0 to 1.0) into a Pygame Sound."""
    # Ensure float in -1.0 to 1.0
    clipped = np.clip(samples, -1.0, 1.0)
    # Convert to 16-bit PCM
    pcm = (clipped * 32767.0).astype(np.int16)
    # Stereo expansion if 1D
    if pcm.ndim == 1:
        stereo_pcm = np.column_stack((pcm, pcm))
    else:
        stereo_pcm = pcm
    return pygame.mixer.Sound(buffer=stereo_pcm.tobytes())


def synth_squelch(duration: float = 0.12) -> pygame.mixer.Sound:
    """Visceral wet squelch/flesh sound for movement and liquid impact."""
    sr = AUDIO_SAMPLE_RATE
    num_samples = int(sr * duration)
    t = np.linspace(0, duration, num_samples, endpoint=False)

    # Modulated sine wave with quick downward pitch bend
    pitch = np.linspace(280.0, 70.0, num_samples)
    noise = np.random.uniform(-0.4, 0.4, num_samples)
    carrier = np.sin(2 * np.pi * pitch * t) * 0.6 + noise * 0.4

    # Envelope: quick attack, bubbling exponential decay
    envelope = np.exp(-t * 22.0)
    samples = carrier * envelope
    return create_sound_from_array(samples)


def synth_acid_sizzle(duration: float = 0.25) -> pygame.mixer.Sound:
    """Fizzing, bubbling corrosive reaction sound."""
    sr = AUDIO_SAMPLE_RATE
    num_samples = int(sr * duration)
    t = np.linspace(0, duration, num_samples, endpoint=False)

    # High frequency noise modulated by low frequency bubbling
    noise = np.random.uniform(-1.0, 1.0, num_samples)
    bubble_mod = (np.sin(2 * np.pi * 32.0 * t) + 1.0) * 0.5
    envelope = np.sin(np.pi * (t / duration)) ** 0.5

    samples = noise * bubble_mod * envelope * 0.35
    return create_sound_from_array(samples)


def synth_explosion(duration: float = 0.55) -> pygame.mixer.Sound:
    """Low rumbling biogas explosion with crunchy transient."""
    sr = AUDIO_SAMPLE_RATE
    num_samples = int(sr * duration)
    t = np.linspace(0, duration, num_samples, endpoint=False)

    # Low sub-bass sine wave decaying from 85Hz down to 25Hz
    sub_pitch = np.linspace(90.0, 25.0, num_samples)
    sub = np.sin(2 * np.pi * sub_pitch * t)

    # Heavy blast noise
    noise = np.random.uniform(-1.0, 1.0, num_samples)

    # Exponential decay envelope
    envelope = np.exp(-t * 6.5)
    samples = (sub * 0.6 + noise * 0.5) * envelope
    return create_sound_from_array(samples)


def synth_shot(duration: float = 0.10) -> pygame.mixer.Sound:
    """Punchy visceral bio-projectile launch."""
    sr = AUDIO_SAMPLE_RATE
    num_samples = int(sr * duration)
    t = np.linspace(0, duration, num_samples, endpoint=False)

    pitch = np.linspace(420.0, 90.0, num_samples)
    carrier = np.sin(2 * np.pi * pitch * t)
    noise = np.random.uniform(-0.3, 0.3, num_samples)

    envelope = np.exp(-t * 30.0)
    samples = (carrier + noise) * envelope * 0.7
    return create_sound_from_array(samples)


def synth_bone_crack(duration: float = 0.08) -> pygame.mixer.Sound:
    """Sharp, snappy bone fracture impact."""
    sr = AUDIO_SAMPLE_RATE
    num_samples = int(sr * duration)
    t = np.linspace(0, duration, num_samples, endpoint=False)

    pitch = np.linspace(800.0, 150.0, num_samples)
    carrier = np.sin(2 * np.pi * pitch * t)
    noise = np.random.uniform(-0.8, 0.8, num_samples)

    envelope = np.exp(-t * 45.0)
    samples = (carrier * 0.4 + noise * 0.6) * envelope * 0.8
    return create_sound_from_array(samples)


def synth_pickup(duration: float = 0.18) -> pygame.mixer.Sound:
    """Bioluminescent cellular absorption chime."""
    sr = AUDIO_SAMPLE_RATE
    num_samples = int(sr * duration)
    t = np.linspace(0, duration, num_samples, endpoint=False)

    # Harmonic chord (A440 + C#554 + E659)
    chord = (
        np.sin(2 * np.pi * 440.0 * t) * 0.4
        + np.sin(2 * np.pi * 554.3 * t) * 0.35
        + np.sin(2 * np.pi * 659.2 * t) * 0.3
    )
    envelope = np.exp(-t * 12.0)
    samples = chord * envelope * 0.5
    return create_sound_from_array(samples)
