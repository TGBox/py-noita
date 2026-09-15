"""Unit tests for Py-Noita Modding API and ModManager."""

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from py_noita.system.mod_api import ModAPI, mod_api
from py_noita.system.mod_manager import ModManager, ModMetadata
from py_noita.weapons.gene import Gene, GeneType, GENE_DICT
from py_noita.entities.enemy import Enemy, create_enemy, CUSTOM_ENEMY_FACTORIES
from py_noita.world.biome import Biome, ALL_BIOMES, BIOME_BY_ID
from py_noita.ui.codex import Strain, ALL_STRAINS
from py_noita.simulation.materials import STATE_LIQUID, PROP_STATE, PROP_DENSITY, MATERIAL_COLORS


class DummyEnemy(Enemy):
    """Test enemy class."""
    def __init__(self, x: float, y: float):
        super().__init__(x, y, enemy_type="TEST_SLUG", hp=50.0, width=16, height=16)
        self.name = "Test Slug"


class TestModAPI(unittest.TestCase):
    """Tests for ModAPI registration functions and lifecycle hooks."""

    def setUp(self):
        self.api = ModAPI()

    def tearDown(self):
        self.api.reset_for_tests()

    def test_register_gene(self):
        """Verify custom gene registration."""
        test_gene = Gene(
            id="TEST_ACID_SPRAY",
            name="Test-Säurespray",
            gene_type=GeneType.PROJECTILE,
            description="Test description",
            biomass_cost=15.0,
        )
        success = self.api.register_gene(test_gene)
        self.assertTrue(success)
        self.assertIn("TEST_ACID_SPRAY", GENE_DICT)
        self.assertEqual(GENE_DICT["TEST_ACID_SPRAY"].name, "Test-Säurespray")

    def test_register_material(self):
        """Verify custom material registration into simulation property tables."""
        mat_id = 48
        colors = [(100, 200, 50), (120, 220, 70)]
        success = self.api.register_material(
            mat_id=mat_id,
            name="Test-Ooze",
            state=STATE_LIQUID,
            density=1.5,
            colors=colors,
            flammability=25,
            glow=120,
        )
        self.assertTrue(success)
        self.assertEqual(PROP_STATE[mat_id], STATE_LIQUID)
        self.assertAlmostEqual(PROP_DENSITY[mat_id], 1.5, places=2)
        self.assertIn(mat_id, MATERIAL_COLORS)
        self.assertEqual(MATERIAL_COLORS[mat_id], colors)

    def test_register_enemy(self):
        """Verify custom enemy registration and factory instantiation."""
        success = self.api.register_enemy("TEST_SLUG", lambda x, y: DummyEnemy(x, y))
        self.assertTrue(success)

        enemy = create_enemy("TEST_SLUG", 120.0, 240.0)
        self.assertEqual(enemy.enemy_type, "TEST_SLUG")
        self.assertEqual(enemy.name, "Test Slug")
        self.assertEqual(enemy.x, 120.0)
        self.assertEqual(enemy.y, 240.0)

    def test_register_biome(self):
        """Verify custom biome registration."""
        test_biome = Biome(
            biome_id="TEST_CRYSTAL_CAVERN",
            name="Kristall-Kaverne",
            depth_level=9,
            ambient_color=(10, 15, 30),
            primary_solid=1,
            secondary_solid=2,
            liquid_pool_mat=21,
            gas_mat=0,
            powder_mat=10,
            enemy_types=["MACROPHAGE"],
        )
        success = self.api.register_biome(test_biome)
        self.assertTrue(success)
        self.assertIn("TEST_CRYSTAL_CAVERN", BIOME_BY_ID)
        self.assertEqual(BIOME_BY_ID["TEST_CRYSTAL_CAVERN"].name, "Kristall-Kaverne")

    def test_register_strain(self):
        """Verify custom strain registration."""
        test_strain = Strain(
            strain_id="TEST_MUTANT",
            name="Test-Mutant",
            description="Versuchsobjekt",
            unlock_cost=50,
            starter_gene_ids=["BONE_SPIKE"],
            starter_gland_mat=20,
        )
        success = self.api.register_strain(test_strain)
        self.assertTrue(success)
        self.assertTrue(any(s.strain_id == "TEST_MUTANT" for s in ALL_STRAINS))

    def test_lifecycle_hooks(self):
        """Verify hook registration and event dispatching."""
        called_events = []

        @self.api.hook("on_run_start")
        def on_run(game_ref):
            called_events.append(("run_start", game_ref))

        self.api.register_hook("on_biome_loaded", lambda b: called_events.append(("biome", b)))

        self.api.trigger_hook("on_run_start", "dummy_game")
        self.api.trigger_hook("on_biome_loaded", "dummy_biome")

        self.assertEqual(len(called_events), 2)
        self.assertEqual(called_events[0], ("run_start", "dummy_game"))
        self.assertEqual(called_events[1], ("biome", "dummy_biome"))


