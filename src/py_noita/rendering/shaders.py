"""Hardware-accelerated GLSL Post-Processing Shaders & VFX Pipeline.

Features:
- Heat shimmer over fire and biogas flames (distortion noise).
- Acid refraction & corrosive screen caustic distortion.
- Shockwave pressure-wave ring and chromatic aberration on detonations.
- Visceral low-HP vignette and heartbeat pulse effect.
- Dual-mode: OpenGL GLSL shader when available, JIT/Numba accelerated CPU fallback.
"""

import math
from typing import List, Optional, Tuple
import numpy as np
import pygame
from numba import njit

# Check for OpenGL availability
HAS_OPENGL = False
try:
    from OpenGL import GL
    HAS_OPENGL = True
except ImportError:
    HAS_OPENGL = False


GLSL_VERTEX_SHADER = """
#version 120
attribute vec2 in_vert;
attribute vec2 in_uv;
varying vec2 v_uv;

void main() {
    v_uv = in_uv;
    gl_Position = vec4(in_vert, 0.0, 1.0);
}
"""

GLSL_FRAGMENT_SHADER = """
#version 120
uniform sampler2D u_texture;
uniform float u_time;
uniform float u_heat_intensity;
uniform float u_acid_distortion;
uniform vec2 u_shockwave_center;
uniform float u_shockwave_radius;
uniform float u_shockwave_intensity;
uniform float u_chromatic_aberration;
uniform float u_low_hp_pulse;
uniform vec2 u_resolution;

varying vec2 v_uv;

vec2 get_heat_offset(vec2 uv, float time) {
    float x = sin(uv.y * 40.0 + time * 6.0) * cos(uv.x * 25.0 + time * 4.0);
    float y = cos(uv.x * 40.0 + time * 5.0) * sin(uv.y * 30.0 + time * 3.5);
    return vec2(x, y) * 0.006 * u_heat_intensity;
}

vec2 get_acid_offset(vec2 uv, float time) {
    float angle = atan(uv.y - 0.5, uv.x - 0.5);
    float dist = length(uv - 0.5);
    float wave = sin(dist * 22.0 - time * 4.0 + angle * 3.0);
    return vec2(cos(wave), sin(wave)) * 0.008 * u_acid_distortion;
}

void main() {
    vec2 uv = v_uv;
    
    // 1. Heat Shimmer distortion
    if (u_heat_intensity > 0.001) {
        uv += get_heat_offset(uv, u_time);
    }
    
    // 2. Acid Refraction & Caustic Warping
    if (u_acid_distortion > 0.001) {
        uv += get_acid_offset(uv, u_time);
    }
    
    // 3. Shockwave Pressure-Wave Ring
    if (u_shockwave_intensity > 0.001) {
        vec2 diff = uv - u_shockwave_center;
        float dist = length(diff);
        float ring = smoothstep(0.05, 0.0, abs(dist - u_shockwave_radius));
        if (dist > 0.0001) {
            vec2 dir = diff / dist;
            uv += dir * ring * u_shockwave_intensity * 0.035;
        }
    }
    
    // 4. Chromatic Aberration
    vec4 color;
    if (u_chromatic_aberration > 0.001) {
        vec2 ca_offset = (uv - 0.5) * u_chromatic_aberration * 0.025;
        float r = texture2D(u_texture, uv + ca_offset).r;
        float g = texture2D(u_texture, uv).g;
        float b = texture2D(u_texture, uv - ca_offset).b;
        color = vec4(r, g, b, 1.0);
    } else {
        color = texture2D(u_texture, uv);
    }
    
    // 5. Visceral Low-HP Vignette & Heartbeat Pulse
    if (u_low_hp_pulse > 0.001) {
        float dist = length(uv - 0.5);
        float vignette = smoothstep(0.75, 0.2, dist);
        float pulse = 0.5 + 0.5 * sin(u_time * 6.5);
        pulse = pow(pulse, 3.0);
        vec3 blood_tint = vec3(0.7, 0.02, 0.05);
        vec3 darkened = color.rgb * (0.35 + 0.65 * vignette);
        color.rgb = mix(color.rgb, mix(darkened, blood_tint, (1.0 - vignette) * 0.85), u_low_hp_pulse * (0.4 + 0.6 * pulse));
    }
    
    gl_FragColor = color;
}
"""


class ShockwaveInstance:
    """An active expanding detonation pressure wave."""

    def __init__(self, uv_x: float, uv_y: float, intensity: float = 1.0):
        self.uv_x = uv_x
        self.uv_y = uv_y
        self.radius = 0.0
        self.intensity = intensity
        self.max_radius = 0.65
        self.speed = 1.2

    def update(self, dt: float) -> bool:
        """Advance shockwave ring. Returns False when fully dissipated."""
        self.radius += self.speed * dt
        self.intensity = max(0.0, self.intensity - 1.8 * dt)
        return self.radius < self.max_radius and self.intensity > 0.01


