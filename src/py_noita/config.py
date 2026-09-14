"""Global configuration constants for Py-Noita."""

from dataclasses import dataclass
from typing import Tuple


# Display Resolutions
RES_FULL_HD: Tuple[int, int] = (1920, 1080)
RES_ULTRAWIDE: Tuple[int, int] = (2560, 1080)
RES_WINDOWED_1080: Tuple[int, int] = (1280, 720)
RES_WINDOWED_UW: Tuple[int, int] = (1680, 720)

# Pixel Scale Factor: 1 simulation pixel = PIXEL_SCALE screen pixels
PIXEL_SCALE: int = 4

# Viewport simulation grid size (calculated from screen res // PIXEL_SCALE)
# For Full HD (1920x1080): 480 x 270
VIEWPORT_SIM_WIDTH_16_9: int = 1920 // PIXEL_SCALE   # 480
VIEWPORT_SIM_WIDTH_21_9: int = 2560 // PIXEL_SCALE   # 640
VIEWPORT_SIM_HEIGHT: int = 1080 // PIXEL_SCALE       # 270

# World / Biome dimensions (in simulation pixels)
WORLD_WIDTH: int = 960         # 2 full screens wide in 16:9
WORLD_HEIGHT: int = 1620       # 6 full screens deep in 16:9

# Simulation performance settings
CHUNK_SIZE: int = 32           # Chunks of 32x32 pixels for active dirty tracking
TARGET_FPS: int = 60
PHYSICS_TICKS_PER_SEC: int = 60
GRAVITY: float = 0.28          # Gravitational acceleration per tick for particles/fluids

# Player Settings
PLAYER_MAX_HP: float = 100.0
PLAYER_MAX_LEVITATION: float = 100.0
PLAYER_LEVITATION_RECHARGE: float = 0.55
PLAYER_LEVITATION_DRAIN: float = 0.85
PLAYER_MOVE_SPEED: float = 1.4
PLAYER_HOVER_IMPULSE: float = 0.35
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
