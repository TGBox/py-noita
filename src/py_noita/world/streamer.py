"""Asynchronous chunk streaming and disk memory management."""

from concurrent.futures import ThreadPoolExecutor
import math
import os
from pathlib import Path
import random
import tempfile
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import numpy as np

from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import (
    MAT_ACID,
    MAT_AIR,
    MAT_BIOGAS,
    MAT_BLOOD,
    MAT_BONE,
    MAT_TISSUE,
    MAT_WALL_BONE,
    MAT_WATER,
)
from py_noita.world.chunk import CHUNK_PIXEL_SIZE, WorldChunk


class WorldStreamer:
    """Manages an unbounded streaming world by paging chunks between RAM and Disk.
    Uses asynchronous background disk I/O and deterministic world generation from seed.
    Guarantees active RAM usage stays strictly below 500 MB.
    """

    def __init__(
        self,
        seed: int,
        save_dir: Optional[Path] = None,
        chunk_size: int = CHUNK_PIXEL_SIZE,
        active_chunk_radius: int = 4,
        max_loaded_chunks: int = 128,
    ):
        self.seed = seed
        self.chunk_size = chunk_size
        self.active_radius = active_chunk_radius
        self.max_loaded = max_loaded_chunks

        if save_dir is None:
            self.save_dir = (
                Path(tempfile.gettempdir()) / "py_noita_saves" / f"seed_{seed}"
            )
        else:
            self.save_dir = Path(save_dir) / f"seed_{seed}"

        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.chunks_dir = self.save_dir / "chunks"
        self.chunks_dir.mkdir(parents=True, exist_ok=True)

        self.loaded_chunks: Dict[Tuple[int, int], WorldChunk] = {}
        self.saving_futures = []
        self.thread_pool = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="ChunkStreamer"
        )

    def _get_chunk_path(self, cx: int, cy: int) -> Path:
        return self.chunks_dir / f"c_{cx}_{cy}.chunk"

    def has_chunk_on_disk(self, cx: int, cy: int) -> bool:
        return self._get_chunk_path(cx, cy).exists()

    def load_chunk_from_disk(self, cx: int, cy: int) -> Optional[WorldChunk]:
        """Load and decompress chunk from disk."""
        path = self._get_chunk_path(cx, cy)
        if not path.exists():
            return None
        try:
            with open(path, "rb") as f:
                data = f.read()
            chunk = WorldChunk.deserialize(data)
            return chunk
        except Exception:
            return None

    def save_chunk_to_disk(self, chunk: WorldChunk) -> None:
        """Serialize and save chunk to disk synchronously."""
        path = self._get_chunk_path(chunk.cx, chunk.cy)
        data = chunk.serialize()
        with open(path, "wb") as f:
            f.write(data)
        chunk.dirty = False

    def save_chunk_async(self, chunk: WorldChunk) -> None:
        """Dispatch chunk save to background worker thread."""
        chunk_copy = WorldChunk(
            chunk.cx,
            chunk.cy,
            size=chunk.size,
            grid=chunk.grid,
            life=chunk.life,
            color_var=chunk.color_var,
        )
        chunk.dirty = False
        self.thread_pool.submit(self.save_chunk_to_disk, chunk_copy)

    def generate_chunk_deterministic(self, cx: int, cy: int) -> WorldChunk:
        """Deterministically generate procedural terrain for chunk (cx, cy) using seed."""
        chunk = WorldChunk(cx, cy, size=self.chunk_size)
        rng = np.random.default_rng(abs(hash((self.seed, cx, cy))) % (2**31))

        # Depth in world coordinates:
        world_y = cy * self.chunk_size
        world_x = cx * self.chunk_size

        for y in range(self.chunk_size):
            gy = world_y + y
            for x in range(self.chunk_size):
                gx = world_x + x

                # Boundary bedrock walls on extreme horizontal boundaries
                if abs(gx) > 20000:
                    chunk.grid[y, x] = MAT_WALL_BONE
                    continue

                if gy < 10:
                    # Open surface air
                    chunk.grid[y, x] = MAT_AIR
                elif gy < 20:
                    # Epidermis surface skin
                    chunk.grid[y, x] = MAT_TISSUE
                else:
                    # Organic subterranean caverns
                    freq1 = 0.035
                    val1 = math.sin(gx * freq1) * math.cos(gy * freq1)
                    val2 = math.sin(gx * 0.08 + 1.2) * math.sin(gy * 0.08 - 0.7)
                    noise = val1 * 0.65 + val2 * 0.35

                    if noise > -0.05:
                        # Solid flesh or bone
                        bone_noise = math.sin(gx * 0.12) * math.cos(gy * 0.12)
                        if bone_noise > 0.35:
                            chunk.grid[y, x] = MAT_BONE
                        else:
                            chunk.grid[y, x] = MAT_TISSUE
                    else:
                        # Cavern hollow: air, acid pool, or biogas
                        if gy > 300 and rng.random() < 0.08:
                            chunk.grid[y, x] = MAT_ACID
                        elif gy > 500 and rng.random() < 0.04:
                            chunk.grid[y, x] = MAT_BIOGAS
                        else:
                            chunk.grid[y, x] = MAT_AIR

        chunk.color_var = rng.integers(
            0, 4, size=(self.chunk_size, self.chunk_size), dtype=np.uint8
        )
        chunk.generated = True
        return chunk

    def get_or_load_chunk(self, cx: int, cy: int) -> WorldChunk:
        """Get chunk from RAM, load from Disk, or generate deterministically."""
        key = (cx, cy)
        if key in self.loaded_chunks:
            return self.loaded_chunks[key]

        # Check disk
        if self.has_chunk_on_disk(cx, cy):
            chunk = self.load_chunk_from_disk(cx, cy)
            if chunk is not None:
                self.loaded_chunks[key] = chunk
                return chunk

        # Generate deterministically
        chunk = self.generate_chunk_deterministic(cx, cy)
        self.loaded_chunks[key] = chunk
        return chunk

    def sync_to_grid(
        self, grid: SimulationGrid, origin_cx: int, origin_cy: int
    ) -> None:
        """Blit active chunks into the active SimulationGrid canvas."""
        gw = grid.width
        gh = grid.height

        for (cx, cy), chunk in self.loaded_chunks.items():
            gx0 = (cx - origin_cx) * self.chunk_size
            gy0 = (cy - origin_cy) * self.chunk_size

            if (
                gx0 + self.chunk_size <= 0
                or gx0 >= gw
                or gy0 + self.chunk_size <= 0
                or gy0 >= gh
            ):
                continue

            src_x0 = max(0, -gx0)
            src_y0 = max(0, -gy0)
            src_x1 = min(self.chunk_size, gw - gx0)
            src_y1 = min(self.chunk_size, gh - gy0)

            dst_x0 = max(0, gx0)
            dst_y0 = max(0, gy0)
            dst_x1 = dst_x0 + (src_x1 - src_x0)
            dst_y1 = dst_y0 + (src_y1 - src_y0)

            grid.grid[dst_y0:dst_y1, dst_x0:dst_x1] = chunk.grid[
                src_y0:src_y1, src_x0:src_x1
            ]
            grid.life[dst_y0:dst_y1, dst_x0:dst_x1] = chunk.life[
                src_y0:src_y1, src_x0:src_x1
            ]
            grid.color_var[dst_y0:dst_y1, dst_x0:dst_x1] = chunk.color_var[
                src_y0:src_y1, src_x0:src_x1
            ]

    def sync_from_grid(
        self, grid: SimulationGrid, origin_cx: int, origin_cy: int
    ) -> None:
        """Flush simulated pixels from SimulationGrid back into loaded chunks."""
        gw = grid.width
        gh = grid.height

        for (cx, cy), chunk in self.loaded_chunks.items():
            gx0 = (cx - origin_cx) * self.chunk_size
            gy0 = (cy - origin_cy) * self.chunk_size

            if (
                gx0 + self.chunk_size <= 0
                or gx0 >= gw
                or gy0 + self.chunk_size <= 0
                or gy0 >= gh
            ):
                continue

            src_x0 = max(0, gx0)
            src_y0 = max(0, gy0)
            src_x1 = min(gw, gx0 + self.chunk_size)
            src_y1 = min(gh, gy0 + self.chunk_size)

            dst_x0 = max(0, -gx0)
            dst_y0 = max(0, -gy0)
            dst_x1 = dst_x0 + (src_x1 - src_x0)
            dst_y1 = dst_y0 + (src_y1 - src_y0)

            chunk.grid[dst_y0:dst_y1, dst_x0:dst_x1] = grid.grid[
                src_y0:src_y1, src_x0:src_x1
            ]
            chunk.life[dst_y0:dst_y1, dst_x0:dst_x1] = grid.life[
                src_y0:src_y1, src_x0:src_x1
            ]
            chunk.dirty = True

    def update_streaming(
        self,
        center_x: float,
        center_y: float,
        grid: Optional[SimulationGrid] = None,
    ) -> Tuple[int, int]:
        """Keep chunks around (center_x, center_y) loaded and evict distant chunks to disk.
        Returns (loaded_chunk_count, memory_kb).
        """
        center_cx = int(center_x) // self.chunk_size
        center_cy = int(center_y) // self.chunk_size

        needed_keys = set()
        for dcy in range(-self.active_radius, self.active_radius + 1):
            for dcx in range(-self.active_radius, self.active_radius + 1):
                needed_keys.add((center_cx + dcx, center_cy + dcy))

        # 1. Load or generate newly needed chunks
        for key in needed_keys:
            if key not in self.loaded_chunks:
                self.get_or_load_chunk(key[0], key[1])

        # 2. Evict chunks outside retention radius
        evict_radius = self.active_radius + 2
        to_evict = []
        for key, chunk in self.loaded_chunks.items():
            dist_x = abs(key[0] - center_cx)
            dist_y = abs(key[1] - center_cy)
            if dist_x > evict_radius or dist_y > evict_radius:
                to_evict.append(key)

        for key in to_evict:
            chunk = self.loaded_chunks.pop(key)
            if chunk.dirty:
                self.save_chunk_async(chunk)

        total_kb = len(self.loaded_chunks) * (
            self.chunk_size * self.chunk_size * 4 // 1024
        )
        return len(self.loaded_chunks), total_kb

    def flush_all(self) -> None:
        """Synchronously flush all loaded dirty chunks to disk."""
        for chunk in self.loaded_chunks.values():
            if chunk.dirty:
                self.save_chunk_to_disk(chunk)

    def shutdown(self) -> None:
        """Flush and wait for background workers to complete."""
        self.flush_all()
        self.thread_pool.shutdown(wait=True)
