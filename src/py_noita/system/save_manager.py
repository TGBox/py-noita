"""Mid-Run Quicksave and Crash-Recovery System for Py-Noita.

Provides atomic, robust serialization of:
- Simulation pixel grid, decay lifetimes, color variation, and decal stain maps.
- Symbiote Player statistics, vitals, position, velocity, and status timers.
- Cannula deck loadouts, installed genes, slots, and energy buffers.
- Liquid glands, fluid inventory, and fill levels.
- Genetic mutation perks and passive modifiers.
- Living immune enemies and biological bosses.
- Exploration loot cysts, ancient DNA lore tablets, and hidden gene orbs.
- Portal state, endgame triggers, and world seed determinism.
- Strict Permadeath deletion upon player death.
"""

from datetime import datetime
import json
import os
from pathlib import Path
import struct
from typing import Any, Dict, Optional
import zlib
import numpy as np

from py_noita.config import WORLD_HEIGHT, WORLD_WIDTH
from py_noita.entities.enemy import Enemy, create_enemy
from py_noita.entities.player import LiquidGland, Player
from py_noita.perks.perk_definitions import ALL_PERKS
from py_noita.perks.perk_manager import PerkManager
from py_noita.physics.physics_world import PhysicsWorld
from py_noita.simulation.grid import SimulationGrid
from py_noita.weapons.cannula import OrganCannula
from py_noita.weapons.gene import GENE_DICT
from py_noita.world.biome import ALL_BIOMES
from py_noita.world.endings import AscentReturnGateway, SurfaceAscentPortal
from py_noita.world.generator import LootCyst, WorldPortal
from py_noita.world.incubation_node import IncubationNode
from py_noita.world.secrets import DnaTablet, GeneOrb
from py_noita.world.streamer import WorldStreamer


GRID_SAVE_MAGIC = b"PNSV"  # Py-Noita Save Grid


