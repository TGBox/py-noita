"""Settings and Configuration Manager for Py-Noita.

Provides robust, persistent storage and dynamic updating of:
- Keyboard & Mouse action bindings and remapping.
- Gamepad calibration (deadzone, stick sensitivity, inverted Y axis, button layout).
- Graphics preferences (window mode, resolution, v-sync, screen shake scale, particle density).
- Audio mixer levels (master, music, SFX, ambient environment).
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import pygame


DEFAULT_KEYBINDINGS: Dict[str, List[Union[int, str]]] = {
    "move_left": [pygame.K_a, pygame.K_LEFT],
    "move_right": [pygame.K_d, pygame.K_RIGHT],
    "hover": [pygame.K_w, pygame.K_UP, pygame.K_SPACE],
    "drop": [pygame.K_s, pygame.K_DOWN],
    "fire_cannula": ["MOUSE_1"],
    "discharge_gland": ["MOUSE_3"],
    "suck_liquid": [pygame.K_f],
    "interact": [pygame.K_e],
    "inventory": [pygame.K_TAB, pygame.K_i],
    "quicksave": [pygame.K_F5],
    "pause": [pygame.K_ESCAPE],
    "cannula_1": [pygame.K_1],
    "cannula_2": [pygame.K_2],
    "cannula_3": [pygame.K_3],
    "cannula_4": [pygame.K_4],
    "gland_1": [pygame.K_5],
    "gland_2": [pygame.K_6],
    "gland_3": [pygame.K_7],
    "gland_4": [pygame.K_8],
}

ACTION_LABELS_DE: Dict[str, str] = {
    "move_left": "Nach Links kriechen",
    "move_right": "Nach Rechts kriechen",
    "hover": "Schweben / Flagellen-Auftrieb",
    "drop": "Schneller Fall / Ducken",
    "fire_cannula": "Kanüle abfeuern (Primär)",
    "discharge_gland": "Drüsenflüssigkeit versprühen",
    "suck_liquid": "Flüssigkeit einsaugen",
    "interact": "Interagieren / Portal betreten",
    "inventory": "Genom-Kodex & Inventar",
    "quicksave": "Schnellspeichern (Mid-Run)",
    "pause": "Pause / Menü",
    "cannula_1": "Kanüle 1 ausrüsten",
    "cannula_2": "Kanüle 2 ausrüsten",
    "cannula_3": "Kanüle 3 ausrüsten",
    "cannula_4": "Kanüle 4 ausrüsten",
    "gland_1": "Organ-Drüse 1 auswählen",
    "gland_2": "Organ-Drüse 2 auswählen",
    "gland_3": "Organ-Drüse 3 auswählen",
    "gland_4": "Organ-Drüse 4 auswählen",
}


class SettingsManager:
    """Manages loading, saving, and accessing all user configurations."""

    def __init__(self, filepath: Optional[Path] = None):
        if filepath is None:
            self.filepath = Path("saves") / "settings.json"
        else:
            self.filepath = Path(filepath)

        # 1. Controls
        self.keybindings: Dict[str, List[Union[int, str]]] = {k: list(v) for k, v in DEFAULT_KEYBINDINGS.items()}

        # 2. Gamepad
        self.gamepad_deadzone: float = 0.15
        self.gamepad_sensitivity: float = 1.0
        self.gamepad_invert_y: bool = False
        self.gamepad_btn_jump: int = 0         # A
        self.gamepad_btn_inventory: int = 1    # B
        self.gamepad_btn_suck: int = 2         # X
        self.gamepad_btn_interact: int = 3     # Y

        # 3. Graphics
        self.window_mode: str = "WINDOWED"     # "WINDOWED", "FULLSCREEN", "BORDERLESS"
        self.resolution: List[int] = [1280, 720]
        self.vsync: bool = True
        self.screen_shake: float = 1.0         # 0.0 to 1.0 (0% - 100%)
        self.particle_density: float = 1.0     # 0.25 to 1.0 (25% - 100%)
        self.integer_scaling: bool = True      # Integer pixel scaling
        self.filter_mode: str = "CRISP"        # "CRISP" (nearest) or "SMOOTH" (bilinear)
        self.camera_zoom: str = "STANDARD"     # "NAH", "STANDARD", "WEIT"

        # 4. Audio
        self.master_volume: float = 0.8        # 0.0 to 1.0
        self.music_volume: float = 0.7         # 0.0 to 1.0
        self.sfx_volume: float = 0.8           # 0.0 to 1.0
        self.ambient_volume: float = 0.7       # 0.0 to 1.0

        # 5. Accessibility & Localization (i18n)
        self.language: str = "de"              # "de" or "en"
        self.photosensitivity_mode: bool = False
        self.hud_scale: float = 1.0            # 0.75x to 2.0x

        # Load existing if available
        self.load()
        from py_noita.system.localization import loc
        loc.set_language(self.language)

    def reset_to_defaults(self) -> None:
        """Reset all parameters to factory defaults."""
        self.keybindings = {k: list(v) for k, v in DEFAULT_KEYBINDINGS.items()}
        self.gamepad_deadzone = 0.15
        self.gamepad_sensitivity = 1.0
        self.gamepad_invert_y = False
        self.gamepad_btn_jump = 0
        self.gamepad_btn_inventory = 1
        self.gamepad_btn_suck = 2
        self.gamepad_btn_interact = 3
        self.window_mode = "WINDOWED"
        self.resolution = [1280, 720]
        self.vsync = True
        self.screen_shake = 1.0
        self.particle_density = 1.0
        self.integer_scaling = True
        self.filter_mode = "CRISP"
        self.camera_zoom = "STANDARD"
        self.master_volume = 0.8
        self.music_volume = 0.7
        self.sfx_volume = 0.8
        self.ambient_volume = 0.7
        self.language = "de"
        self.photosensitivity_mode = False
        self.hud_scale = 1.0
        from py_noita.system.localization import loc
        loc.set_language(self.language)
        self.save()

    def rebind_action(self, action: str, input_value: Union[int, str]) -> None:
        """Assign a new key or mouse button to an action (replaces first slot)."""
        if action in self.keybindings:
            self.keybindings[action] = [input_value]
            self.save()

    def get_action_display_name(self, action: str) -> str:
        """Get formatted German description of the action."""
        return ACTION_LABELS_DE.get(action, action.replace("_", " ").title())

    def get_binding_display_str(self, action: str) -> str:
        """Get human-readable key / mouse label for an action."""
        bindings = self.keybindings.get(action, [])
        if not bindings:
            return "NICHT BELEGT"

        labels = []
        for b in bindings:
            if isinstance(b, str):
                if b == "MOUSE_1":
                    labels.append("Maus Links")
                elif b == "MOUSE_2":
                    labels.append("Maus Mitte")
                elif b == "MOUSE_3":
                    labels.append("Maus Rechts")
                else:
                    labels.append(b)
            elif isinstance(b, int):
                name = pygame.key.name(b).upper()
                if b == pygame.K_SPACE:
                    name = "LEERTASTE"
                elif b == pygame.K_ESCAPE:
                    name = "ESC"
                elif b == pygame.K_RETURN:
                    name = "ENTER"
                elif b == pygame.K_TAB:
                    name = "TAB"
                elif b == pygame.K_UP:
                    name = "PFEIL HOCH"
                elif b == pygame.K_DOWN:
                    name = "PFEIL RUNTER"
                elif b == pygame.K_LEFT:
                    name = "PFEIL LINKS"
                elif b == pygame.K_RIGHT:
                    name = "PFEIL RECHTS"
                labels.append(name)
        return " / ".join(labels)

    def is_action_pressed(self, action: str, pressed_keys, mouse_buttons) -> bool:
        """Check if any bound key or mouse button for this action is active."""
        bindings = self.keybindings.get(action, [])
        for b in bindings:
            if isinstance(b, int):
                if 0 <= b < len(pressed_keys) and pressed_keys[b]:
                    return True
            elif isinstance(b, str):
                if b == "MOUSE_1" and mouse_buttons[0]:
                    return True
                elif b == "MOUSE_2" and len(mouse_buttons) > 1 and mouse_buttons[1]:
                    return True
                elif b == "MOUSE_3" and len(mouse_buttons) > 2 and mouse_buttons[2]:
                    return True
        return False

    def is_action_event(self, action: str, event: pygame.event.Event) -> bool:
        """Check if a specific KEYDOWN or MOUSEBUTTONDOWN event triggers the action."""
        bindings = self.keybindings.get(action, [])
        if event.type == pygame.KEYDOWN:
            for b in bindings:
                if isinstance(b, int) and b == event.key:
                    return True
        elif event.type == pygame.MOUSEBUTTONDOWN:
            for b in bindings:
                if isinstance(b, str):
                    if b == "MOUSE_1" and event.button == 1:
                        return True
                    elif b == "MOUSE_2" and event.button == 2:
                        return True
                    elif b == "MOUSE_3" and event.button == 3:
                        return True
        return False

    def save(self) -> bool:
        """Serialize settings to JSON disk file atomically."""
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "version": 1,
                "controls": self.keybindings,
                "gamepad": {
                    "deadzone": self.gamepad_deadzone,
                    "sensitivity": self.gamepad_sensitivity,
                    "invert_y": self.gamepad_invert_y,
                    "btn_jump": self.gamepad_btn_jump,
                    "btn_inventory": self.gamepad_btn_inventory,
                    "btn_suck": self.gamepad_btn_suck,
                    "btn_interact": self.gamepad_btn_interact,
                },
                "graphics": {
                    "window_mode": self.window_mode,
                    "resolution": self.resolution,
                    "vsync": self.vsync,
                    "screen_shake": self.screen_shake,
                    "particle_density": self.particle_density,
                    "integer_scaling": self.integer_scaling,
                    "filter_mode": self.filter_mode,
                    "camera_zoom": self.camera_zoom,
                },
                "audio": {
                    "master_volume": self.master_volume,
                    "music_volume": self.music_volume,
                    "sfx_volume": self.sfx_volume,
                    "ambient_volume": self.ambient_volume,
                },
                "accessibility": {
                    "language": self.language,
                    "photosensitivity_mode": self.photosensitivity_mode,
                    "hud_scale": self.hud_scale,
                },
            }
            tmp_path = self.filepath.with_suffix(".json.tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            if self.filepath.exists():
                self.filepath.unlink()
            tmp_path.replace(self.filepath)
            return True
        except Exception as e:
            print(f"[SettingsManager] Save failed: {e}")
            return False

    def load(self) -> bool:
        """Read settings from JSON disk file if exists."""
        if not self.filepath.exists():
            return False
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "controls" in data:
                # Merge with defaults so new actions aren't missing
                for k, v in data["controls"].items():
                    self.keybindings[k] = v

            if "gamepad" in data:
                gp = data["gamepad"]
                self.gamepad_deadzone = float(gp.get("deadzone", 0.15))
                self.gamepad_sensitivity = float(gp.get("sensitivity", 1.0))
                self.gamepad_invert_y = bool(gp.get("invert_y", False))
                self.gamepad_btn_jump = int(gp.get("btn_jump", 0))
                self.gamepad_btn_inventory = int(gp.get("btn_inventory", 1))
                self.gamepad_btn_suck = int(gp.get("btn_suck", 2))
                self.gamepad_btn_interact = int(gp.get("btn_interact", 3))

            if "graphics" in data:
                gr = data["graphics"]
                self.window_mode = str(gr.get("window_mode", "WINDOWED"))
                self.resolution = list(gr.get("resolution", [1280, 720]))
                self.vsync = bool(gr.get("vsync", True))
                self.screen_shake = float(gr.get("screen_shake", 1.0))
                self.particle_density = float(gr.get("particle_density", 1.0))
                self.integer_scaling = bool(gr.get("integer_scaling", True))
                self.filter_mode = str(gr.get("filter_mode", "CRISP"))
                self.camera_zoom = str(gr.get("camera_zoom", "STANDARD"))

            if "audio" in data:
                au = data["audio"]
                self.master_volume = float(au.get("master_volume", 0.8))
                self.music_volume = float(au.get("music_volume", 0.7))
                self.sfx_volume = float(au.get("sfx_volume", 0.8))
                self.ambient_volume = float(au.get("ambient_volume", 0.7))

            if "accessibility" in data:
                acc = data["accessibility"]
                self.language = str(acc.get("language", "de"))
                self.photosensitivity_mode = bool(acc.get("photosensitivity_mode", False))
                self.hud_scale = float(acc.get("hud_scale", 1.0))
                from py_noita.system.localization import loc
                loc.set_language(self.language)

            return True
        except Exception as e:
            print(f"[SettingsManager] Load failed: {e}")
            return False
