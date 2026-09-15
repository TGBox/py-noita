"""Modding API for Py-Noita.

Provides safe registration hooks for:
- Custom Genes (cannula cards, modifiers, triggers)
- Custom Materials (fallingsand physics, densities, reactions, color palettes)
- Custom Biomes (level generation configs, themes, cavern layouts)
- Custom Enemies (AI types, limb rigs, behaviors, projectiles)
- Custom Symbiote Strains (player starting classes, loadouts)
- Lifecycle Event Hooks (on_init, on_run_start, on_player_spawn, on_enemy_killed, on_biome_loaded)
"""

from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import logging

from py_noita.weapons.gene import Gene, GENE_DICT, GENE_LIBRARY
from py_noita.simulation.materials import (
    MAX_MATERIALS,
    PROP_ACID_VULN,
    PROP_DENSITY,
    PROP_DISPERSION,
    PROP_FLAMMABILITY,
    PROP_GLOW,
    PROP_LIFETIME,
    PROP_STATE,
    MATERIAL_COLORS,
)
from py_noita.entities.enemy import Enemy, CUSTOM_ENEMY_FACTORIES
from py_noita.world.biome import Biome, ALL_BIOMES, BIOME_BY_ID
from py_noita.ui.codex import Strain, ALL_STRAINS


logger = logging.getLogger("py_noita.mod_api")