class SaveManager:
    """Manages serialization, atomic disk persistence, and recovery of active runs."""

    def __init__(self, save_dir: Optional[Path] = None):
        if save_dir is None:
            self.save_dir = Path("saves")
        else:
            self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def _get_json_path(self, filename: str = "quicksave") -> Path:
        return self.save_dir / f"{filename}.json"

    def _get_grid_path(self, filename: str = "quicksave") -> Path:
        return self.save_dir / f"{filename}_grid.bin"

    def has_quicksave(self, filename: str = "quicksave") -> bool:
        """Check if a complete, valid quicksave exists."""
        j_path = self._get_json_path(filename)
        g_path = self._get_grid_path(filename)
        return j_path.exists() and g_path.exists() and j_path.stat().st_size > 0 and g_path.stat().st_size > 0

    def get_quicksave_info(self, filename: str = "quicksave") -> Optional[Dict[str, Any]]:
        """Read lightweight metadata for menu display without loading heavy world grids."""
        if not self.has_quicksave(filename):
            return None
        try:
            with open(self._get_json_path(filename), "r", encoding="utf-8") as f:
                data = json.load(f)
            biome_idx = data.get("current_biome_index", 0)
            biome_name = ALL_BIOMES[min(biome_idx, len(ALL_BIOMES) - 1)].name if ALL_BIOMES else f"Biom {biome_idx + 1}"
            player_data = data.get("player", {})
            return {
                "timestamp": data.get("timestamp", "Unbekannt"),
                "world_seed": data.get("world_seed", 0),
                "biome_index": biome_idx,
                "biome_name": biome_name,
                "player_hp": player_data.get("hp", 0.0),
                "player_max_hp": player_data.get("max_hp", 100.0),
                "biomass": player_data.get("biomass_currency", 0),
                "orbs": player_data.get("orbs_collected", 0),
                "kills": data.get("kills_this_run", 0),
            }
        except Exception:
            return None

    def delete_quicksave(self, filename: str = "quicksave") -> None:
        """Permanently remove quicksave files (invoked upon player permadeath or run completion)."""
        j_path = self._get_json_path(filename)
        g_path = self._get_grid_path(filename)
        for path in (j_path, g_path):
            if path.exists():
                try:
                    path.unlink()
                except Exception:
                    pass

    def save_run(self, game: Any, filename: str = "quicksave") -> bool:
        """Atomically serialize the entire state of the running game session to disk."""
        if not game.player or not game.player.alive:
            return False

        try:
            # 1. Compile JSON metadata & entity states
            cannulas_data = []
            for c in game.player.cannulas:
                slot_ids = [(gene.id if gene is not None else None) for gene in c.slots]
                cannulas_data.append({
                    "name": c.name,
                    "capacity": c.capacity,
                    "cast_delay": c.cast_delay,
                    "recharge_time": c.recharge_time,
                    "biomass_max": c.biomass_max,
                    "biomass_recharge": c.biomass_recharge,
                    "spread": c.spread,
                    "shuffle": c.shuffle,
                    "current_biomass": c.current_biomass,
                    "slots": slot_ids,
                })

            glands_data = []
            for g in game.player.glands:
                glands_data.append({
                    "capacity": g.capacity,
                    "current_amount": g.current_amount,
                    "material_id": g.material_id,
                })

            player_data = {
                "x": game.player.x,
                "y": game.player.y,
                "vx": game.player.vx,
                "vy": game.player.vy,
                "hp": game.player.hp,
                "max_hp": game.player.max_hp,
                "levitation": game.player.levitation,
                "max_levitation": game.player.max_levitation,
                "on_fire": game.player.on_fire,
                "fire_timer": game.player.fire_timer,
                "acid_burn_timer": game.player.acid_burn_timer,
                "blood_soaked_timer": game.player.blood_soaked_timer,
                "active_cannula_index": game.player.active_cannula_index,
                "active_gland_index": game.player.active_gland_index,
                "biomass_currency": game.player.biomass_currency,
                "orbs_collected": game.player.orbs_collected,
                "discovered_tablets": list(getattr(game.player, "discovered_tablets", [])),
                "cannulas": cannulas_data,
                "glands": glands_data,
            }

            perks_data = [p.id for p in game.perk_manager.active_perks]

            enemies_data = []
            for e in game.enemies:
                if getattr(e, "alive", True):
                    enemies_data.append({
                        "enemy_type": e.enemy_type,
                        "x": e.x,
                        "y": e.y,
                        "vx": e.vx,
                        "vy": e.vy,
                        "hp": e.hp,
                        "max_hp": e.max_hp,
                        "blood_mat": getattr(e, "blood_mat", 3),
                        "biomass_value": getattr(e, "biomass_value", 15),
                    })

            cysts_data = []
            for cyst in game.loot_cysts:
                cysts_data.append({
                    "x": cyst.x,
                    "y": cyst.y,
                    "reward_type": getattr(cyst, "reward_type", "BIOMASS"),
                    "alive": cyst.alive,
                })

            orbs_data = []
            for orb in game.gene_orbs:
                orbs_data.append({
                    "orb_id": orb.orb_id,
                    "x": orb.x,
                    "y": orb.y,
                    "reward_gene_id": orb.reward_gene_id,
                    "name": orb.name,
                    "description": orb.description,
                    "collected": orb.collected,
                })

            tablets_data = []
            for tab in game.dna_tablets:
                tablets_data.append({
                    "tablet_id": tab.tablet_id,
                    "x": tab.x,
                    "y": tab.y,
                    "title": tab.title,
                    "text": tab.text,
                })

            exit_portal_data = None
            if game.exit_portal:
                exit_portal_data = {
                    "x": game.exit_portal.x,
                    "y": game.exit_portal.y,
                    "radius": game.exit_portal.radius,
                    "active": game.exit_portal.active,
                }

            ascent_portal_data = None
            if game.ascent_portal:
                ascent_portal_data = {
                    "x": game.ascent_portal.x,
                    "y": game.ascent_portal.y,
                }

            ascent_return_data = None
            if game.ascent_return_gateway:
                ascent_return_data = {
                    "x": game.ascent_return_gateway.x,
                    "y": game.ascent_return_gateway.y,
                }

            secret_boss_data = None
            if game.secret_boss and getattr(game.secret_boss, "alive", True):
                secret_boss_data = {
                    "enemy_type": game.secret_boss.enemy_type,
                    "x": game.secret_boss.x,
                    "y": game.secret_boss.y,
                    "hp": game.secret_boss.hp,
                    "max_hp": game.secret_boss.max_hp,
                    "alive": True,
                }

            state_payload = {
                "version": 1,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "world_seed": game.world_seed,
                "current_biome_index": game.current_biome_index,
                "game_state": game.state,
                "kills_this_run": game.kills_this_run,
                "earned_mutagen": game.earned_mutagen,
                "has_primordial_genome": game.has_primordial_genome,
                "core_boss_defeated": game.core_boss_defeated,
                "ending_id": game.ending_id,
                "player": player_data,
                "perk_ids": perks_data,
                "enemies": enemies_data,
                "loot_cysts": cysts_data,
                "gene_orbs": orbs_data,
                "dna_tablets": tablets_data,
                "exit_portal": exit_portal_data,
                "ascent_portal": ascent_portal_data,
                "ascent_return_gateway": ascent_return_data,
                "secret_boss": secret_boss_data,
            }

            # 2. Serialize World Grid binary payload
            w = game.grid.width
            h = game.grid.height
            header = struct.pack("<4sii", GRID_SAVE_MAGIC, w, h)
            raw_grid_data = (
                game.grid.grid.tobytes()
                + game.grid.life.tobytes()
                + game.grid.color_var.tobytes()
                + game.grid.stain_map.tobytes()
            )
            compressed_grid = zlib.compress(raw_grid_data, level=4)
            grid_payload = header + compressed_grid

            # 3. Atomic File Writes via temporary files
            json_tmp = self.save_dir / f"{filename}.json.tmp"
            grid_tmp = self.save_dir / f"{filename}_grid.bin.tmp"

            with open(json_tmp, "w", encoding="utf-8") as f:
                json.dump(state_payload, f, indent=2)

            with open(grid_tmp, "wb") as f:
                f.write(grid_payload)

            # Atomic replace
            json_target = self._get_json_path(filename)
            grid_target = self._get_grid_path(filename)

            if json_target.exists():
                json_target.unlink()
            json_tmp.replace(json_target)

            if grid_target.exists():
                grid_target.unlink()
            grid_tmp.replace(grid_target)

            return True

        except Exception as err:
            print(f"[SaveManager] Quicksave failed: {err}")
            return False

    def load_run(self, game: Any, filename: str = "quicksave") -> bool:
        """Load and reconstruct the saved run seamlessly."""
        if not self.has_quicksave(filename):
            return False

        try:
            # 1. Read JSON metadata
            with open(self._get_json_path(filename), "r", encoding="utf-8") as f:
                state_data = json.load(f)

            # 2. Read and unpack Grid binary payload
            with open(self._get_grid_path(filename), "rb") as f:
                grid_bytes = f.read()

            header_size = struct.calcsize("<4sii")
            magic, w, h = struct.unpack("<4sii", grid_bytes[:header_size])
            if magic != GRID_SAVE_MAGIC:
                print(f"[SaveManager] Invalid grid magic: {magic}")
                return False

            decompressed = zlib.decompress(grid_bytes[header_size:])
            grid_size = w * h
            life_size = w * h * 2  # uint16
            color_var_size = w * h
            stain_map_size = w * h

            expected_len = grid_size + life_size + color_var_size + stain_map_size
            if len(decompressed) != expected_len:
                print(f"[SaveManager] Corrupted decompressed grid length: {len(decompressed)} != {expected_len}")
                return False

            o0 = 0
            o1 = o0 + grid_size
            o2 = o1 + life_size
            o3 = o2 + color_var_size
            o4 = o3 + stain_map_size

            restored_grid = np.frombuffer(decompressed[o0:o1], dtype=np.uint8).reshape((h, w))
            restored_life = np.frombuffer(decompressed[o1:o2], dtype=np.uint16).reshape((h, w))
            restored_color_var = np.frombuffer(decompressed[o2:o3], dtype=np.uint8).reshape((h, w))
            restored_stain = np.frombuffer(decompressed[o3:o4], dtype=np.uint8).reshape((h, w))

            # Apply to simulation grid
            if game.grid.width != w or game.grid.height != h:
                game.grid = SimulationGrid(w, h)
            game.grid.grid = restored_grid.copy()
            game.grid.life = restored_life.copy()
            game.grid.color_var = restored_color_var.copy()
            game.grid.stain_map = restored_stain.copy()
            game.grid.init_boundaries()

            # Mark all chunks dirty for simulation
            for cy in range(game.grid.chunks_y):
                for cx in range(game.grid.chunks_x):
                    game.grid.active_chunks.add((cx, cy))

            # Recreate PhysicsWorld
            game.physics_world = PhysicsWorld(game.grid)
            game.grid.physics_world = game.physics_world

            # 3. Restore Core Session Variables
            game.world_seed = state_data.get("world_seed", 42891)
            game.current_biome_index = state_data.get("current_biome_index", 0)
            game.kills_this_run = state_data.get("kills_this_run", 0)
            game.earned_mutagen = state_data.get("earned_mutagen", 0)
            game.has_primordial_genome = state_data.get("has_primordial_genome", False)
            game.core_boss_defeated = state_data.get("core_boss_defeated", False)
            game.ending_id = state_data.get("ending_id", 0)
            game.is_victory = False

            # 4. Restore Player & Equipment
            pdata = state_data["player"]
            player = Player(pdata["x"], pdata["y"])
            player.vx = pdata.get("vx", 0.0)
            player.vy = pdata.get("vy", 0.0)
            player.hp = pdata.get("hp", player.max_hp)
            player.max_hp = pdata.get("max_hp", player.max_hp)
            player.levitation = pdata.get("levitation", player.max_levitation)
            player.max_levitation = pdata.get("max_levitation", player.max_levitation)
            player.on_fire = pdata.get("on_fire", False)
            player.fire_timer = pdata.get("fire_timer", 0)
            player.acid_burn_timer = pdata.get("acid_burn_timer", 0)
            player.blood_soaked_timer = pdata.get("blood_soaked_timer", 0)
            player.biomass_currency = pdata.get("biomass_currency", 0)
            player.orbs_collected = pdata.get("orbs_collected", 0)
            player.discovered_tablets = list(pdata.get("discovered_tablets", []))
            player.active_cannula_index = pdata.get("active_cannula_index", 0)
            player.active_gland_index = pdata.get("active_gland_index", 0)

            # Reconstruct Cannulas
            player.cannulas.clear()
            for cdata in pdata.get("cannulas", []):
                cannula = OrganCannula(
                    name=cdata.get("name", "Organ-Kanüle"),
                    capacity=cdata.get("capacity", 4),
                    cast_delay=cdata.get("cast_delay", 0.15),
                    recharge_time=cdata.get("recharge_time", 0.55),
                    biomass_max=cdata.get("biomass_max", 120.0),
                    biomass_recharge=cdata.get("biomass_recharge", 45.0),
                    spread=cdata.get("spread", 2.0),
                    shuffle=cdata.get("shuffle", False),
                )
                cannula.current_biomass = cdata.get("current_biomass", cannula.biomass_max)
                for slot_idx, gid in enumerate(cdata.get("slots", [])):
                    if gid and gid in GENE_DICT:
                        cannula.set_slot(slot_idx, GENE_DICT[gid])
                player.cannulas.append(cannula)

            # Reconstruct Glands
            for g_idx, gdata in enumerate(pdata.get("glands", [])):
                if g_idx < len(player.glands):
                    player.glands[g_idx].capacity = gdata.get("capacity", 150)
                    player.glands[g_idx].current_amount = gdata.get("current_amount", 0)
                    player.glands[g_idx].material_id = gdata.get("material_id", 0)

            game.player = player

            # 5. Restore Perks
            game.perk_manager = PerkManager()
            for pid in state_data.get("perk_ids", []):
                perk_obj = next((p for p in ALL_PERKS if p.id == pid), None)
                if perk_obj:
                    game.perk_manager.add_perk(perk_obj, game.player)

            # 6. Restore Enemies
            game.enemies.clear()
            for edata in state_data.get("enemies", []):
                enemy = create_enemy(edata["enemy_type"], edata["x"], edata["y"])
                enemy.vx = edata.get("vx", 0.0)
                enemy.vy = edata.get("vy", 0.0)
                enemy.hp = edata.get("hp", enemy.max_hp)
                enemy.max_hp = edata.get("max_hp", enemy.max_hp)
                enemy.blood_mat = edata.get("blood_mat", getattr(enemy, "blood_mat", 3))
                enemy.biomass_value = edata.get("biomass_value", getattr(enemy, "biomass_value", 15))
                game.enemies.append(enemy)

            # 7. Restore Collectibles & Secrets
            game.loot_cysts.clear()
            for cdata in state_data.get("loot_cysts", []):
                cyst = LootCyst(cdata["x"], cdata["y"], cdata.get("reward_type", "BIOMASS"))
                cyst.alive = cdata.get("alive", True)
                game.loot_cysts.append(cyst)

            game.gene_orbs.clear()
            for odata in state_data.get("gene_orbs", []):
                orb = GeneOrb(
                    orb_id=odata["orb_id"],
                    x=odata["x"],
                    y=odata["y"],
                    reward_gene_id=odata["reward_gene_id"],
                    name=odata["name"],
                    description=odata["description"],
                )
                orb.collected = odata.get("collected", False)
                game.gene_orbs.append(orb)

            game.dna_tablets.clear()
            for tdata in state_data.get("dna_tablets", []):
                tab = DnaTablet(
                    tablet_id=tdata["tablet_id"],
                    x=tdata["x"],
                    y=tdata["y"],
                    title=tdata["title"],
                    text=tdata["text"],
                )
                game.dna_tablets.append(tab)

            # 8. Restore Portals & Boss
            game.exit_portal = None
            if state_data.get("exit_portal"):
                ep = state_data["exit_portal"]
                game.exit_portal = WorldPortal(ep["x"], ep["y"])
                game.exit_portal.radius = ep.get("radius", 16.0)
                game.exit_portal.active = ep.get("active", True)

            game.ascent_portal = None
            if state_data.get("ascent_portal"):
                ap = state_data["ascent_portal"]
                game.ascent_portal = SurfaceAscentPortal(ap["x"], ap["y"])

            game.ascent_return_gateway = None
            if state_data.get("ascent_return_gateway"):
                arg = state_data["ascent_return_gateway"]
                game.ascent_return_gateway = AscentReturnGateway(arg["x"], arg["y"])

            game.secret_boss = None
            if state_data.get("secret_boss"):
                sb_data = state_data["secret_boss"]
                game.secret_boss = create_enemy(sb_data["enemy_type"], sb_data["x"], sb_data["y"])
                game.secret_boss.hp = sb_data.get("hp", game.secret_boss.max_hp)
                game.secret_boss.max_hp = sb_data.get("max_hp", game.secret_boss.max_hp)
                game.enemies.append(game.secret_boss)

            # 9. Restore Streamer & Camera
            if game.streamer:
                game.streamer.shutdown()
            game.streamer = WorldStreamer(seed=game.world_seed)

            game.camera.center_on(game.player.center_x, game.player.center_y)
            game.projectiles.clear()
            game.explosion_debris.clear()

            # Restore audio theme
            if hasattr(game.audio, "music") and game.audio.music:
                game.audio.music.set_theme(game.current_biome_index)
                game.audio.music.set_combat_intensity(0.0)

            game.state = state_data.get("game_state", "PLAYING")
            return True

        except Exception as err:
            print(f"[SaveManager] Restore run failed: {err}")
            return False
