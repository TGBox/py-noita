# -*- mode: python ; coding: utf-8 -*-
# Py-Noita Automated PyInstaller Spec File

block_cipher = None

a = Analysis(
    ['C:/Users/DaniBani/Documents/VisualStudioCodeProjects/py-noita/src/py_noita/main.py'],
    pathex=['C:/Users/DaniBani/Documents/VisualStudioCodeProjects/py-noita/src'],
    binaries=[],
    datas=[],
    hiddenimports=['py_noita', 'py_noita.config', 'py_noita.main', 'py_noita.simulation', 'py_noita.simulation.materials', 'py_noita.simulation.grid', 'py_noita.simulation.sand_simulation', 'py_noita.simulation.spatial_hash', 'py_noita.simulation.transmutation', 'py_noita.entities', 'py_noita.entities.player', 'py_noita.entities.enemy', 'py_noita.entities.rigid_body', 'py_noita.entities.ik_rig', 'py_noita.entities.corpse', 'py_noita.weapons', 'py_noita.weapons.gene', 'py_noita.weapons.projectile', 'py_noita.weapons.cannula', 'py_noita.weapons.deck_evaluator', 'py_noita.world', 'py_noita.world.biome', 'py_noita.world.generator', 'py_noita.world.incubation_node', 'py_noita.world.secrets', 'py_noita.world.streamer', 'py_noita.rendering', 'py_noita.rendering.renderer', 'py_noita.rendering.camera', 'py_noita.rendering.lighting', 'py_noita.rendering.particles', 'py_noita.rendering.shaders', 'py_noita.rendering.liquid_shaders', 'py_noita.ui', 'py_noita.ui.hud', 'py_noita.ui.editor', 'py_noita.ui.hover_info', 'py_noita.ui.game_over', 'py_noita.ui.codex', 'py_noita.ui.settings_menu', 'py_noita.audio', 'py_noita.audio.manager', 'py_noita.audio.sound_catalog', 'py_noita.audio.adaptive_music', 'py_noita.audio.spatial', 'py_noita.audio.acoustics', 'py_noita.system', 'py_noita.system.save_manager', 'py_noita.system.settings_manager', 'py_noita.system.localization', 'py_noita.system.steamworks', 'py_noita.system.mod_api', 'py_noita.system.mod_manager', 'pygame', 'pygame.font', 'pygame.image', 'pygame.mixer', 'pygame.surface', 'numpy', 'numba', 'pymunk', 'OpenGL', 'OpenGL.GL'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'test'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries if True else [],
    a.zipfiles if True else [],
    a.datas if True else [],
    [],
    name='PyNoita',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
