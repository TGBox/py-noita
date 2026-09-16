"""Unit tests for GLSL Post-Processing Shaders & VFX Pipeline."""

import unittest
import numpy as np
import pygame

from py_noita.rendering.renderer import Renderer
from py_noita.rendering.shaders import (
    GLSL_FRAGMENT_SHADER,
    GLSL_VERTEX_SHADER,
    ShaderPostProcessor,
    ShockwaveInstance,
)


class TestShadersAndPostProcessing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_shader_initialization_and_glsl_sources(self):
        """Test shader post-processor setup and GLSL shader definitions."""
        processor = ShaderPostProcessor(width=320, height=180)
        self.assertEqual(processor.width, 320)
        self.assertEqual(processor.height, 180)
        self.assertIn("u_heat_intensity", GLSL_FRAGMENT_SHADER)
        self.assertIn("u_acid_distortion", GLSL_FRAGMENT_SHADER)
        self.assertIn("u_shockwave_radius", GLSL_FRAGMENT_SHADER)
        self.assertIn("u_chromatic_aberration", GLSL_FRAGMENT_SHADER)
        self.assertIn("u_low_hp_pulse", GLSL_FRAGMENT_SHADER)

    def test_heat_shimmer_and_acid_distortion(self):
        """Test heat shimmer and acid refraction apply non-identity distortion."""
        processor = ShaderPostProcessor(width=64, height=64)
        processor.update(dt=0.016, heat_val=0.8, acid_val=0.7)
        self.assertAlmostEqual(processor.heat_intensity, 0.8)
        self.assertAlmostEqual(processor.acid_distortion, 0.7)

        # Create checkerboard pattern
        surf = pygame.Surface((64, 64))
        surf.fill((100, 100, 100))
        for y in range(0, 64, 4):
            for x in range(0, 64, 4):
                surf.set_at((x, y), (200, 200, 200))

        out_surf = processor.apply_post_processing(surf)
        self.assertEqual(out_surf.get_size(), (64, 64))
        # Surface must be modified by distortion
        orig_arr = pygame.surfarray.array3d(surf)
        out_arr = pygame.surfarray.array3d(out_surf)
        self.assertFalse(np.array_equal(orig_arr, out_arr))

    def test_detonation_shockwave_and_chromatic_aberration(self):
        """Test shockwave creation, radius expansion, and chromatic aberration decay."""
        processor = ShaderPostProcessor(width=100, height=100)
        processor.add_shockwave(uv_x=0.5, uv_y=0.5, intensity=1.0)
        self.assertEqual(len(processor.shockwaves), 1)
        self.assertGreater(processor.chromatic_aberration, 0.5)

        # Step time
        sw = processor.shockwaves[0]
        initial_radius = sw.radius
        processor.update(dt=0.1)

        self.assertGreater(sw.radius, initial_radius)
        self.assertLess(sw.intensity, 1.0)

    def test_visceral_low_hp_vignette(self):
        """Test low HP activates visceral red vignette pulse."""
        processor = ShaderPostProcessor(width=80, height=80)
        # HP at 10%
        processor.update(dt=0.2, player_hp_ratio=0.1)
        self.assertGreater(processor.low_hp_pulse, 0.0)

        # Uniform white surface
        surf = pygame.Surface((80, 80))
        surf.fill((255, 255, 255))

        out_surf = processor.apply_post_processing(surf)
        # Corner pixel (0, 0) should be darker and redder than center pixel (40, 40)
        corner_color = out_surf.get_at((0, 0))
        center_color = out_surf.get_at((40, 40))

        # Center stays bright, corner receives vignette darkening/red tint
        self.assertLess(corner_color.g, center_color.g)
        self.assertLess(corner_color.b, center_color.b)

    def test_renderer_present_with_post_processor(self):
        """Renderer applies post-processing seamlessly during present."""
        renderer = Renderer(screen_res=(320, 180))
        self.assertIsNotNone(renderer.post_processor)

        screen = pygame.Surface((320, 180))
        renderer.sim_surface.fill((50, 80, 120))
        renderer.post_processor.add_shockwave(0.5, 0.5, 0.5)
        renderer.present(screen)
        # Screen should receive rendered pixels
        center = screen.get_at((160, 90))
        self.assertGreater(center.b, 0)

    def test_renderer_present_with_resized_destination_surface(self):
        """Renderer handles destination surface resized by OS (e.g. window borders) without ValueError."""
        renderer = Renderer(screen_res=(2560, 1080))
        # Simulated OS-resized window (e.g. 2560x1017)
        resized_screen = pygame.Surface((2560, 1017))
        renderer.sim_surface.fill((40, 60, 80))
        
        # Must not throw ValueError
        renderer.present(resized_screen)
        self.assertEqual(renderer.screen_res, (2560, 1017))
        self.assertEqual(renderer.dest_rect.height, 1017)
        self.assertLessEqual(renderer.dest_rect.width, 2560)


if __name__ == "__main__":
    unittest.main()
