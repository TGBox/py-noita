"""Unit tests for asynchronous chunk streaming, disk paging, and seed determinism."""

import os
from pathlib import Path
import shutil
import tempfile
import unittest
import numpy as np

from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import MAT_AIR, MAT_BONE, MAT_TISSUE
from py_noita.world.chunk import CHUNK_PIXEL_SIZE, WorldChunk
from py_noita.world.streamer import WorldStreamer


class TestChunkStreaming(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="py_noita_test_chunks_"))

    def tearDown(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_chunk_serialization_and_deserialization(self):
        """WorldChunk serializes to compressed binary and restores identical data."""
        chunk = WorldChunk(cx=3, cy=-2, size=64)
        chunk.grid[10, 15] = MAT_TISSUE
        chunk.grid[20, 25] = MAT_BONE
        chunk.life[10, 15] = 120
        chunk.color_var[20, 25] = 2

        payload = chunk.serialize()
        self.assertIsInstance(payload, bytes)
        self.assertGreater(len(payload), 10)

        restored = WorldChunk.deserialize(payload)
        self.assertEqual(restored.cx, 3)
        self.assertEqual(restored.cy, -2)
        self.assertEqual(restored.size, 64)
        np.testing.assert_array_equal(restored.grid, chunk.grid)
        np.testing.assert_array_equal(restored.life, chunk.life)
        np.testing.assert_array_equal(restored.color_var, chunk.color_var)

    def test_deterministic_generation_from_seed(self):
        """Identical world seeds produce identical chunks; different seeds differ."""
        streamer1 = WorldStreamer(seed=42891, save_dir=self.temp_dir / "s1")
        streamer2 = WorldStreamer(seed=42891, save_dir=self.temp_dir / "s2")
        streamer3 = WorldStreamer(seed=99999, save_dir=self.temp_dir / "s3")

        c1 = streamer1.generate_chunk_deterministic(2, 5)
        c2 = streamer2.generate_chunk_deterministic(2, 5)
        c3 = streamer3.generate_chunk_deterministic(2, 5)

        # c1 and c2 must be completely identical
        np.testing.assert_array_equal(c1.grid, c2.grid)

        # c3 must differ from c1
        self.assertFalse(np.array_equal(c1.grid, c3.grid))

        streamer1.shutdown()
        streamer2.shutdown()
        streamer3.shutdown()

    def test_streaming_and_memory_eviction(self):
        """Moving player pages in nearby chunks and evicts distant chunks to disk, keeping RAM low."""
        streamer = WorldStreamer(
            seed=12345,
            save_dir=self.temp_dir,
            active_chunk_radius=2,  # 5x5 = 25 active chunks
            max_loaded_chunks=40,
        )

        # Position at (0, 0)
        loaded_count, mem_kb = streamer.update_streaming(0.0, 0.0)
        self.assertGreaterEqual(loaded_count, 25)
        self.assertLess(mem_kb, 500000, "Memory must stay well under 500 MB (500,000 KB)!")

        # Mark a chunk dirty
        origin_chunk = streamer.loaded_chunks.get((0, 0))
        self.assertIsNotNone(origin_chunk)
        origin_chunk.grid[5, 5] = MAT_BONE
        origin_chunk.dirty = True

        # Teleport player far away to (2000, 2000)
        streamer.update_streaming(2000.0, 2000.0)

        # Old chunk (0, 0) should be evicted from memory
        self.assertNotIn((0, 0), streamer.loaded_chunks)

        # Flush background saves
        streamer.flush_all()

        # Teleport back to (0, 0): chunk should reload from disk with dirty changes preserved
        streamer.update_streaming(0.0, 0.0)
        reloaded = streamer.loaded_chunks.get((0, 0))
        self.assertIsNotNone(reloaded)
        self.assertEqual(reloaded.grid[5, 5], MAT_BONE, "Dirty changes must be preserved across disk paging!")

        streamer.shutdown()

    def test_sync_with_simulation_grid(self):
        """WorldStreamer can blit chunks to and read back from SimulationGrid."""
        streamer = WorldStreamer(seed=777, save_dir=self.temp_dir)
        grid = SimulationGrid(width=128, height=128)

        # Load chunks around (0, 0)
        streamer.update_streaming(32.0, 32.0)
        streamer.sync_to_grid(grid, origin_cx=0, origin_cy=0)

        # Modify pixel in simulation grid
        grid.set_pixel(10, 10, MAT_TISSUE)
        streamer.sync_from_grid(grid, origin_cx=0, origin_cy=0)

        # Chunk (0, 0) must now have MAT_TISSUE at (10, 10)
        chunk0 = streamer.loaded_chunks[(0, 0)]
        self.assertEqual(chunk0.grid[10, 10], MAT_TISSUE)
        self.assertTrue(chunk0.dirty)

        streamer.shutdown()


if __name__ == "__main__":
    unittest.main()
