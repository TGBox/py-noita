"""Numba-accelerated physics and chemical reaction simulation kernels."""

import numpy as np
from numba import njit
from py_noita.simulation.materials import (
    STATE_EMPTY,
    STATE_SOLID,
    STATE_POWDER,
    STATE_LIQUID,
    STATE_GAS,
    STATE_ENERGY,
    MAT_AIR,
    MAT_TISSUE,
    MAT_BONE,
    MAT_CHITIN,
    MAT_WALL_BONE,
    MAT_NERVE,
    MAT_TENTACLE_FLESH,
    MAT_SPORES,
    MAT_EGGS,
    MAT_ASH,
    MAT_BONE_CHIP,
    MAT_BLOOD,
    MAT_ACID,
    MAT_BILE,
    MAT_LYMPH,
    MAT_PUS,
    MAT_MUTAGEN,
    MAT_WATER,
    MAT_BIOGAS,
    MAT_TOXIC_VAPOR,
    MAT_SMOKE,
    MAT_FIRE,
    MAT_CORROSION,
    PROP_STATE,
    PROP_DENSITY,
    PROP_FLAMMABILITY,
    PROP_ACID_VULN,
    PROP_DISPERSION,
    PROP_LIFETIME,
)


@njit(fastmath=True)
def simulate_step(
    grid: np.ndarray,
    life: np.ndarray,
    color_var: np.ndarray,
    min_x: int,
    max_x: int,
    min_y: int,
    max_y: int,
    frame_count: int,
    prop_state: np.ndarray,
    prop_density: np.ndarray,
    prop_flam: np.ndarray,
    prop_acid_vuln: np.ndarray,
    prop_disp: np.ndarray,
    prop_life: np.ndarray,
) -> int:
    """Execute one simulation step across the given bounding box.
    Returns the count of active/moved particles.
    """
    height, width = grid.shape
    moved_count = 0

    # Ensure bounds stay within grid
    x0 = max(1, min_x)
    x1 = min(width - 2, max_x)
    y0 = max(1, min_y)
    y1 = min(height - 2, max_y)

    left_to_right = (frame_count % 2 == 0)

    # 1. Update falling matter (Powders & Liquids) from bottom to top
    for y in range(y1, y0 - 1, -1):
        x_range = range(x0, x1 + 1) if left_to_right else range(x1, x0 - 1, -1)
        for x in x_range:
            mat = grid[y, x]
            if mat == MAT_AIR:
                continue

            state = prop_state[mat]

            # POWDERS (Sand, Spores, Eggs, Ash, Bone chips)
            if state == STATE_POWDER:
                density = prop_density[mat]

                # Check directly below
                below = grid[y + 1, x]
                if prop_density[below] < density and prop_state[below] != STATE_SOLID:
                    grid[y, x], grid[y + 1, x] = below, mat
                    life[y, x], life[y + 1, x] = life[y + 1, x], life[y, x]
                    color_var[y, x], color_var[y + 1, x] = color_var[y + 1, x], color_var[y, x]
                    moved_count += 1
                    continue

                # Diagonal roll
                dir_bias = 1 if ((x + y + frame_count) % 2 == 0) else -1
                d1_x = x + dir_bias
                d2_x = x - dir_bias

                if 1 <= d1_x < width - 1:
                    diag1 = grid[y + 1, d1_x]
                    if prop_density[diag1] < density and prop_state[diag1] != STATE_SOLID:
                        grid[y, x], grid[y + 1, d1_x] = diag1, mat
                        life[y, x], life[y + 1, d1_x] = life[y + 1, d1_x], life[y, x]
                        color_var[y, x], color_var[y + 1, d1_x] = color_var[y + 1, d1_x], color_var[y, x]
                        moved_count += 1
                        continue

                if 1 <= d2_x < width - 1:
                    diag2 = grid[y + 1, d2_x]
                    if prop_density[diag2] < density and prop_state[diag2] != STATE_SOLID:
                        grid[y, x], grid[y + 1, d2_x] = diag2, mat
                        life[y, x], life[y + 1, d2_x] = life[y + 1, d2_x], life[y, x]
                        color_var[y, x], color_var[y + 1, d2_x] = color_var[y + 1, d2_x], color_var[y, x]
                        moved_count += 1
                        continue

            # LIQUIDS (Blood, Acid, Bile, Lymph, Pus, Mutagen, Water)
            elif state == STATE_LIQUID:
                density = prop_density[mat]

                # Check directly below
                below = grid[y + 1, x]
                if prop_density[below] < density and prop_state[below] != STATE_SOLID:
                    grid[y, x], grid[y + 1, x] = below, mat
                    life[y, x], life[y + 1, x] = life[y + 1, x], life[y, x]
                    color_var[y, x], color_var[y + 1, x] = color_var[y + 1, x], color_var[y, x]
                    moved_count += 1
                    continue

                # Diagonal down
                dir_bias = 1 if ((x + y + frame_count) % 2 == 0) else -1
                d1_x = x + dir_bias
                d2_x = x - dir_bias

                if 1 <= d1_x < width - 1:
                    diag1 = grid[y + 1, d1_x]
                    if prop_density[diag1] < density and prop_state[diag1] != STATE_SOLID:
                        grid[y, x], grid[y + 1, d1_x] = diag1, mat
                        life[y, x], life[y + 1, d1_x] = life[y + 1, d1_x], life[y, x]
                        color_var[y, x], color_var[y + 1, d1_x] = color_var[y + 1, d1_x], color_var[y, x]
                        moved_count += 1
                        continue

                if 1 <= d2_x < width - 1:
                    diag2 = grid[y + 1, d2_x]
                    if prop_density[diag2] < density and prop_state[diag2] != STATE_SOLID:
                        grid[y, x], grid[y + 1, d2_x] = diag2, mat
                        life[y, x], life[y + 1, d2_x] = life[y + 1, d2_x], life[y, x]
                        color_var[y, x], color_var[y + 1, d2_x] = color_var[y + 1, d2_x], color_var[y, x]
                        moved_count += 1
                        continue

                # Sideways dispersion
                disp = prop_disp[mat]
                if disp > 0:
                    flow_dir = 1 if ((x * 7 + y * 13 + frame_count) % 2 == 0) else -1
                    target_x = x + flow_dir
                    if 1 <= target_x < width - 1:
                        side_cell = grid[y, target_x]
                        if prop_density[side_cell] < density and prop_state[side_cell] != STATE_SOLID:
                            grid[y, x], grid[y, target_x] = side_cell, mat
                            life[y, x], life[y, target_x] = life[y, target_x], life[y, x]
                            color_var[y, x], color_var[y, target_x] = color_var[y, target_x], color_var[y, x]
                            moved_count += 1
                            continue

    # 2. Update rising matter (Gases & Fire/Energy) from top to bottom
    for y in range(y0, y1 + 1):
        x_range = range(x0, x1 + 1) if left_to_right else range(x1, x0 - 1, -1)
        for x in x_range:
            mat = grid[y, x]
            if mat == MAT_AIR:
                continue

            state = prop_state[mat]

            # GASES (Biogas, Toxic Vapor, Smoke)
            if state == STATE_GAS:
                # Decrement lifetime
                cur_life = life[y, x]
                if cur_life > 1:
                    life[y, x] = cur_life - 1
                elif cur_life == 1:
                    grid[y, x] = MAT_AIR
                    life[y, x] = 0
                    moved_count += 1
                    continue

                density = prop_density[mat]

                # Rise up
                above = grid[y - 1, x]
                if above == MAT_AIR or (prop_state[above] == STATE_GAS and prop_density[above] > density):
                    grid[y, x], grid[y - 1, x] = above, mat
                    life[y, x], life[y - 1, x] = life[y - 1, x], life[y, x]
                    color_var[y, x], color_var[y - 1, x] = color_var[y - 1, x], color_var[y, x]
                    moved_count += 1
                    continue

                # Diagonal rise
                dir_bias = 1 if ((x + y + frame_count) % 2 == 0) else -1
                d1_x = x + dir_bias
                if 1 <= d1_x < width - 1:
                    diag_above = grid[y - 1, d1_x]
                    if diag_above == MAT_AIR:
                        grid[y, x], grid[y - 1, d1_x] = diag_above, mat
                        life[y, x], life[y - 1, d1_x] = life[y - 1, d1_x], life[y, x]
                        color_var[y, x], color_var[y - 1, d1_x] = color_var[y - 1, d1_x], color_var[y, x]
                        moved_count += 1
                        continue

                # Sideways drift
                side_x = x + (1 if ((x + frame_count) % 2 == 0) else -1)
                if 1 <= side_x < width - 1:
                    side_cell = grid[y, side_x]
                    if side_cell == MAT_AIR:
                        grid[y, x], grid[y, side_x] = side_cell, mat
                        life[y, x], life[y, side_x] = life[y, side_x], life[y, x]
                        color_var[y, x], color_var[y, side_x] = color_var[y, side_x], color_var[y, x]
                        moved_count += 1
                        continue

            # FIRE
            elif mat == MAT_FIRE:
                cur_life = life[y, x]
                if cur_life > 1:
                    life[y, x] = cur_life - 1
                else:
                    # Decay into smoke with 40% probability or air
                    if (x * 11 + y * 17 + frame_count) % 10 < 4:
                        grid[y, x] = MAT_SMOKE
                        life[y, x] = prop_life[MAT_SMOKE]
                    else:
                        grid[y, x] = MAT_AIR
                        life[y, x] = 0
                    moved_count += 1
                    continue

                # Spread fire to neighboring flammable cells
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < width and 0 <= ny < height:
                            nmat = grid[ny, nx]
                            if nmat == MAT_AIR:
                                continue

                            # Biogas detonation: ignite violently
                            if nmat == MAT_BIOGAS:
                                grid[ny, nx] = MAT_FIRE
                                life[ny, nx] = prop_life[MAT_FIRE] + 15
                                moved_count += 1
                            # Water or lymph extinguishes fire
                            elif nmat in (MAT_WATER, MAT_LYMPH):
                                grid[y, x] = MAT_SMOKE
                                life[y, x] = 60
                                grid[ny, nx] = MAT_AIR
                                moved_count += 1
                                break
                            elif prop_flam[nmat] > 0:
                                # Roll flammability chance
                                roll = (x * 31 + y * 47 + nx * 13 + frame_count) % 100
                                if roll < prop_flam[nmat]:
                                    grid[ny, nx] = MAT_FIRE
                                    life[ny, nx] = prop_life[MAT_FIRE]
                                    moved_count += 1

            # CORROSION FOAM
            elif mat == MAT_CORROSION:
                cur_life = life[y, x]
                if cur_life > 1:
                    life[y, x] = cur_life - 1
                else:
                    # Turns into toxic vapor
                    grid[y, x] = MAT_TOXIC_VAPOR
                    life[y, x] = prop_life[MAT_TOXIC_VAPOR]
                    moved_count += 1

    # 3. Chemical & Biological Reactions (Acid, Lymph neutralization, Mutagen)
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            mat = grid[y, x]

            # ACID REACTIONS
            if mat == MAT_ACID:
                # Check neighbors for tissue, bone, or lymph
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < width and 0 <= ny < height:
                            nmat = grid[ny, nx]

                            # Neutralization with Lymph -> produces Water
                            if nmat == MAT_LYMPH:
                                grid[y, x] = MAT_WATER
                                grid[ny, nx] = MAT_WATER
                                moved_count += 2
                                break

                            # Dissolving Tissue or Bone
                            vuln = prop_acid_vuln[nmat]
                            if vuln > 0:
                                roll = (x * 19 + y * 23 + frame_count) % 100
                                if roll < vuln:
                                    grid[ny, nx] = MAT_CORROSION
                                    life[ny, nx] = prop_life[MAT_CORROSION]
                                    # Emitter of Biogas bubble
                                    if y > 1 and grid[y - 1, x] == MAT_AIR:
                                        grid[y - 1, x] = MAT_BIOGAS
                                        life[y - 1, x] = prop_life[MAT_BIOGAS]
                                    moved_count += 1

            # MUTAGEN ALCHEMY
            elif mat == MAT_MUTAGEN:
                # Mutates solid tissue into creeping tentacle flesh
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < width and 0 <= ny < height:
                            nmat = grid[ny, nx]
                            if nmat == MAT_TISSUE:
                                roll = (x * 43 + y * 67 + frame_count) % 100
                                if roll < 40:
                                    grid[ny, nx] = MAT_TENTACLE_FLESH
                                    color_var[ny, nx] = (color_var[ny, nx] + 1) % 4
                                    moved_count += 1

    return moved_count
