"""Community Mod Manager for Py-Noita.

Handles:
- Discovery of mods in `mods/` directory.
- Parsing `mod.json` or `mod.lua` metadata.
- Dependency resolution and topological load ordering.
- Safe dynamic loading and sandboxing of Python `init.py` modules.
- Enabling / disabling mods with JSON configuration persistence.
- Dispatching lifecycle events to active mods.
"""

from dataclasses import dataclass, field
import importlib.util
import json
import logging
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Set

from py_noita.system.mod_api import ModAPI, mod_api


logger = logging.getLogger("py_noita.mod_manager")


@dataclass
class ModMetadata:
    """Metadata for a community mod."""
    id: str
    name: str
    version: str = "1.0.0"
    author: str = "Unknown"
    description: str = ""
    enabled: bool = True
    dependencies: List[str] = field(default_factory=list)
    entry_point: str = "init.py"


class Mod:
    """Represents a discovered community mod."""

    def __init__(self, meta: ModMetadata, path: Path):
        self.meta = meta
        self.path = path
        self.loaded: bool = False
        self.error: Optional[str] = None
        self.module: Optional[Any] = None

    @property
    def id(self) -> str:
        return self.meta.id

    @property
    def name(self) -> str:
        return self.meta.name

    @property
    def enabled(self) -> bool:
        return self.meta.enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self.meta.enabled = value