class ModAPI:
    """Central API exposed to community mods."""

    def __init__(self):
        self.custom_genes: Dict[str, Gene] = {}
        self.custom_materials: Dict[int, Dict[str, Any]] = {}
        self.custom_enemies: Dict[str, Callable[[float, float], Enemy]] = {}
        self.custom_biomes: Dict[str, Biome] = {}
        self.custom_strains: Dict[str, Strain] = {}
        self.hooks: Dict[str, List[Callable[..., Any]]] = {
            "on_init": [],
            "on_run_start": [],
            "on_player_spawn": [],
            "on_enemy_killed": [],
            "on_biome_loaded": [],
            "on_tick": [],
        }

    def register_gene(self, gene: Gene) -> bool:
        """Register a new Gene card for cannulas and loot drops."""
        if not isinstance(gene, Gene):
            logger.error(f"[ModAPI] Invalid gene object: {gene}")
            return False
        if gene.id in GENE_DICT:
            logger.warning(f"[ModAPI] Overriding existing gene '{gene.id}'")
        else:
            GENE_LIBRARY.append(gene)
        GENE_DICT[gene.id] = gene
        self.custom_genes[gene.id] = gene
        logger.info(f"[ModAPI] Registered custom gene '{gene.id}' ({gene.name})")
        return True

    def register_material(
        self,
        mat_id: int,
        name: str,
        state: int,
        density: float,
        colors: List[Tuple[int, int, int]],
        flammability: int = 0,
        acid_vuln: int = 0,
        dispersion: int = 0,
        lifetime: int = 0,
        glow: int = 0,
    ) -> bool:
        """Register a new physics material into the simulation arrays."""
        if mat_id < 0 or mat_id >= MAX_MATERIALS:
            logger.error(f"[ModAPI] Material ID {mat_id} out of bounds (0..{MAX_MATERIALS-1})")
            return False
        if not colors:
            colors = [(200, 200, 200)]

        PROP_STATE[mat_id] = state
        PROP_DENSITY[mat_id] = density
        PROP_FLAMMABILITY[mat_id] = flammability
        PROP_ACID_VULN[mat_id] = acid_vuln
        PROP_DISPERSION[mat_id] = dispersion
        PROP_LIFETIME[mat_id] = lifetime
        PROP_GLOW[mat_id] = glow
        MATERIAL_COLORS[mat_id] = list(colors)

        self.custom_materials[mat_id] = {
            "id": mat_id,
            "name": name,
            "state": state,
            "density": density,
            "colors": colors,
        }
        logger.info(f"[ModAPI] Registered custom material {mat_id} ('{name}')")
        return True

    def register_enemy(self, enemy_type: str, factory: Callable[[float, float], Enemy]) -> bool:
        """Register a custom enemy constructor."""
        if not callable(factory):
            logger.error(f"[ModAPI] Enemy factory for '{enemy_type}' must be callable")
            return False
        CUSTOM_ENEMY_FACTORIES[enemy_type] = factory
        self.custom_enemies[enemy_type] = factory
        logger.info(f"[ModAPI] Registered custom enemy '{enemy_type}'")
        return True

    def register_biome(self, biome: Biome, is_side_path: bool = True) -> bool:
        """Register a new subterranean biome."""
        if not isinstance(biome, Biome):
            logger.error(f"[ModAPI] Invalid biome object: {biome}")
            return False
        biome.is_side_path = is_side_path
        if biome.biome_id in BIOME_BY_ID:
            logger.warning(f"[ModAPI] Overriding existing biome '{biome.biome_id}'")
        else:
            ALL_BIOMES.append(biome)
        BIOME_BY_ID[biome.biome_id] = biome
        self.custom_biomes[biome.biome_id] = biome
        logger.info(f"[ModAPI] Registered custom biome '{biome.biome_id}' ({biome.name})")
        return True

    def register_strain(self, strain: Strain) -> bool:
        """Register a playable Symbiote strain."""
        if not isinstance(strain, Strain):
            logger.error(f"[ModAPI] Invalid strain object: {strain}")
            return False
        if any(s.strain_id == strain.strain_id for s in ALL_STRAINS):
            logger.warning(f"[ModAPI] Strain '{strain.strain_id}' already registered")
        else:
            ALL_STRAINS.append(strain)
        self.custom_strains[strain.strain_id] = strain
        logger.info(f"[ModAPI] Registered custom strain '{strain.strain_id}' ({strain.name})")
        return True

    def register_hook(self, event_name: str, callback: Callable[..., Any]) -> None:
        """Subscribe a callback to a lifecycle event."""
        if event_name not in self.hooks:
            self.hooks[event_name] = []
        self.hooks[event_name].append(callback)

    def hook(self, event_name: str):
        """Decorator for registering event hooks."""
        def decorator(fn: Callable[..., Any]):
            self.register_hook(event_name, fn)
            return fn
        return decorator

    def trigger_hook(self, event_name: str, *args, **kwargs) -> List[Any]:
        """Dispatch lifecycle event to all subscribed hooks safely."""
        results = []
        if event_name in self.hooks:
            for cb in self.hooks[event_name]:
                try:
                    res = cb(*args, **kwargs)
                    results.append(res)
                except Exception as e:
                    logger.error(f"[ModAPI] Error in hook '{event_name}': {e}", exc_info=True)
        return results

    def reset_for_tests(self) -> None:
        """Clean up custom registrations for unit testing."""
        for gid in list(self.custom_genes.keys()):
            GENE_DICT.pop(gid, None)
            GENE_LIBRARY[:] = [g for g in GENE_LIBRARY if g.id != gid]
        self.custom_genes.clear()

        for mid in list(self.custom_materials.keys()):
            PROP_STATE[mid] = 0
            PROP_DENSITY[mid] = 0.0
            PROP_FLAMMABILITY[mid] = 0
            PROP_ACID_VULN[mid] = 0
            PROP_DISPERSION[mid] = 0
            PROP_LIFETIME[mid] = 0
            PROP_GLOW[mid] = 0
            MATERIAL_COLORS.pop(mid, None)
        self.custom_materials.clear()

        for etype in list(self.custom_enemies.keys()):
            CUSTOM_ENEMY_FACTORIES.pop(etype, None)
        self.custom_enemies.clear()

        for bid in list(self.custom_biomes.keys()):
            BIOME_BY_ID.pop(bid, None)
            ALL_BIOMES[:] = [b for b in ALL_BIOMES if b.biome_id != bid]
        self.custom_biomes.clear()

        for sid in list(self.custom_strains.keys()):
            ALL_STRAINS[:] = [s for s in ALL_STRAINS if s.strain_id != sid]
        self.custom_strains.clear()

        for k in self.hooks:
            self.hooks[k].clear()


# Global ModAPI singleton instance
mod_api = ModAPI()
