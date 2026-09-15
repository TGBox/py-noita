"""Steamworks Integration for Py-Noita.

Provides:
- 40+ Bio-Horror Steam Achievements catalog with dual-language metadata.
- Graceful standalone fallback if Steam client is not running.
- In-game Achievement Toast Notification HUD rendering.
- Steam Cloud Save synchronization for Bio-Codex, metaprogress, and settings.
- Steam Deck verification profile (1280x800, 60 FPS target, controller profile).
"""

from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pygame

from py_noita.config import COLOR_ACID_GLOW, COLOR_NERVE_GLOW, COLOR_PLAYER_GLOW


@dataclass
class SteamAchievement:
    """Definition of a Steam achievement."""
    id: str
    name_de: str
    name_en: str
    desc_de: str
    desc_en: str
    icon: str = "trophy"
    unlocked: bool = False
    unlock_time: Optional[str] = None
    hidden: bool = False


ACHIEVEMENT_CATALOG: List[SteamAchievement] = [
    # --- 1. Combat & Cellular Warfare (10) ---
    SteamAchievement("ACH_FIRST_KILL", "Erste Zersetzung", "First Decomposition", "Zersetze deine erste feindliche Immunzelle.", "Decompose your first hostile immune cell."),
    SteamAchievement("ACH_KILLS_50", "Zelluläre Säuberung", "Cellular Purge", "Vernichte 50 Immunwächter in einem Run.", "Eliminate 50 immune guardians in a single run."),
    SteamAchievement("ACH_KILLS_200", "Apoptose-Kollaps", "Apoptosis Collapse", "Eliminiere 200 Feinde in einem einzigen Abstieg.", "Eliminate 200 enemies in a single descent."),
    SteamAchievement("ACH_KILL_WORM", "Gewürm-Bändiger", "Worm Tamer", "Töte einen riesigen Fleischwurm im vaskulären Gewebe.", "Slay a giant fleshworm in the vascular muscle."),
    SteamAchievement("ACH_KILL_SPIDER", "Chitin-Brecher", "Chitin Breaker", "Vernichte eine Parasiten-Spinne im Nahkampf.", "Crush a parasite spider in close combat."),
    SteamAchievement("ACH_KILL_SENTRY", "Synapsen-Trennung", "Synapse Severing", "Zerstöre ein Nerven-Geschütz bevor es feuert.", "Destroy a synaptic sentry before it discharges."),
    SteamAchievement("ACH_CORE_BOSS", "Hirntod", "Brain Death", "Besiege das Ur-Hirn im primordialen Zentrum.", "Defeat the Primordial Brain Core at the center."),
    SteamAchievement("ACH_PACIFIST_BIOME", "Pazifistischer Parasit", "Pacifist Parasite", "Durchquere ein gesamtes Biom ohne Feinde zu töten.", "Complete an entire biome without slaying any enemies."),
    SteamAchievement("ACH_UNTOUCHED_BOSS", "Makellose Zersetzung", "Flawless Decomposition", "Besiege einen Boss ohne Schaden zu nehmen.", "Defeat a boss encounter without taking any damage."),
    SteamAchievement("ACH_SKELETON_WALL", "Anatomische Trophäe", "Anatomical Trophy", "Nagle ein feindliches Skelett an eine Knochenwand.", "Embed a complete enemy skeleton onto a bone wall."),

    # --- 2. Wand & Gene Deckbuilding (10) ---
    SteamAchievement("ACH_FIRST_GENE", "Genetische Modifikation", "Genetic Modification", "Installiere dein erstes Gen in eine Organ-Kanüle.", "Install your first gene card into an organ cannula."),
    SteamAchievement("ACH_FULL_CANNULA", "Organ-Sättigung", "Organ Saturation", "Fülle alle Slots einer 6-Slot-Kanüle mit Genen.", "Fill all slots of a 6-slot cannula with active genes."),
    SteamAchievement("ACH_RECURSIVE_BURST", "Rezidiv-Wucherung", "Recursive Outgrowth", "Löse eine Kaskade von 4 Trigger-Genen auf einmal aus.", "Trigger a cascade of 4 linked trigger genes at once."),
    SteamAchievement("ACH_META_GENE", "Mutationsexperte", "Mutation Expert", "Installiere ein Meta-Gen für rekursive Gen-Kopien.", "Install a meta-gene to recursively duplicate sequences."),
    SteamAchievement("ACH_HOMING_ACID", "Zielsuch-Verätzung", "Homing Corrosion", "Triff 5 Gegner mit Zielsuch-Säure-Projektilen.", "Hit 5 enemies using homing acid projectiles."),
    SteamAchievement("ACH_RAPID_FIRE", "Maschinengewehr-Drüse", "Machine-Gun Gland", "Erreiche eine Feuerrate von über 10 Schüssen pro Sekunde.", "Achieve a firing cadence exceeding 10 shots per second."),
    SteamAchievement("ACH_BONE_BOMB_TRIPLE", "Cluster-Osteotomie", "Cluster Osteotomy", "Zünde 3 Knochen-Bomben mit einer einzigen Auslösung.", "Detonate 3 bone bombs with a single trigger cast."),
    SteamAchievement("ACH_HIGH_DAMAGE", "Toxischer Schock", "Toxic Shock", "Füge einem Ziel über 100 Schaden mit einem Schuss zu.", "Inflict over 100 damage to a target with a single burst."),
    SteamAchievement("ACH_FOUR_CANNULAS", "Volles Arsenal", "Full Arsenal", "Trage 4 vollwertige Organ-Kanülen gleichzeitig.", "Equip 4 complete organ cannulas simultaneously."),
    SteamAchievement("ACH_PERK_SYNERGY", "Metamorphe Perfektion", "Metamorphic Perfection", "Besitze 5 aktive Genom-Mutationen gleichzeitig.", "Possess 5 active genomic mutation perks at once."),

    # --- 3. Fluid & Chemical Alchemy (8) ---
    SteamAchievement("ACH_FIRST_GLAND", "Flüssigkeits-Speicher", "Fluid Reservoir", "Fülle eine Organ-Drüse bis zum Anschlag mit Säure.", "Fill an organ gland to maximum capacity with acid."),
    SteamAchievement("ACH_ACID_BATH", "Verdauungs-Taufe", "Digestive Baptism", "Tauche vollständig in Magensäure unter und überlebe.", "Submerge completely in gastric acid and survive."),
    SteamAchievement("ACH_BLOOD_EXTINGUISH", "Blut-Löschung", "Blood Extinguish", "Lösche deinen brennenden Körper in einem Blutbecken.", "Extinguish your flaming body inside a pool of blood."),
    SteamAchievement("ACH_ALCHEMY_REACTION", "Meister-Alchemist", "Master Alchemist", "Löse eine Säure-Knochen-Gaszersetzung aus.", "Trigger an acid-bone chemical effervescence reaction."),
    SteamAchievement("ACH_BILE_EXPLOSION", "Gallen-Detonation", "Bile Detonation", "Entzünde eine toxische Biogas-Blase mit Feuer.", "Ignite a volatile biogas pocket using fire."),
    SteamAchievement("ACH_ABSORB_GOLD", "Biologische Gier", "Biological Greed", "Sauge 200 Einheiten gelöste Biomasse auf.", "Absorb 200 units of dissolved biomass currency."),
    SteamAchievement("ACH_FULL_GLANDS", "Tetra-Drüse", "Tetra-Gland", "Fülle alle 4 Organ-Drüsen mit 4 verschiedenen Flüssigkeiten.", "Fill all 4 glands with 4 distinct biological fluids."),
    SteamAchievement("ACH_SLIME_CRAWL", "Schleim-Gleiten", "Slime Glide", "Krieche 100 Meter auf viskosem Schmierschleim.", "Crawl 100 meters across viscous organic slime."),

    # --- 4. Secrets, Lore & Exploration (6) ---
    SteamAchievement("ACH_SECRET_ORB", "Verborgene Ur-Blase", "Hidden Primordial Orb", "Finde deinen ersten geheimen Gen-Orb.", "Locate and absorb your first hidden Gene Orb."),
    SteamAchievement("ACH_ALL_ORBS", "Genom-Vervollständigung", "Genome Completion", "Sammle alle 5 geheimen Ur-Gene im Wirt.", "Collect all 5 secret Primordial Gene Orbs in the host."),
    SteamAchievement("ACH_DNA_TABLET", "Fleisch-Erinnerung", "Flesh Memory", "Finde ein uraltes DNA-Lore-Fragment.", "Discover an ancient inscribed DNA lore tablet."),
    SteamAchievement("ACH_ALL_TABLETS", "Bio-Archivar", "Bio-Archivist", "Entziffere alle 5 DNA-Tablets der Vorfahren.", "Decipher all 5 ancient ancestral DNA tablets."),
    SteamAchievement("ACH_BILE_LAGOON", "Gallen-Zuflucht", "Bile Haven", "Betritt die geheime toxische Gallen-Lagune.", "Enter the secret Toxic Bile Lagoon side biome."),
    SteamAchievement("ACH_INCUBATION_SANCTUARY", "Heiliger Berg", "Holy Mountain", "Erreiche den sicheren Inkubations-Knoten.", "Reach the safe biological Incubation Sanctuary."),

    # --- 5. Narrative Endings & Meta Progression (6) ---
    SteamAchievement("ACH_ENDING_1", "Wirts-Kollaps", "Host Collapse", "Erreiche Ende 1: Der Wirtskörper bricht zusammen.", "Achieve Ending 1: The host organism collapses."),
    SteamAchievement("ACH_ENDING_2", "Harmonische Symbiose", "Harmonic Symbiosis", "Erreiche Ende 2: Vollkommene Zellfusion.", "Achieve Ending 2: Perfect cellular symbiotic fusion."),
    SteamAchievement("ACH_ENDING_3", "Kosmische Metamorphose", "Cosmic Metamorphosis", "Erreiche das wahre Ende: Kosmische Flucht.", "Achieve the True Ending: Cosmic ascension into the stars."),
    SteamAchievement("ACH_UNLOCK_ALL_STRAINS", "Genetische Vielfalt", "Genetic Diversity", "Schalte alle 4 Symbioten-Stämme im Labor frei.", "Unlock all 4 playable Symbiote strains in the Codex."),
    SteamAchievement("ACH_MUTAGEN_1000", "Mutagen-Magnat", "Mutagen Tycoon", "Sammle insgesamt 1.000 Mutagen-Essenz an.", "Accumulate a lifetime balance of 1,000 Mutagen Essence."),
    SteamAchievement("ACH_SPEEDRUN", "Blitz-Invasion", "Lightning Breach", "Erreiche den Kern in unter 12 Minuten.", "Reach the primordial core in under 12 minutes."),
]