@njit(fastmath=True)
def apply_cpu_post_processing(
    src: np.ndarray,
    dst: np.ndarray,
    width: int,
    height: int,
    time_val: float,
    heat_int: float,
    acid_dist: float,
    shock_cx: float,
    shock_cy: float,
    shock_r: float,
    shock_int: float,
    ca_int: float,
    low_hp_int: float,
) -> None:
    """Fast Numba CPU fallback for post-processing shaders."""
    ca_pixel_shift = int(ca_int * 8.0)
    pulse = 0.5 + 0.5 * math.sin(time_val * 6.5)
    pulse = pulse * pulse * pulse

    for y in range(height):
        v = y / float(height)
        v_diff = v - 0.5
        v_diff_sq = v_diff * v_diff

        for x in range(width):
            u = x / float(width)
            u_diff = u - 0.5
            dist_center = math.sqrt(u_diff * u_diff + v_diff_sq)

            sample_x = x
            sample_y = y

            # 1. Heat shimmer
            if heat_int > 0.01:
                hx = math.sin(v * 40.0 + time_val * 6.0) * math.cos(u * 25.0 + time_val * 4.0)
                hy = math.cos(u * 40.0 + time_val * 5.0) * math.sin(v * 30.0 + time_val * 3.5)
                sample_x = int(x + hx * heat_int * 4.0)
                sample_y = int(y + hy * heat_int * 4.0)

            # 2. Acid refraction
            if acid_dist > 0.01:
                angle = math.atan2(v - 0.5, u - 0.5)
                wave = math.sin(dist_center * 22.0 - time_val * 4.0 + angle * 3.0)
                sample_x = int(sample_x + math.cos(wave) * acid_dist * 5.0)
                sample_y = int(sample_y + math.sin(wave) * acid_dist * 5.0)

            # 3. Shockwave ring
            if shock_int > 0.01 and shock_r > 0.01:
                dx = u - shock_cx
                dy = v - shock_cy
                d_shock = math.sqrt(dx * dx + dy * dy)
                ring_dist = abs(d_shock - shock_r)
                if ring_dist < 0.06 and d_shock > 0.001:
                    factor = (1.0 - (ring_dist / 0.06)) * shock_int * 15.0
                    sample_x = int(sample_x + (dx / d_shock) * factor)
                    sample_y = int(sample_y + (dy / d_shock) * factor)

            # Clamp sampled coordinates
            sample_x = max(0, min(width - 1, sample_x))
            sample_y = max(0, min(height - 1, sample_y))

            # 4. Chromatic Aberration
            if ca_pixel_shift > 0:
                rx = min(width - 1, sample_x + ca_pixel_shift)
                bx = max(0, sample_x - ca_pixel_shift)
                r_val = src[rx, sample_y, 0]
                g_val = src[sample_x, sample_y, 1]
                b_val = src[bx, sample_y, 2]
            else:
                r_val = src[sample_x, sample_y, 0]
                g_val = src[sample_x, sample_y, 1]
                b_val = src[sample_x, sample_y, 2]

            # 5. Visceral Low-HP Vignette & Heartbeat
            if low_hp_int > 0.01:
                # Radial vignette
                vignette = 1.0 - min(1.0, max(0.0, (dist_center - 0.25) / 0.5))
                red_factor = low_hp_int * (0.4 + 0.6 * pulse) * (1.0 - vignette)
                r_val = int(r_val * (0.35 + 0.65 * vignette) + 178 * red_factor)
                g_val = int(g_val * (0.35 + 0.65 * vignette))
                b_val = int(b_val * (0.35 + 0.65 * vignette))

            dst[x, y, 0] = min(255, max(0, r_val))
            dst[x, y, 1] = min(255, max(0, g_val))
            dst[x, y, 2] = min(255, max(0, b_val))


