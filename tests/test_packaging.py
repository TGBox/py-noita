"""Unit tests for automated release packaging pipeline."""

import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest

from py_noita.system.packaging import (
    ALL_HIDDEN_IMPORTS,
    bundle_distribution,
    compute_sha256,
    create_release_notes,
    generate_nuitka_args,
    generate_pyinstaller_spec,
    run_pipeline,
)


class TestPackagingPipeline(unittest.TestCase):
    """Test suite for Py-Noita standalone executable packaging system."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.dist_path = Path(self.temp_dir) / "dist"
        self.build_path = Path(self.temp_dir) / "build"
        self.spec_path = Path(self.temp_dir) / "py_noita.spec"
        self.entry_point = Path(self.temp_dir) / "main.py"
        with open(self.entry_point, "w", encoding="utf-8") as f:
            f.write("print('Py-Noita')\n")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_hidden_imports_catalog(self):
        """Verify all critical engine packages and third-party libs are included in hidden imports."""
        self.assertIn("py_noita.main", ALL_HIDDEN_IMPORTS)
        self.assertIn("py_noita.simulation.falling_sand", ALL_HIDDEN_IMPORTS)
        self.assertIn("py_noita.weapons.gene", ALL_HIDDEN_IMPORTS)
        self.assertIn("py_noita.rendering.renderer", ALL_HIDDEN_IMPORTS)
        self.assertIn("py_noita.system.steamworks", ALL_HIDDEN_IMPORTS)
        self.assertIn("py_noita.system.mod_manager", ALL_HIDDEN_IMPORTS)
        self.assertIn("pygame", ALL_HIDDEN_IMPORTS)
        self.assertIn("numpy", ALL_HIDDEN_IMPORTS)
        self.assertIn("numba", ALL_HIDDEN_IMPORTS)

    def test_generate_pyinstaller_spec(self):
        """Verify PyInstaller spec generation."""
        spec_content = generate_pyinstaller_spec(
            self.spec_path,
            self.entry_point,
            self.dist_path,
            self.build_path,
            onefile=True,
            noconsole=True,
        )
        self.assertTrue(self.spec_path.exists())
        self.assertIn("Analysis", spec_content)
        self.assertIn("PYZ", spec_content)
        self.assertIn("EXE", spec_content)
        self.assertIn("name='PyNoita'", spec_content)
        self.assertIn("console=False", spec_content)

    def test_generate_nuitka_args(self):
        """Verify Nuitka compilation flags."""
        args = generate_nuitka_args(
            self.entry_point,
            self.dist_path,
            onefile=True,
            noconsole=True,
        )
        self.assertIn("--onefile", args)
        self.assertIn("--windows-disable-console", args)
        self.assertTrue(any("--output-dir" in a for a in args))
        self.assertIn(str(self.entry_point), args)

    def test_compute_sha256(self):
        """Verify SHA256 checksum computation."""
        sample_file = Path(self.temp_dir) / "sample.bin"
        content = b"Py-Noita-Bio-Horror-Test-Data"
        with open(sample_file, "wb") as f:
            f.write(content)

        expected = hashlib.sha256(content).hexdigest()
        computed = compute_sha256(sample_file)
        self.assertEqual(computed, expected)
        self.assertEqual(len(computed), 64)

    def test_create_release_notes(self):
        """Verify release notes formatting and contents."""
        self.dist_path.mkdir(parents=True, exist_ok=True)
        readme = create_release_notes(self.dist_path)
        self.assertTrue(readme.exists())
        with open(readme, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertIn("SYSTEMVORAUSSETZUNGEN", text)
        self.assertIn("STEUERUNG", text)
        self.assertIn("COMMUNITY-MODDING", text)

    def test_bundle_distribution(self):
        """Verify bundle creation including mods, saves placeholder, and SHA256SUMS.txt."""
        self.dist_path.mkdir(parents=True, exist_ok=True)
        # Create a mock binary
        mock_exe = self.dist_path / "PyNoita.exe"
        with open(mock_exe, "wb") as f:
            f.write(b"MOCK_EXE_DATA")

        meta = bundle_distribution(self.dist_path)
        self.assertTrue(Path(meta["readme"]).exists())
        self.assertTrue(Path(meta["manifest"]).exists())
        self.assertTrue((self.dist_path / "saves").exists())
        self.assertTrue((self.dist_path / "mods").exists())

        # Check manifest contents
        with open(meta["manifest"], "r", encoding="utf-8") as f:
            manifest_lines = f.readlines()
        self.assertGreater(len(manifest_lines), 0)
        self.assertTrue(any("PyNoita.exe" in line for line in manifest_lines))

    def test_dry_run_pipeline(self):
        """Verify full dry-run pipeline generates valid release artifacts without error."""
        success = run_pipeline(
            engine="pyinstaller",
            dry_run=True,
            clean=True,
            onefile=True,
            noconsole=True,
            dist_dir=self.dist_path,
            build_dir=self.build_path,
        )
        self.assertTrue(success)
        self.assertTrue((self.dist_path / "PyNoita.exe").exists())
        self.assertTrue((self.dist_path / "README_RELEASE.txt").exists())
        self.assertTrue((self.dist_path / "SHA256SUMS.txt").exists())
        self.assertTrue((self.dist_path / "mods").exists())


if __name__ == "__main__":
    unittest.main()