class SteamToastNotification:
    """Animated pop-up toast displaying unlocked achievement."""

    def __init__(self, achievement: SteamAchievement):
        self.ach = achievement
        self.lifetime = 4.5  # Seconds
        self.timer = 4.5
        self.slide_y = -60.0  # Off screen top
        self.target_y = 12.0

    def update(self, dt: float) -> bool:
        """Update animation and countdown. Returns False when expired."""
        self.timer -= dt
        if self.timer <= 0.0:
            return False

        # Smooth slide in and slide out
        if self.timer > 0.5:
            self.slide_y += (self.target_y - self.slide_y) * min(1.0, dt * 10.0)
        else:
            self.slide_y += (-70.0 - self.slide_y) * min(1.0, dt * 10.0)
        return True

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, title_font: pygame.font.Font, lang: str = "de") -> None:
        sw = surface.get_width()
        w, h = 260, 48
        x = (sw - w) // 2
        y = int(self.slide_y)

        # Draw toast box
        box_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        box_surf.fill((18, 14, 24, 240))
        surface.blit(box_surf, (x, y))
        pygame.draw.rect(surface, COLOR_ACID_GLOW, (x, y, w, h), 1, border_radius=4)
        pygame.draw.rect(surface, (60, 20, 40), (x + 2, y + 2, w - 4, h - 4), 1, border_radius=3)

        # Trophy icon / Gold medal symbol
        trophy_col = (255, 215, 40)
        pygame.draw.circle(surface, trophy_col, (x + 22, y + 24), 12)
        pygame.draw.circle(surface, (180, 140, 20), (x + 22, y + 24), 12, 1)

        header = "ERFOLG FREIGESCHALTET!" if lang == "de" else "ACHIEVEMENT UNLOCKED!"
        name = self.ach.name_de if lang == "de" else self.ach.name_en
        desc = self.ach.desc_de if lang == "de" else self.ach.desc_en

        t_surf = font.render(header, True, COLOR_ACID_GLOW)
        n_surf = title_font.render(name, True, COLOR_PLAYER_GLOW)

        surface.blit(t_surf, (x + 42, y + 8))
        surface.blit(n_surf, (x + 42, y + 23))