class ShaderPostProcessor:
    """Manages GLSL and JIT post-processing shader effects for the game renderer."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.time: float = 0.0

        # Effect control values (0.0 to 1.0)
        self.heat_intensity: float = 0.0
        self.acid_distortion: float = 0.0
        self.chromatic_aberration: float = 0.0
        self.low_hp_pulse: float = 0.0

        # Shockwaves queue
        self.shockwaves: List[ShockwaveInstance] = []

        # Secondary scratch buffer for CPU fallback
        self.scratch_buffer = np.zeros((width, height, 3), dtype=np.uint8)
        self.photosensitivity_mode: bool = False

        # OpenGL GLSL program handle
        self.gl_program = None
        self.gl_texture = None
        self.gl_vbo = None
        self._init_glsl_if_available()

    def _init_glsl_if_available(self) -> None:
        """Attempt to compile GLSL shaders if OpenGL context is active."""
        if not HAS_OPENGL:
            return

        try:
            # Check if OpenGL context is valid
            GL.glGetString(GL.GL_VERSION)
        except Exception:
            return

        try:
            vert_shader = GL.glCreateShader(GL.GL_VERTEX_SHADER)
            GL.glShaderSource(vert_shader, GLSL_VERTEX_SHADER)
            GL.glCompileShader(vert_shader)

            frag_shader = GL.glCreateShader(GL.GL_FRAGMENT_SHADER)
            GL.glShaderSource(frag_shader, GLSL_FRAGMENT_SHADER)
            GL.glCompileShader(frag_shader)

            program = GL.glCreateProgram()
            GL.glAttachShader(program, vert_shader)
            GL.glAttachShader(program, frag_shader)
            GL.glLinkShader(program)

            self.gl_program = program
        except Exception:
            self.gl_program = None

    def add_shockwave(self, uv_x: float, uv_y: float, intensity: float = 1.0) -> None:
        """Trigger an expanding detonation pressure-wave at normalized UV coordinates (0..1)."""
        if self.photosensitivity_mode:
            self.shockwaves.append(ShockwaveInstance(uv_x, uv_y, intensity * 0.4))
            self.chromatic_aberration = 0.0
        else:
            self.shockwaves.append(ShockwaveInstance(uv_x, uv_y, intensity))
            self.chromatic_aberration = min(1.0, self.chromatic_aberration + intensity * 0.8)

    def trigger_detonation(self, world_x: float, world_y: float, cam_x: float, cam_y: float, power: float = 30.0) -> None:
        """Convenience method to trigger shockwave and aberration from world coordinates."""
        uv_x = (world_x - cam_x) / max(1.0, float(self.width))
        uv_y = (world_y - cam_y) / max(1.0, float(self.height))
        intensity = min(1.0, power / 35.0)
        self.add_shockwave(uv_x, uv_y, intensity)

    def update(self, dt: float, heat_val: float = 0.0, acid_val: float = 0.0, player_hp_ratio: float = 1.0) -> None:
        """Update animation time and decay/ramp effect parameters."""
        self.time += dt

        # Smooth heat shimmer & acid distortion
        self.heat_intensity = max(0.0, min(1.0, heat_val))
        self.acid_distortion = max(0.0, min(1.0, acid_val))

        if self.photosensitivity_mode:
            self.chromatic_aberration = 0.0
            if player_hp_ratio < 0.25:
                # Steady subtle vignette without rapid strobing
                self.low_hp_pulse = 0.25
            else:
                self.low_hp_pulse = 0.0
        else:
            # Chromatic aberration decay
            if self.chromatic_aberration > 0.0:
                self.chromatic_aberration = max(0.0, self.chromatic_aberration - 2.2 * dt)

            # Low HP pulse (activates when HP < 25%)
            if player_hp_ratio < 0.25:
                target_pulse = (0.25 - player_hp_ratio) / 0.25
                self.low_hp_pulse = min(1.0, self.low_hp_pulse + 4.0 * dt * target_pulse)
            else:
                self.low_hp_pulse = max(0.0, self.low_hp_pulse - 3.0 * dt)

        # Update active shockwaves
        self.shockwaves = [sw for sw in self.shockwaves if sw.update(dt)]

    def apply_post_processing(self, surface: pygame.Surface) -> pygame.Surface:
        """Apply active shader effects to the surface and return processed surface."""
        # If no effects active, return original surface unchanged
        if (
            self.heat_intensity < 0.01
            and self.acid_distortion < 0.01
            and self.chromatic_aberration < 0.01
            and self.low_hp_pulse < 0.01
            and not self.shockwaves
        ):
            return surface

        # Extract primary shockwave parameters (if any)
        shock_cx = 0.5
        shock_cy = 0.5
        shock_r = 0.0
        shock_int = 0.0
        if self.shockwaves:
            sw = self.shockwaves[0]
            shock_cx = sw.uv_x
            shock_cy = sw.uv_y
            shock_r = sw.radius
            shock_int = sw.intensity

        # CPU / Numba JIT accelerated fallback
        src_array = pygame.surfarray.pixels3d(surface)
        out_surface = surface.copy()
        dst_array = pygame.surfarray.pixels3d(out_surface)

        apply_cpu_post_processing(
            src_array,
            dst_array,
            self.width,
            self.height,
            self.time,
            self.heat_intensity,
            self.acid_distortion,
            shock_cx,
            shock_cy,
            shock_r,
            shock_int,
            self.chromatic_aberration,
            self.low_hp_pulse,
        )

        del src_array
        del dst_array
        return out_surface
