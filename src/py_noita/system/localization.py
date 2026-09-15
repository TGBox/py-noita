"""Localization (i18n) system for Py-Noita.

Supports complete bilingual German ('de') and English ('en') text catalog for:
- Menus, settings, UI prompts, and HUD labels.
- 8 Biomes and Holy Mountain Incubation Nodes.
- Symbiote strains, descriptions, and unlock costs.
- Endings, epilogues, and cosmic achievements.
- Materials, chemical reagents, and visceral organs.
- Gene names and biological tooltips.
"""

from typing import Any, Dict, Optional, Tuple


TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # -------------------------------------------------------------------------
    # MAIN MENU & NAVIGATION
    # -------------------------------------------------------------------------
    "menu_title": {
        "de": "PY-NOITA // MIKROKOSMOS",
        "en": "PY-NOITA // MICROCOSM",
    },
    "menu_subtitle": {
        "de": "Jeder Pixel physikalisch simuliert  •  Bio-Horror Deckbuilder",
        "en": "Every pixel physically simulated  •  Bio-Horror Deckbuilder",
    },
    "menu_mutagen_balance": {
        "de": "Mutagen-Essenz (Labor-Konto): {amount} M",
        "en": "Mutagen Essence (Lab Balance): {amount} M",
    },
    "menu_resume_run": {
        "de": "[C] RUN FORTSETZEN: {biome} (HP: {hp}/{max_hp}) • Seed: {seed}",
        "en": "[C] RESUME RUN: {biome} (HP: {hp}/{max_hp}) • Seed: {seed}",
    },
    "menu_start_run": {
        "de": "[LEERTASTE] Abstieg in den Wirt beginnen",
        "en": "[SPACE] Begin Descent into Host",
    },
    "menu_unlock_strain": {
        "de": "[U] Freischalten ({cost} Mutagen)",
        "en": "[U] Unlock Strain ({cost} Mutagen)",
    },
    "menu_seed_prompt": {
        "de": "WELT-SEED: [ {seed} ]  •  [R] Zufall  •  [S] Eingeben",
        "en": "WORLD SEED: [ {seed} ]  •  [R] Random  •  [S] Enter Seed",
    },
    "menu_seed_input": {
        "de": "WELT-SEED EINGEBEN: [ {seed}_ ]  (ENTER = Bestätigen, ESC = Abbruch)",
        "en": "ENTER WORLD SEED: [ {seed}_ ]  (ENTER = Confirm, ESC = Cancel)",
    },
    "menu_footer_controls": {
        "de": "[O] Optionen  |  [F1] Auflösung  |  [F11] Vollbild  |  WASD + Maus",
        "en": "[O] Options  |  [F1] Resolution  |  [F11] Fullscreen  |  WASD + Mouse",
    },
    "quicksave_saved": {
        "de": "[F5 QUICKSAVE GESPEICHERT]",
        "en": "[F5 QUICKSAVE SAVED]",
    },

    # -------------------------------------------------------------------------
    # SETTINGS & ACCESSIBILITY
    # -------------------------------------------------------------------------
    "settings_title": {
        "de": "BIO-SYNTHESE KONFIGURATION & SYSTEM",
        "en": "BIO-SYNTHESIS SYSTEM & CONFIGURATION",
    },
    "tab_controls": {
        "de": "1. TASTENBELEGUNG",
        "en": "1. CONTROLS",
    },
    "tab_gamepad": {
        "de": "2. GAMEPAD",
        "en": "2. GAMEPAD",
    },
    "tab_graphics": {
        "de": "3. GRAFIK & ACCESSIBILITY",
        "en": "3. GRAPHICS & ACCESSIBILITY",
    },
    "tab_audio": {
        "de": "4. AUDIO",
        "en": "4. AUDIO",
    },
    "opt_language": {
        "de": "Sprache / Language",
        "en": "Language / Sprache",
    },
    "opt_photosensitivity": {
        "de": "Photosensitivität (Blitzlicht-Schutz)",
        "en": "Photosensitivity (Flashing Lights Shield)",
    },
    "opt_hud_scale": {
        "de": "HUD- & Schriftgröße (Skalierung)",
        "en": "HUD & Text Scale (1080p - 4K)",
    },
    "opt_screen_shake": {
        "de": "Bildschirm-Wackeln (Screen Shake)",
        "en": "Screen Shake Trauma",
    },
    "opt_particle_density": {
        "de": "Partikeldichte (Simulation)",
        "en": "Particle Density",
    },
    "opt_window_mode": {
        "de": "Fenstermodus",
        "en": "Window Mode",
    },
    "opt_resolution": {
        "de": "Basis-Auflösung",
        "en": "Base Resolution",
    },
    "opt_vsync": {
        "de": "Vertikale Synchronisation (V-Sync)",
        "en": "Vertical Sync (V-Sync)",
    },
    "opt_master_vol": {
        "de": "Master-Lautstärke",
        "en": "Master Volume",
    },
    "opt_music_vol": {
        "de": "Musik-Lautstärke (Adaptiver Soundtrack)",
        "en": "Music Volume (Adaptive Soundtrack)",
    },
    "opt_sfx_vol": {
        "de": "Soundeffekte (SFX-Arsenal)",
        "en": "Sound Effects (SFX Arsenal)",
    },
    "opt_ambient_vol": {
        "de": "Umgebungs-Akustik & Hall",
        "en": "Ambient Acoustics & Reverb",
    },
    "opt_audio_test": {
        "de": "Audio-Testton abspielen",
        "en": "Play Audio Test Sound",
    },
    "state_on": {
        "de": "AKTIV",
        "en": "ENABLED",
    },
    "state_off": {
        "de": "DEAKTIVIERT",
        "en": "DISABLED",
    },

    # -------------------------------------------------------------------------
    # HUD & GAMEPLAY LABELS
    # -------------------------------------------------------------------------
    "hud_depth": {
        "de": "TIEFE: {depth}m",
        "en": "DEPTH: {depth}m",
    },
    "hud_biomass": {
        "de": "BIOMASSE",
        "en": "BIOMASS",
    },
    "hud_gland": {
        "de": "DRÜSE",
        "en": "GLAND",
    },
    "hud_cannula": {
        "de": "KANÜLE",
        "en": "CANNULA",
    },
    "hud_empty": {
        "de": "LEER",
        "en": "EMPTY",
    },

    # -------------------------------------------------------------------------
    # BIOMES
    # -------------------------------------------------------------------------
    "biome_epidermis": {
        "de": "Epidermis & Cutis",
        "en": "Epidermis & Cutis",
    },
    "biome_muscle": {
        "de": "Vaskulärer Muskel",
        "en": "Vascular Muscle",
    },
    "biome_acid": {
        "de": "Magensäure-Kavernen",
        "en": "Gastric Acid Caverns",
    },
    "biome_bile": {
        "de": "Toxische Gallen-Lagune",
        "en": "Toxic Bile Lagoon",
    },
    "biome_lung": {
        "de": "Infizierte Lunge",
        "en": "Infected Lung",
    },
    "biome_bone": {
        "de": "Knochen-Katakomben",
        "en": "Bone Catacombs",
    },
    "biome_nerve": {
        "de": "Rückenmark & Nerven",
        "en": "Spinal Cord & Nerves",
    },
    "biome_core": {
        "de": "Primordiales Zentrum",
        "en": "Primordial Center",
    },
    "biome_incubation": {
        "de": "Inkubations-Knoten",
        "en": "Incubation Sanctuary",
    },

    # -------------------------------------------------------------------------
    # ENDINGS
    # -------------------------------------------------------------------------
    "ending_host_death_title": {
        "de": "WIRTS-KOLLAPS (Nekrotischer Sieg)",
        "en": "HOST COLLAPSE (Necrotic Victory)",
    },
    "ending_host_death_desc": {
        "de": "Der Wirtskörper erliegt der zersetzenden Parasiten-Invasion. Säure und Fäulnis fluten die Organe.",
        "en": "The host organism succumbs to parasitic invasion. Acid and putrefaction drown the hollow organs.",
    },
    "ending_symbiosis_title": {
        "de": "HARMONISCHE SYMBIOSE",
        "en": "HARMONIC SYMBIOSIS",
    },
    "ending_symbiosis_desc": {
        "de": "Parasit und Wirt verschmelzen zu einer neuartigen, unsterblichen Lebensform in vollkommener Einheit.",
        "en": "Parasite and host fuse into a novel immortal chimeric lifeform in perfect cellular unity.",
    },
    "ending_cosmic_title": {
        "de": "KOSMISCHE METAMORPHOSE (Wahres Ende)",
        "en": "COSMIC METAMORPHOSIS (True Ending)",
    },
    "ending_cosmic_desc": {
        "de": "Mit allen genetischen Relikten durchbrichst du die Fleischhülle und entweichst als kosmisches Wesen in die Unendlichkeit.",
        "en": "Bearing all ancient genetic relics, you breach the flesh shell and ascend into infinity as a cosmic entity.",
    },
}