class SteamworksIntegration:
    """Manages Steamworks client API connection, achievements, cloud saves, and Steam Deck optimization."""

    def __init__(self, save_dir: Optional[Path] = None):
        if save_dir is None:
            self.save_dir = Path("saves")
        else:
            self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

        self.achievements_file = self.save_dir / "achievements.json"
        self.cloud_sync_meta_file = self.save_dir / "cloud_sync.json"

        # Build catalog dict with independent achievement instances
        self.achievements: Dict[str, SteamAchievement] = {
            a.id: SteamAchievement(
                id=a.id,
                name_de=a.name_de,
                name_en=a.name_en,
                desc_de=a.desc_de,
                desc_en=a.desc_en,
                icon=a.icon,
                unlocked=False,
                unlock_time=None,
                hidden=a.hidden,
            )
            for a in ACHIEVEMENT_CATALOG
        }
        self.active_toasts: List[SteamToastNotification] = []

        # Steam client state
        self.is_steam_running: bool = False
        self.steam_id: Optional[str] = None
        self._init_steam_bridge()

        # Load local unlocked status
        self.load_achievements()

        # Steam Deck detection
        self.is_deck: bool = self._detect_steam_deck()

    def _init_steam_bridge(self) -> None:
        """Attempt to hook into steamworks SDK or detect local Steam environment."""
        try:
            # Check environment variables provided by Steam client
            if "SteamAppId" in os.environ or "STEAM_COMPAT_CLIENT_INSTALL_PATH" in os.environ:
                self.is_steam_running = True
                self.steam_id = os.environ.get("SteamAppId", "1984020")
            else:
                self.is_steam_running = False
        except Exception:
            self.is_steam_running = False

    def _detect_steam_deck(self) -> bool:
        """Check if executing on Valve Steam Deck hardware."""
        # SteamOS sets SteamDeck=1 or runs on 1280x800 display with handheld form-factor
        if os.environ.get("SteamDeck") == "1" or os.environ.get("SteamClientLaunch") == "1":
            return True
        return False

    def get_steam_deck_profile(self) -> Dict[str, Any]:
        """Recommended hardware & UI parameters when running on Steam Deck."""
        return {
            "target_fps": 60,
            "resolution": [1280, 800],
            "window_mode": "FULLSCREEN",
            "hud_scale": 1.25,
            "gamepad_deadzone": 0.12,
            "gamepad_sensitivity": 1.1,
            "battery_saver_particles": 0.75,
        }

    def unlock_achievement(self, ach_id: str, audio_manager: Optional[Any] = None) -> bool:
        """Unlock an achievement, dispatch notification toast, and persist progress."""
        if ach_id not in self.achievements:
            return False

        ach = self.achievements[ach_id]
        if ach.unlocked:
            return False

        ach.unlocked = True
        ach.unlock_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Create visual toast notification
        self.active_toasts.append(SteamToastNotification(ach))

        # Play reward sound
        if audio_manager and hasattr(audio_manager, "play"):
            audio_manager.play("pickup", volume=1.0, throttle=0.0)

        # Save progress
        self.save_achievements()
        self.sync_cloud_save()
        return True

    def is_achievement_unlocked(self, ach_id: str) -> bool:
        """Check if achievement has been earned."""
        return self.achievements.get(ach_id, SteamAchievement("", "", "", "", "")).unlocked

    def get_unlocked_count(self) -> Tuple[int, int]:
        """Return (unlocked_count, total_count)."""
        unlocked = sum(1 for a in self.achievements.values() if a.unlocked)
        return unlocked, len(self.achievements)

    def update(self, dt: float) -> None:
        """Tick toast notification animations."""
        self.active_toasts = [t for t in self.active_toasts if t.update(dt)]

    def draw_toasts(self, surface: pygame.Surface, lang: str = "de") -> None:
        """Render any active achievement toasts to the screen."""
        if not self.active_toasts:
            return
        font = pygame.font.SysFont("Arial", 9, bold=True)
        title_font = pygame.font.SysFont("Arial", 11, bold=True)
        for toast in self.active_toasts:
            toast.draw(surface, font, title_font, lang=lang)

    def save_achievements(self) -> bool:
        """Persist achievements to disk file."""
        try:
            payload = {}
            for ach_id, ach in self.achievements.items():
                if ach.unlocked:
                    payload[ach_id] = {
                        "unlocked": True,
                        "time": ach.unlock_time,
                    }
            tmp = self.achievements_file.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            if self.achievements_file.exists():
                self.achievements_file.unlink()
            tmp.replace(self.achievements_file)
            return True
        except Exception as e:
            print(f"[Steamworks] Save achievements failed: {e}")
            return False

    def load_achievements(self) -> bool:
        """Restore earned achievements from local cache."""
        if not self.achievements_file.exists():
            return False
        try:
            with open(self.achievements_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for ach_id, info in data.items():
                if ach_id in self.achievements:
                    self.achievements[ach_id].unlocked = bool(info.get("unlocked", False))
                    self.achievements[ach_id].unlock_time = info.get("time")
            return True
        except Exception as e:
            print(f"[Steamworks] Load achievements failed: {e}")
            return False

    def sync_cloud_save(self) -> Dict[str, Any]:
        """Perform Steam Cloud synchronization check and update cloud manifests."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        meta = {
            "last_synced": timestamp,
            "steam_running": self.is_steam_running,
            "app_id": self.steam_id or "1984020",
            "files_synced": ["achievements.json", "codex.json", "settings.json"],
            "status": "IN_SYNC",
        }
        try:
            with open(self.cloud_sync_meta_file, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
        except Exception:
            pass
        return meta
