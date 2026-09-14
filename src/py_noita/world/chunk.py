"""World chunk representation with fast binary compression and serialization."""

import os
import struct
import zlib
from typing import Any, List, Optional, Tuple
import numpy as np

CHUNK_PIXEL_SIZE = 64  # 64x64 pixels per chunk


class WorldChunk:
    """A 64x64 tile chunk of the cellular organ world."""

    def __init__(
        self,
        cx: int,
        cy: int,
        size: int = CHUNK_PIXEL_SIZE,
        grid: Optional[np.ndarray] = None,
        life: Optional[np.ndarray] = None,
        color_var: Optional[np.ndarray] = None,
    ):
        self.cx = cx
        self.cy = cy
        self.size = size
        self.dirty: bool = False
        self.generated: bool = False

        if grid is not None:
            self.grid = grid.copy()
        else:
            self.grid = np.zeros((size, size), dtype=np.uint8)

        if life is not None:
            self.life = life.copy()
        else:
            self.life = np.zeros((size, size), dtype=np.uint16)

        if color_var is not None:
            self.color_var = color_var.copy()
        else:
            self.color_var = np.zeros((size, size), dtype=np.uint8)

    @property
    def world_x(self) -> int:
        return self.cx * self.size

    @property
    def world_y(self) -> int:
        return self.cy * self.size

    def serialize(self) -> bytes:
        """Compress chunk voxel data into a compact binary payload."""
        header = struct.pack("<4siiH", b"PNCK", self.cx, self.cy, self.size)
        raw_data = (
            self.grid.tobytes() + self.life.tobytes() + self.color_var.tobytes()
        )
        compressed = zlib.compress(raw_data, level=6)
        return header + compressed

    @classmethod
    def deserialize(cls, data: bytes) -> "WorldChunk":
        """Unpack binary payload back into a WorldChunk instance."""
        header_len = struct.calcsize("<4siiH")
        magic, cx, cy, size = struct.unpack("<4siiH", data[:header_len])
        if magic != b"PNCK":
            raise ValueError(f"Invalid chunk header magic: {magic}")

        decompressed = zlib.decompress(data[header_len:])
        grid_bytes = size * size
        life_bytes = size * size * 2
        color_bytes = size * size

        grid = np.frombuffer(decompressed[:grid_bytes], dtype=np.uint8).reshape(
            (size, size)
        )
        life = np.frombuffer(
            decompressed[grid_bytes : grid_bytes + life_bytes], dtype=np.uint16
        ).reshape((size, size))
        color_var = np.frombuffer(
            decompressed[grid_bytes + life_bytes : grid_bytes + life_bytes + color_bytes],
            dtype=np.uint8,
        ).reshape((size, size))

        chunk = cls(cx, cy, size=size, grid=grid, life=life, color_var=color_var)
        chunk.generated = True
        return chunk
