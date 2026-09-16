"""Global configuration constants for Py-Noita."""

from dataclasses import dataclass
from typing import Tuple


# Display Resolutions
RES_FULL_HD: Tuple[int, int] = (1920, 1080)
RES_ULTRAWIDE: Tuple[int, int] = (2560, 1080)
RES_WINDOWED_1080: Tuple[int, int] = (1280, 720)
RES_WINDOWED_UW: Tuple[int, int] = (1680, 720)

# Pixel Scale Factor: 1 simulation pixel = PIXEL_SCALE screen pixels
PIXEL_SCALE: int = 3

# Viewport simulation grid size (~30-40% wider field of view)
# For Full HD (1920x1080): 640 x 360 (exact 3x integer scale)
# For 1440p (2560x1440): exact 4x integer scale
# For 4K (3840x2160): exact 6x integer scale
VIEWPORT_SIM_WIDTH_16_9: int = 640
VIEWPORT_SIM_WIDTH_21_9: int = 854
VIEWPORT_SIM_HEIGHT: int = 360

# World / Biome dimensions (in simulation pixels)
WORLD_WIDTH: int = 1280        # Generous horizontal exploration space (40 chunks)
WORLD_HEIGHT: int = 1800       # Deep vertical subterranean descent (56 chunks)

# Simulation performance settings
CHUNK_SIZE: int = 32           # Chunks of 32x32 pixels for active dirty tracking
TARGET_FPS: int = 60
PHYSICS_TICKS_PER_SEC: int = 60
GRAVITY: float = 0.28          # Gravitational acceleration per tick for particles/fluids

# Player Settings
PLAYER_MAX_HP: float = 100.0
PLAYER_MAX_LEVITATION: float = 100.0
PLAYER_LEVITATION_RECHARGE: float = 2.2    # Fully recharges in ~0.75-0.8s on ground
PLAYER_LEVITATION_DRAIN: float = 0.85
PLAYER_MOVE_SPEED: float = 1.4
PLAYER_HOVER_IMPULSE: float = 0.38
PLAYER_WIDTH: int = 8          # in simulation pixels
PLAYER_HEIGHT: int = 12        # in simulation pixels

# Audio Settings
AUDIO_SAMPLE_RATE: int = 44100
AUDIO_CHANNELS: int = 2
AUDIO_BUFFER_SIZE: int = 512

# Colors for UI & Lighting (RGB)
COLOR_BG_DARK = (14, 10, 18)
COLOR_ACID_GLOW = (80, 255, 40)
COLOR_BIOGAS_GLOW = (255, 120, 20)
COLOR_MUTAGEN_GLOW = (200, 30, 240)
COLOR_NERVE_GLOW = (50, 210, 255)
COLOR_BLOOD_GLOW = (180, 20, 20)
COLOR_PLAYER_GLOW = (240, 230, 200)