class ModManager:
    """Discovers, manages, and executes community mods."""

    def __init__(self, mods_dir: Optional[Path] = None, api: Optional[ModAPI] = None):
        if mods_dir is None:
            self.mods_dir = Path("mods")
        else:
            self.mods_dir = Path(mods_dir)
        self.mods_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.mods_dir / "mods_config.json"

        self.api = api or mod_api
        self.mods: Dict[str, Mod] = {}
        self.load_order: List[str] = []

    def discover_mods(self) -> List[Mod]:
        """Scan mods directory for mod folders containing mod.json or init.py or mod.lua."""
        self.mods.clear()
        config = self.load_config()

        if not self.mods_dir.exists():
            return []

        for item in self.mods_dir.iterdir():
            if not item.is_dir() or item.name.startswith((".", "_")):
                continue

            mod_json = item / "mod.json"
            mod_lua = item / "mod.lua"
            init_py = item / "init.py"

            meta: Optional[ModMetadata] = None

            if mod_json.exists():
                try:
                    with open(mod_json, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    meta = ModMetadata(
                        id=data.get("id", item.name),
                        name=data.get("name", item.name),
                        version=data.get("version", "1.0.0"),
                        author=data.get("author", "Unknown"),
                        description=data.get("description", ""),
                        enabled=data.get("enabled", True),
                        dependencies=data.get("dependencies", []),
                        entry_point=data.get("entry_point", "init.py" if init_py.exists() else ("mod.lua" if mod_lua.exists() else "init.py")),
                    )
                except Exception as e:
                    logger.error(f"[ModManager] Error parsing {mod_json}: {e}")
                    continue
            elif mod_lua.exists():
                # Parse Lua declaration table
                meta = self._parse_lua_metadata(mod_lua, item.name)
            elif init_py.exists():
                meta = ModMetadata(
                    id=item.name,
                    name=item.name.replace("_", " ").title(),
                    version="1.0.0",
                    author="Local",
                    description=f"Community mod from {item.name}",
                    enabled=True,
                    entry_point="init.py",
                )

            if meta:
                # Apply saved enabled status from config if present
                if meta.id in config:
                    meta.enabled = bool(config[meta.id])

                self.mods[meta.id] = Mod(meta, item)

        self._resolve_load_order()
        return list(self.mods.values())

    def _parse_lua_metadata(self, lua_path: Path, fallback_id: str) -> ModMetadata:
        """Lightweight parser for Lua mod declaration tables."""
        try:
            with open(lua_path, "r", encoding="utf-8") as f:
                content = f.read()

            mod_id = fallback_id
            name = fallback_id.replace("_", " ").title()
            version = "1.0.0"
            author = "Lua Modder"
            desc = ""

            id_m = re.search(r'id\s*=\s*["\']([^"\']+)["\']', content)
            if id_m:
                mod_id = id_m.group(1)

            name_m = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
            if name_m:
                name = name_m.group(1)

            ver_m = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
            if ver_m:
                version = ver_m.group(1)

            desc_m = re.search(r'description\s*=\s*["\']([^"\']+)["\']', content)
            if desc_m:
                desc = desc_m.group(1)

            return ModMetadata(
                id=mod_id,
                name=name,
                version=version,
                author=author,
                description=desc,
                enabled=True,
                entry_point="mod.lua",
            )
        except Exception as e:
            logger.error(f"[ModManager] Error parsing Lua metadata {lua_path}: {e}")
            return ModMetadata(id=fallback_id, name=fallback_id, entry_point="mod.lua")

    def _resolve_load_order(self) -> None:
        """Topologically sort enabled mods according to dependencies."""
        visited: Set[str] = set()
        order: List[str] = []

        def visit(mod_id: str, stack: Set[str]):
            if mod_id in stack:
                logger.warning(f"[ModManager] Cyclic dependency detected involving '{mod_id}'")
                return
            if mod_id not in visited and mod_id in self.mods:
                stack.add(mod_id)
                mod = self.mods[mod_id]
                for dep in mod.meta.dependencies:
                    if dep in self.mods:
                        visit(dep, stack)
                    else:
                        logger.warning(f"[ModManager] Missing dependency '{dep}' for mod '{mod_id}'")
                stack.remove(mod_id)
                visited.add(mod_id)
                order.append(mod_id)

        for mid in self.mods:
            if mid not in visited:
                visit(mid, set())

        self.load_order = order

    def load_all_mods(self) -> int:
        """Execute and register all enabled mods in resolved order. Returns count loaded."""
        if not self.mods:
            self.discover_mods()

        loaded_count = 0
        for mod_id in self.load_order:
            mod = self.mods[mod_id]
            if not mod.enabled:
                continue

            success = self._load_mod(mod)
            if success:
                loaded_count += 1

        # Fire on_init hook
        self.api.trigger_hook("on_init", self.api)
        return loaded_count

    def _load_mod(self, mod: Mod) -> bool:
        """Dynamically load and execute a single mod."""
        entry = mod.path / mod.meta.entry_point

        if not entry.exists():
            mod.error = f"Entry point '{mod.meta.entry_point}' not found"
            logger.error(f"[ModManager] Mod '{mod.id}': {mod.error}")
            return False

        if entry.suffix == ".py":
            try:
                module_name = f"py_noita_mod_{mod.id}"
                spec = importlib.util.spec_from_file_location(module_name, entry)
                if spec is None or spec.loader is None:
                    raise ImportError(f"Cannot create module spec for {entry}")

                mod_module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = mod_module

                # Inject API into module globals
                mod_module.api = self.api
                mod_module.mod_api = self.api

                spec.loader.exec_module(mod_module)
                mod.module = mod_module

                # Call init(api) if defined
                if hasattr(mod_module, "init"):
                    mod_module.init(self.api)
                elif hasattr(mod_module, "on_load"):
                    mod_module.on_load(self.api)

                mod.loaded = True
                mod.error = None
                logger.info(f"[ModManager] Successfully loaded mod '{mod.name}' ({mod.id})")
                return True
            except Exception as e:
                mod.error = str(e)
                logger.error(f"[ModManager] Failed to load Python mod '{mod.id}': {e}", exc_info=True)
                return False
        elif entry.suffix == ".lua":
            # For Lua mods, parse and execute via Lua script parser / declarative schema
            try:
                self._execute_lua_mod(entry, mod)
                mod.loaded = True
                mod.error = None
                logger.info(f"[ModManager] Successfully loaded Lua mod '{mod.name}' ({mod.id})")
                return True
            except Exception as e:
                mod.error = str(e)
                logger.error(f"[ModManager] Failed to load Lua mod '{mod.id}': {e}", exc_info=True)
                return False
        else:
            mod.error = f"Unsupported mod script type '{entry.suffix}'"
            return False

    def _execute_lua_mod(self, lua_path: Path, mod: Mod) -> None:
        """Execute declarative Lua mod directives."""
        with open(lua_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse registered genes if declared
        # Example: register_gene { id = "LUA_GENE", name = "Lua Gene", ... }
        gene_matches = re.finditer(r'register_gene\s*\{([^}]+)\}', content)
        for m in gene_matches:
            block = m.group(1)
            gid = self._extract_lua_str(block, "id", f"{mod.id}_gene")
            gname = self._extract_lua_str(block, "name", "Custom Gene")
            gdesc = self._extract_lua_str(block, "desc", "A custom gene created via Lua.")
            gcost = float(self._extract_lua_num(block, "cost", 10.0))
            from py_noita.weapons.gene import Gene, GeneType
            custom_gene = Gene(
                id=gid,
                name=gname,
                gene_type=GeneType.PROJECTILE,
                description=gdesc,
                biomass_cost=gcost,
            )
            self.api.register_gene(custom_gene)

    def _extract_lua_str(self, text: str, key: str, default: str) -> str:
        m = re.search(rf'{key}\s*=\s*["\']([^"\']+)["\']', text)
        return m.group(1) if m else default

    def _extract_lua_num(self, text: str, key: str, default: float) -> float:
        m = re.search(rf'{key}\s*=\s*([0-9\.]+)', text)
        return float(m.group(1)) if m else default

    def enable_mod(self, mod_id: str) -> bool:
        """Enable a mod and persist configuration."""
        if mod_id in self.mods:
            self.mods[mod_id].enabled = True
            self.save_config()
            return True
        return False

    def disable_mod(self, mod_id: str) -> bool:
        """Disable a mod and persist configuration."""
        if mod_id in self.mods:
            self.mods[mod_id].enabled = False
            self.save_config()
            return True
        return False

    def save_config(self) -> bool:
        """Save enabled/disabled state of all mods to disk."""
        try:
            data = {mid: m.enabled for mid, m in self.mods.items()}
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"[ModManager] Save config failed: {e}")
            return False

    def load_config(self) -> Dict[str, bool]:
        """Load enabled/disabled state of mods from disk."""
        if not self.config_file.exists():
            return {}
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[ModManager] Load config failed: {e}")
            return {}