class Localization:
    """Manages active language and string lookups."""

    def __init__(self, default_lang: str = "de"):
        self.language: str = default_lang if default_lang in ("de", "en") else "de"

    def set_language(self, lang_code: str) -> None:
        """Switch active locale ('de' or 'en')."""
        if lang_code in ("de", "en"):
            self.language = lang_code

    def get_language(self) -> str:
        return self.language

    def t(self, key: str, **kwargs) -> str:
        """Retrieve translated text string for key, formatting with kwargs."""
        if key not in TRANSLATIONS:
            return key
        entry = TRANSLATIONS[key]
        text = entry.get(self.language, entry.get("de", key))
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text

    def translate_biome_name(self, biome_idx: int) -> str:
        """Get translated biome name by index (0 to 7, or 8 for incubation)."""
        mapping = {
            0: "biome_epidermis",
            1: "biome_muscle",
            2: "biome_acid",
            3: "biome_bile",
            4: "biome_lung",
            5: "biome_bone",
            6: "biome_nerve",
            7: "biome_core",
            8: "biome_incubation",
        }
        key = mapping.get(biome_idx, "biome_epidermis")
        return self.t(key)

    def translate_material(self, mat_id: int) -> str:
        """Translate material ID to localized display name."""
        names = {
            0: {"de": "Luft", "en": "Air"},
            1: {"de": "Gewebe", "en": "Tissue"},
            2: {"de": "Knochen", "en": "Bone"},
            3: {"de": "Chitin", "en": "Chitin"},
            4: {"de": "Wandknochen", "en": "Wall Bone"},
            5: {"de": "Nervenfaser", "en": "Nerve Fiber"},
            6: {"de": "Tentakelfleisch", "en": "Tentacle Flesh"},
            10: {"de": "Sporen", "en": "Spores"},
            11: {"de": "Eier", "en": "Eggs"},
            12: {"de": "Asche", "en": "Ash"},
            13: {"de": "Knochensplitter", "en": "Bone Shard"},
            14: {"de": "Gold / Erz", "en": "Gold / Ore"},
            20: {"de": "Vitales Blut", "en": "Vital Blood"},
            21: {"de": "Magensäure", "en": "Gastric Acid"},
            22: {"de": "Ätzende Galle", "en": "Corrosive Bile"},
            23: {"de": "Lymphe", "en": "Lymph Fluid"},
            24: {"de": "Eiter", "en": "Pus"},
            25: {"de": "Reines Mutagen", "en": "Pure Mutagen"},
            26: {"de": "Verdauungswasser", "en": "Digestive Water"},
            30: {"de": "Biogas", "en": "Biogas"},
            31: {"de": "Toxischer Dampf", "en": "Toxic Vapor"},
            32: {"de": "Rauch", "en": "Smoke"},
            40: {"de": "Bio-Feuer", "en": "Bio-Fire"},
            41: {"de": "Korrosion", "en": "Corrosion"},
        }
        entry = names.get(mat_id, {"de": "Unbekannt", "en": "Unknown"})
        return entry.get(self.language, entry.get("de", "Unbekannt"))


# Global singleton instance for easy import and access
loc = Localization()