class TestModManager(unittest.TestCase):
    """Tests for ModManager mod loading, dependencies, error handling, and Lua parsing."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mods_path = Path(self.temp_dir)
        self.api = ModAPI()
        self.manager = ModManager(mods_dir=self.mods_path, api=self.api)

    def tearDown(self):
        self.api.reset_for_tests()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_discover_and_load_python_mod(self):
        """Create and load a full Python mod dynamically."""
        mod_dir = self.mods_path / "test_bio_mod"
        mod_dir.mkdir()

        mod_json = mod_dir / "mod.json"
        with open(mod_json, "w", encoding="utf-8") as f:
            json.dump({
                "id": "test_bio_mod",
                "name": "Test Bio Mod",
                "version": "1.2.0",
                "author": "Tester",
                "description": "Test mod for py-noita",
                "enabled": True,
            }, f)

        init_py = mod_dir / "init.py"
        with open(init_py, "w", encoding="utf-8") as f:
            f.write("""
from py_noita.weapons.gene import Gene, GeneType

def init(api):
    gene = Gene(
        id="MOD_TEST_GENE",
        name="Mod-Gen",
        gene_type=GeneType.PROJECTILE,
        description="Von Mod erzeugt",
    )
    api.register_gene(gene)
""")

        mods = self.manager.discover_mods()
        self.assertEqual(len(mods), 1)
        self.assertEqual(mods[0].id, "test_bio_mod")

        loaded = self.manager.load_all_mods()
        self.assertEqual(loaded, 1)
        self.assertTrue(mods[0].loaded)
        self.assertIn("MOD_TEST_GENE", GENE_DICT)

    def test_discover_and_parse_lua_mod(self):
        """Create and load a declarative Lua mod."""
        mod_dir = self.mods_path / "test_lua_mod"
        mod_dir.mkdir()

        mod_lua = mod_dir / "mod.lua"
        with open(mod_lua, "w", encoding="utf-8") as f:
            f.write("""
mod = {
    id = "lua_spore_mod",
    name = "Lua Spore Mod",
    version = "2.0.0",
    description = "Mod defined in Lua format",
}

register_gene {
    id = "LUA_TEST_ORB",
    name = "Lua Test Orb",
    desc = "Spawned from Lua directive",
    cost = 25.0,
    mana_drain = 18.0,
}
""")

        mods = self.manager.discover_mods()
        self.assertEqual(len(mods), 1)
        self.assertEqual(mods[0].id, "lua_spore_mod")
        self.assertEqual(mods[0].name, "Lua Spore Mod")

        loaded = self.manager.load_all_mods()
        self.assertEqual(loaded, 1)
        self.assertIn("LUA_TEST_ORB", GENE_DICT)

    def test_enable_disable_persistence(self):
        """Verify enabling and disabling mods persists in json config."""
        mod_dir = self.mods_path / "persist_mod"
        mod_dir.mkdir()
        with open(mod_dir / "mod.json", "w", encoding="utf-8") as f:
            json.dump({"id": "persist_mod", "name": "Persist Mod", "enabled": True}, f)

        self.manager.discover_mods()
        self.assertTrue(self.manager.mods["persist_mod"].enabled)

        # Disable
        self.manager.disable_mod("persist_mod")
        self.assertFalse(self.manager.mods["persist_mod"].enabled)

        # Re-create manager with same path and verify config retained
        new_manager = ModManager(mods_dir=self.mods_path, api=self.api)
        new_manager.discover_mods()
        self.assertFalse(new_manager.mods["persist_mod"].enabled)

    def test_resilience_to_broken_mod(self):
        """Verify a broken mod script does not crash the engine."""
        broken_dir = self.mods_path / "broken_mod"
        broken_dir.mkdir()
        with open(broken_dir / "mod.json", "w", encoding="utf-8") as f:
            json.dump({"id": "broken_mod", "name": "Broken Mod", "enabled": True}, f)
        with open(broken_dir / "init.py", "w", encoding="utf-8") as f:
            f.write("def init(api):\n    raise RuntimeError('Catastrophic mod bug')\n")

        self.manager.discover_mods()
        loaded = self.manager.load_all_mods()
        self.assertEqual(loaded, 0)
        self.assertFalse(self.manager.mods["broken_mod"].loaded)
        self.assertIsNotNone(self.manager.mods["broken_mod"].error)

    def test_sample_mod_integration(self):
        """Test the real repository sample mod in mods/sample_mod/."""
        sample_mod_path = Path("mods/sample_mod")
        if sample_mod_path.exists():
            mgr = ModManager(mods_dir=Path("mods"), api=self.api)
            mods = mgr.discover_mods()
            sample = next((m for m in mods if m.id == "sample_bio_mod"), None)
            self.assertIsNotNone(sample)
            success = mgr._load_mod(sample)
            self.assertTrue(success)
            self.assertIn("NECRO_TENTACLE", GENE_DICT)
            self.assertIn("TUMOR_CARRIER", CUSTOM_ENEMY_FACTORIES)
            self.assertTrue(any(s.strain_id == "STRAIN_NECROMANCER" for s in ALL_STRAINS))


if __name__ == "__main__":
    unittest.main()
