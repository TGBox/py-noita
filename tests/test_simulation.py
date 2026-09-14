"""Automated unit tests and benchmark for Py-Noita simulation engine."""

import time
import unittest
import numpy as np

from py_noita.simulation.materials import (
    MAT_AIR,
    MAT_TISSUE,
    MAT_BONE,
    MAT_ACID,
    MAT_BLOOD,
    MAT_LYMPH,
    MAT_WATER,
    MAT_MUTAGEN,
    MAT_TENTACLE_FLESH,
    MAT_BIOGAS,
    MAT_FIRE,
    MAT_SPORES,
    MAT_CORROSION,
)
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.explosion import create_explosion


class TestSimulation(unittest.TestCase):
    def setUp(self):
        # 120x80 test grid
        self.grid = SimulationGrid(width=120, height=80)

    def test_powder_falls(self):
        """Verify powder particles fall down under gravity."""
        # Place spores at (60, 20)
        self.grid.set_pixel(60, 20, MAT_SPORES)

        # Run 20 simulation steps
        for _ in range(20):
            self.grid.update(cam_x=0, cam_y=0, view_w=120, view_h=80)

        # Spores should have fallen significantly below y=20
        spore_positions = np.argwhere(self.grid.grid == MAT_SPORES)
        self.assertGreater(len(spore_positions), 0)
        final_y = spore_positions[0][0]
        self.assertGreater(final_y, 25, f"Spores did not fall: final y={final_y}")

    def test_liquid_spreads_horizontally(self):
        """Verify liquids fall and disperse sideways."""
        # Create a floor at y=60
        self.grid.fill_rect(20, 60, 80, 5, MAT_TISSUE)
        # Drop a vertical column of blood
        for y in range(40, 58):
            self.grid.set_pixel(60, y, MAT_BLOOD)

        # Step simulation 30 times
        for _ in range(30):
            self.grid.update(cam_x=0, cam_y=0, view_w=120, view_h=80)

        # Blood should have spread across multiple columns
        blood_positions = np.argwhere(self.grid.grid == MAT_BLOOD)
        self.assertGreater(len(blood_positions), 0)
        x_coords = blood_positions[:, 1]
        spread = x_coords.max() - x_coords.min()
        self.assertGreater(spread, 3, f"Liquid did not disperse sideways: spread={spread}")

    def test_acid_dissolves_tissue_and_creates_biogas(self):
        """Verify acid dissolves tissue and creates corrosion/biogas."""
        # Create tissue block
        self.grid.fill_rect(40, 40, 40, 20, MAT_TISSUE)
        # Pour acid on top
        for x in range(50, 65):
            self.grid.set_pixel(x, 39, MAT_ACID)

        # Step simulation 25 times
        for _ in range(25):
            self.grid.update(cam_x=0, cam_y=0, view_w=120, view_h=80)

        # Check for corrosion foam, toxic vapor, or biogas
        corrosion_count = np.sum(self.grid.grid == MAT_CORROSION)
        gas_count = np.sum(self.grid.grid == MAT_BIOGAS)
        air_eaten = np.sum(self.grid.grid[40:45, 50:65] == MAT_AIR)

        self.assertTrue(
            corrosion_count > 0 or gas_count > 0 or air_eaten > 0,
            "Acid failed to react with tissue!",
        )

    def test_lymph_neutralizes_acid(self):
        """Verify lymph and acid neutralize each other into water."""
        self.grid.set_pixel(50, 40, MAT_ACID)
        self.grid.set_pixel(50, 41, MAT_LYMPH)

        for _ in range(5):
            self.grid.update(cam_x=0, cam_y=0, view_w=120, view_h=80)

        # Should produce water
        water_count = np.sum(self.grid.grid == MAT_WATER)
        self.assertGreater(water_count, 0, "Lymph did not neutralize acid into water!")

    def test_mutagen_alchemizes_tissue(self):
        """Verify mutagen turns tissue into tentacle flesh."""
        self.grid.fill_rect(45, 45, 10, 10, MAT_TISSUE)
        for x in range(45, 55):
            self.grid.set_pixel(x, 44, MAT_MUTAGEN)

        for _ in range(30):
            self.grid.update(cam_x=0, cam_y=0, view_w=120, view_h=80)

        tentacle_count = np.sum(self.grid.grid == MAT_TENTACLE_FLESH)
        self.assertGreater(tentacle_count, 0, "Mutagen did not transform tissue!")

    def test_explosion_carves_crater(self):
        """Verify explosion carves out a crater and flings debris."""
        # Solid tissue block
        self.grid.fill_rect(30, 30, 60, 40, MAT_TISSUE)
        initial_tissue = np.sum(self.grid.grid == MAT_TISSUE)

        # Detonate at (60, 50)
        damaged, debris = create_explosion(self.grid, 60, 50, radius=12)

        final_tissue = np.sum(self.grid.grid == MAT_TISSUE)
        self.assertGreater(damaged, 50, f"Explosion did not damage enough cells: {damaged}")
        self.assertLess(final_tissue, initial_tissue, "Tissue count was not reduced!")
        self.assertTrue(len(debris) > 0, "Explosion did not produce debris particles!")

    def test_simulation_benchmark_60fps(self):
        """Verify simulation step execution time is well under 16ms (60+ FPS)."""
        # Populate grid with 2,000 active particles (acid, blood, spores, tissue)
        self.grid.fill_rect(20, 50, 80, 20, MAT_TISSUE)
        for _ in range(1000):
            rx = np.random.randint(25, 95)
            ry = np.random.randint(10, 45)
            rmat = np.random.choice([MAT_ACID, MAT_BLOOD, MAT_SPORES])
            self.grid.set_pixel(rx, ry, rmat)

        # Warmup JIT
        self.grid.update(cam_x=0, cam_y=0, view_w=120, view_h=80)

        # Benchmark 60 steps
        start = time.perf_counter()
        steps = 60
        for _ in range(steps):
            self.grid.update(cam_x=0, cam_y=0, view_w=120, view_h=80)
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / steps) * 1000.0
        print(f"\n[BENCHMARK] Average simulation step: {avg_ms:.2f} ms ({1000.0/avg_ms:.1f} FPS)")
        self.assertLess(avg_ms, 16.67, f"Simulation step too slow for 60 FPS: {avg_ms:.2f} ms")


if __name__ == "__main__":
    unittest.main()
