"""Automated Standalone Single-File Release-Build Pipeline for Py-Noita.

Entry point script delegating to py_noita.system.packaging.
"""

from py_noita.system.packaging import (
    ALL_HIDDEN_IMPORTS,
    DEFAULT_BUILD,
    DEFAULT_DIST,
    ENTRY_POINT,
    PROJECT_ROOT,
    SPEC_FILE,
    bundle_distribution,
    compute_sha256,
    create_release_notes,
    generate_nuitka_args,
    generate_pyinstaller_spec,
    main,
    run_pipeline,
)

__all__ = [
    "ALL_HIDDEN_IMPORTS",
    "DEFAULT_BUILD",
    "DEFAULT_DIST",
    "ENTRY_POINT",
    "PROJECT_ROOT",
    "SPEC_FILE",
    "bundle_distribution",
    "compute_sha256",
    "create_release_notes",
    "generate_nuitka_args",
    "generate_pyinstaller_spec",
    "main",
    "run_pipeline",
]

if __name__ == "__main__":
    main()
