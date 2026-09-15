"""Py-Noita: Bio-Horror Mikrokosmos Pixel Physics Roguelite - Main Game Engine."""

from typing import Any
import math
import os
import random
import sys
from typing import List, Optional
import pygame

from py_noita.audio.audio_manager import AudioManager
from py_noita.audio.music_engine import THEME_BOSS, THEME_INCUBATION
from py_noita.config import (
    COLOR_ACID_GLOW,
    COLOR_BG_DARK,
    COLOR_BIOGAS_GLOW,
    COLOR_MUTAGEN_GLOW,
    COLOR_NERVE_GLOW,
    COLOR_PLAYER_GLOW,
    RES_FULL_HD,
    RES_ULTRAWIDE,
    RES_WINDOWED_1080,
    RES_WINDOWED_UW,
    TARGET_FPS,
    WORLD_HEIGHT,
    WORLD_WIDTH,
)
from py_noita.entities.ai import update_enemy_ai
from py_noita.entities.enemy import Enemy, create_enemy
from py_noita.entities.player import Player
from py_noita.input.input_handler import InputHandler
from py_noita.perks.perk_definitions import ALL_PERKS
from py_noita.perks.perk_manager import PerkManager
from py_noita.physics.physics_world import PhysicsWorld
from py_noita.rendering.camera import Camera
from py_noita.rendering.lighting import LightSource, LightingEngine
from py_noita.rendering.particles import ParticleSystem
from py_noita.rendering.renderer import Renderer
from py_noita.simulation.decals import spawn_corpse_skeleton
from py_noita.simulation.explosion import ExplosionDebris, create_explosion
from py_noita.simulation.grid import SimulationGrid
from py_noita.simulation.materials import (
    MAT_ACID,
    MAT_AIR,
    MAT_BLOOD,
    MAT_MUTAGEN,
    MAT_TISSUE,
)
from py_noita.ui.cannula_editor import CannulaEditor
from py_noita.ui.codex import ALL_STRAINS, BioCodex
from py_noita.ui.game_over import GameOverScreen
from py_noita.ui.hover_info import get_hover_target
from py_noita.ui.hud import HUD
from py_noita.weapons.cannula import OrganCannula
from py_noita.weapons.deck_evaluator import MAX_ACTIVE_PROJECTILES, evaluate_cannula_fire
from py_noita.weapons.gene import GENE_DICT
from py_noita.weapons.projectile import Projectile
from py_noita.world.biome import ALL_BIOMES, Biome
from py_noita.world.endings import (
    ENDING_COSMIC_METAMORPHOSIS,
    ENDING_HOST_DEATH,
    ENDING_NONE,
    ENDING_SYMBIOSIS,
    ENDINGS,
    AscentReturnGateway,
    SurfaceAscentPortal,
)
from py_noita.world.generator import LootCyst, WorldPortal, generate_world_level
from py_noita.world.incubation_node import IncubationNode
from py_noita.world.secrets import DnaTablet, GeneOrb
from py_noita.world.streamer import WorldStreamer
from py_noita.system.save_manager import SaveManager
from py_noita.system.settings_manager import SettingsManager
from py_noita.system.steamworks import SteamworksIntegration
from py_noita.ui.settings_menu import SettingsMenu



# Game States
STATE_MENU = "MENU"
STATE_PLAYING = "PLAYING"
STATE_INCUBATION = "INCUBATION"
STATE_TUNING = "TUNING"
STATE_GAME_OVER = "GAME_OVER"
STATE_SETTINGS = "SETTINGS"


class Game:
    """Master game loop, state controller, and integration coordinator."""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Py-Noita // Mikrokosmos Bio-Horror")

        # Display Setup
        self.is_fullscreen = False
        self.is_ultrawide = False
        self.screen_res = RES_WINDOWED_1080
        self.screen = pygame.display.set_mode(self.screen_res, pygame.RESIZABLE)
        self.clock = pygame.time.Clock()

        # Settings & User Preferences
        self.settings_manager = SettingsManager()
        self.settings_menu = SettingsMenu(self.settings_manager)
        self.steam = SteamworksIntegration()
        if self.steam.is_deck:
            deck_profile = self.steam.get_steam_deck_profile()
            self.settings_manager.hud_scale = deck_profile["hud_scale"]
            self.settings_manager.gamepad_deadzone = deck_profile["gamepad_deadzone"]

        # Audio & Input
        self.audio = AudioManager()
        self.audio.apply_settings(self.settings_manager)
        self.input = InputHandler(settings=self.settings_manager)

        # Rendering & Camera
        self.renderer = Renderer(self.screen_res)
        self.renderer.post_processor.photosensitivity_mode = self.settings_manager.photosensitivity_mode
        self.camera = Camera(self.renderer.view_w, self.renderer.view_h)
        self.camera.shake_scale = self.settings_manager.screen_shake
        self.lighting = LightingEngine(self.renderer.view_w, self.renderer.view_h)
        self.particles = ParticleSystem()
        self.particles.density = self.settings_manager.particle_density

        # UI
        self.hud = HUD(scale=self.settings_manager.hud_scale)
        self.editor = CannulaEditor()
        self.game_over_screen = GameOverScreen()
        self.codex = BioCodex()
        self.font = pygame.font.SysFont("Arial", 12)
        self.title_font = pygame.font.SysFont("Arial", 22, bold=True)

        # Simulation World & 2D Rigid-Body Physics
        self.grid = SimulationGrid(WORLD_WIDTH, WORLD_HEIGHT)
        self.physics_world = PhysicsWorld(self.grid)
        self.grid.physics_world = self.physics_world

        # Gameplay Entities & State
        self.state = STATE_MENU
        self.current_biome_index: int = 0
        self.player: Optional[Player] = None
        self.perk_manager = PerkManager()
        self.enemies: List[Enemy] = []
        self.projectiles: List[Projectile] = []
        self.explosion_debris: List[ExplosionDebris] = []
        self.loot_cysts: List[LootCyst] = []
        self.gene_orbs: List[GeneOrb] = []
        self.dna_tablets: List[DnaTablet] = []
        self.secret_boss: Optional[Enemy] = None
        self.exit_portal: Optional[WorldPortal] = None
        self.incubation_node: Optional[IncubationNode] = None
        self.last_input: Optional[Any] = None

        # Endings & Endgame Quest State
        self.ending_id: int = ENDING_NONE
        self.has_primordial_genome: bool = False
        self.ascent_portal: Optional[SurfaceAscentPortal] = None
        self.ascent_return_gateway: Optional[AscentReturnGateway] = None
        self.core_boss_defeated: bool = False

        # Statistics
        self.kills_this_run: int = 0
        self.earned_mutagen: int = 0
        self.is_victory: bool = False

        # Strain selection & World Seed in menu
        self.menu_strain_index: int = 0
        self.world_seed: int = random.randint(100000, 999999)
        self.entering_seed: bool = False
        self.seed_input_str: str = ""
        self.streamer: Optional[WorldStreamer] = None
        self.footstep_timer: float = 0.0
        self.save_manager = SaveManager()
        self.quicksave_notice_timer: float = 0.0
        self.previous_state: str = STATE_MENU
        self.discovered_tablets: set = set()

    def apply_graphics_settings(self) -> None:
        """Apply window mode, resolution, screen shake, and particle density from settings."""
        w, h = self.settings_manager.resolution[0], self.settings_manager.resolution[1]
        mode = self.settings_manager.window_mode
        self.screen_res = (w, h)
        if mode == "FULLSCREEN":
            self.screen = pygame.display.set_mode(self.screen_res, pygame.FULLSCREEN)
            self.is_fullscreen = True
        elif mode == "BORDERLESS":
            self.screen = pygame.display.set_mode(self.screen_res, pygame.NOFRAME)
            self.is_fullscreen = False
        else:
            self.screen = pygame.display.set_mode(self.screen_res, pygame.RESIZABLE)
            self.is_fullscreen = False

        self.renderer.set_resolution(self.screen_res)
        self.renderer.post_processor.photosensitivity_mode = self.settings_manager.photosensitivity_mode
        self.camera.set_viewport_size(self.renderer.view_w, self.renderer.view_h)
        self.camera.shake_scale = self.settings_manager.screen_shake
        self.particles.density = self.settings_manager.particle_density
        self.hud.set_scale(self.settings_manager.hud_scale)
        self.lighting.resize(self.renderer.view_w, self.renderer.view_h)


    @property
    def current_biome(self) -> Biome:
        return ALL_BIOMES[min(self.current_biome_index, len(ALL_BIOMES) - 1)]

    def toggle_display_resolution(self) -> None:
        """Toggle between Full HD 16:9 and Ultrawide 21:9."""
        self.is_ultrawide = not self.is_ultrawide
        if self.is_fullscreen:
            self.screen_res = RES_ULTRAWIDE if self.is_ultrawide else RES_FULL_HD
            self.screen = pygame.display.set_mode(self.screen_res, pygame.FULLSCREEN)
        else:
            self.screen_res = RES_WINDOWED_UW if self.is_ultrawide else RES_WINDOWED_1080
            self.screen = pygame.display.set_mode(self.screen_res, pygame.RESIZABLE)

        self.renderer.set_resolution(self.screen_res)
        self.camera.set_viewport_size(self.renderer.view_w, self.renderer.view_h)
        self.lighting.resize(self.renderer.view_w, self.renderer.view_h)

    def toggle_fullscreen_mode(self) -> None:
        """Toggle windowed vs fullscreen display."""
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self.screen_res = RES_ULTRAWIDE if self.is_ultrawide else RES_FULL_HD
            self.screen = pygame.display.set_mode(self.screen_res, pygame.FULLSCREEN)
        else:
            self.screen_res = RES_WINDOWED_UW if self.is_ultrawide else RES_WINDOWED_1080
            self.screen = pygame.display.set_mode(self.screen_res, pygame.RESIZABLE)

        self.renderer.set_resolution(self.screen_res)
        self.camera.set_viewport_size(self.renderer.view_w, self.renderer.view_h)
        self.lighting.resize(self.renderer.view_w, self.renderer.view_h)

    def start_new_run(self) -> None:
        """Initialize a fresh run from the selected Symbiote strain."""
        self.current_biome_index = 0
        self.kills_this_run = 0
        self.earned_mutagen = 0
        self.is_victory = False
        self.ending_id = ENDING_NONE
        self.has_primordial_genome = False
        self.core_boss_defeated = False
        self.ascent_return_gateway = None
        self.perk_manager = PerkManager()
        self.projectiles.clear()
        self.explosion_debris.clear()

        # Initialize streaming world manager
        if self.streamer:
            self.streamer.shutdown()
        self.streamer = WorldStreamer(seed=self.world_seed)

        # Load Biome 1
        self.load_biome_level(0)

        # Setup Player starting loadout from selected strain
        selected_strain = ALL_STRAINS[self.menu_strain_index]
        self.player.cannulas.clear()

        # Starter Cannula 1
        starter_c = OrganCannula(
            name="Organ-Kanüle I",
            capacity=4,
            cast_delay=0.12,
            recharge_time=0.45,
            biomass_max=120.0,
            biomass_recharge=40.0,
            spread=2.0,
            shuffle=False,
        )
        for gid in selected_strain.starter_gene_ids:
            if gid in GENE_DICT:
                starter_c.add_gene(GENE_DICT[gid])
        self.player.cannulas.append(starter_c)

        # Starter Cannula 2 (Bomb / Utility)
        starter_c2 = OrganCannula(
            name="Tumor-Schleuder",
            capacity=2,
            cast_delay=0.5,
            recharge_time=0.9,
            biomass_max=80.0,
            biomass_recharge=25.0,
            spread=4.0,
            shuffle=False,
        )
        starter_c2.add_gene(GENE_DICT["BONE_BOMB"])
        self.player.cannulas.append(starter_c2)

        # Set starting liquid gland
        self.player.glands[0].material_id = selected_strain.starter_gland_mat
        self.player.glands[0].current_amount = 80

        # Apply starting strain perk if any
        if selected_strain.bonus_perk_id:
            bonus_perk = next((p for p in ALL_PERKS if p.id == selected_strain.bonus_perk_id), None)
            if bonus_perk:
                self.perk_manager.add_perk(bonus_perk, self.player)

        self.state = STATE_PLAYING

    def load_biome_level(self, biome_index: int) -> None:
        """Generate and enter a subterranean biome level."""
        self.current_biome_index = biome_index
        biome = self.current_biome

        # Generate cavern grid with deterministic seed & scaled boss hp by DNA orbs
        level_seed = self.world_seed + biome_index * 1337
        orbs_cnt = self.player.orbs_collected if self.player else 0
        spawn_pos, portal, enemy_spawns, loot, orbs, tablets, boss = generate_world_level(
            self.grid, biome, physics_world=self.physics_world, seed=level_seed, orbs_collected=orbs_cnt
        )
        self.exit_portal = portal
        self.loot_cysts = loot
        self.gene_orbs = orbs
        self.dna_tablets = tablets
        self.secret_boss = boss
        self.ascent_portal = getattr(self.grid, "ascent_portal", None)
        if biome.biome_id != "PRIMORDIAL_CORE":
            self.ascent_return_gateway = None


        # Create/relocate player
        if self.player is None:
            self.player = Player(spawn_pos[0], spawn_pos[1])
        else:
            self.player.x = spawn_pos[0]
            self.player.y = spawn_pos[1]
            self.player.vx = 0.0
            self.player.vy = 0.0

        # Spawn enemies
        self.enemies.clear()
        for ex, ey, etype in enemy_spawns:
            self.enemies.append(create_enemy(etype, ex, ey))
        if self.secret_boss is not None:
            self.enemies.append(self.secret_boss)

        self.projectiles.clear()
        self.particles.particles.clear()
        self.physics_world = PhysicsWorld(self.grid)
        self.grid.physics_world = self.physics_world
        self.audio.play("squelch", volume=0.7)

        # Update adaptive music theme for this biome
        if hasattr(self.audio, "music") and self.audio.music:
            if self.secret_boss is not None and getattr(self.secret_boss, "alive", True):
                self.audio.music.set_theme(THEME_BOSS)
            else:
                self.audio.music.set_theme(biome_index)
            self.audio.music.set_combat_intensity(0.0)

        if biome.biome_id == "BILE_LAGOON":
            self.steam.unlock_achievement("ACH_BILE_LAGOON", self.audio)

    def enter_incubation_node(self) -> None:
        """Generate and enter the Incubation Node sanctuary."""
        self.state = STATE_INCUBATION
        self.steam.unlock_achievement("ACH_INCUBATION_SANCTUARY", self.audio)
        # Incubation node room
        room_w, room_h = 420, 160
        start_x = (WORLD_WIDTH - room_w) // 2
        start_y = 120

        has_side_path = False
        side_biome_id = None
        side_biome_name = ""
        if self.current_biome.biome_id == "GASTRIC":
            has_side_path = True
            side_biome_id = "BILE_LAGOON"
            side_biome_name = "Gallen-Lagune"

        self.incubation_node = IncubationNode(
            start_x,
            start_y,
            room_w,
            room_h,
            has_side_path=has_side_path,
            side_biome_id=side_biome_id,
            side_biome_name=side_biome_name,
        )
        self.incubation_node.generate_structure(self.grid)

        # Teleport player into sanctuary
        self.player.x = float(start_x + 30)
        self.player.y = float(start_y + room_h - 40)
        self.player.vx = 0.0
        self.player.vy = 0.0

        self.enemies.clear()
        self.projectiles.clear()
        self.audio.play("pickup", volume=0.9)

        if hasattr(self.audio, "music") and self.audio.music:
            self.audio.music.set_theme(THEME_INCUBATION)
            self.audio.music.set_combat_intensity(0.0)

    def trigger_ending(self, ending_id: int) -> None:
        """Trigger one of the three alternative narrative endings."""
        self.save_manager.delete_quicksave()
        self.ending_id = ending_id
        self.is_victory = True
        bonus = ENDINGS.get(ending_id, ENDINGS[ENDING_HOST_DEATH]).bonus_mutagen
        self.earned_mutagen = self.codex.record_run(
            self.current_biome_index + 1,
            self.kills_this_run,
            self.player.biomass_currency if self.player else 0,
        ) + bonus
        self.codex.mutagen_essence += bonus
        self.codex.save()

        # Steam Endings & Meta Achievements
        if ending_id == ENDING_HOST_DEATH:
            self.steam.unlock_achievement("ACH_ENDING_1", self.audio)
        elif ending_id == ENDING_SYMBIOSIS:
            self.steam.unlock_achievement("ACH_ENDING_2", self.audio)
        elif ending_id == ENDING_COSMIC_METAMORPHOSIS:
            self.steam.unlock_achievement("ACH_ENDING_3", self.audio)

        if self.codex.mutagen_essence >= 1000:
            self.steam.unlock_achievement("ACH_MUTAGEN_1000", self.audio)
        if all(s.strain_id in self.codex.unlocked_strains for s in ALL_STRAINS):
            self.steam.unlock_achievement("ACH_UNLOCK_ALL_STRAINS", self.audio)

        self.state = STATE_GAME_OVER

    def run(self) -> None:

        """Master execution loop."""
        running = True
        while running:
            dt = self.clock.tick(TARGET_FPS) / 1000.0
            events = pygame.event.get()
            self.steam.update(dt)

            for event in events:
                if event.type == pygame.QUIT:
                    if self.state in (STATE_PLAYING, STATE_INCUBATION, STATE_TUNING) and self.player and self.player.alive:
                        self.save_manager.save_run(self)
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.screen_res = (event.w, event.h)
                    self.renderer.set_resolution(self.screen_res)
                    self.camera.set_viewport_size(self.renderer.view_w, self.renderer.view_h)
                    self.lighting.resize(self.renderer.view_w, self.renderer.view_h)

            # Route update and render by game state
            if self.state == STATE_MENU:
                self._update_menu(events)
                self._draw_menu()
            elif self.state == STATE_PLAYING:
                self._update_playing(dt, events)
                self._draw_playing()
            elif self.state == STATE_INCUBATION:
                self._update_incubation(dt, events)
                self._draw_playing()
            elif self.state == STATE_TUNING:
                self._update_tuning(events)
                self._draw_tuning()
            elif self.state == STATE_GAME_OVER:
                self._update_game_over(events)
                self._draw_game_over()
            elif self.state == STATE_SETTINGS:
                self._update_settings(events)
                self._draw_settings()

            self.steam.draw_toasts(self.screen, lang=self.settings_manager.language)
            pygame.display.flip()

        pygame.quit()

    def _update_settings(self, events) -> None:
        """Handle settings configuration input and live audio/graphics tweaking."""
        dt = self.clock.get_time() / 1000.0
        self.settings_menu.update(dt)
        for event in events:
            if self.settings_menu.handle_event(event, self.audio):
                self.apply_graphics_settings()
                self.state = self.previous_state

    def _draw_settings(self) -> None:
        """Render settings menu overlay on top of menu or paused world."""
        if self.previous_state in (STATE_PLAYING, STATE_INCUBATION, STATE_TUNING) and self.player:
            self._draw_playing()
        else:
            self._draw_menu()
        self.settings_menu.draw(self.screen)

    def _update_menu(self, events) -> None:
        """Handle main menu / strain selection input and world seed entry."""
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.entering_seed:
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if self.seed_input_str.strip():
                            try:
                                self.world_seed = int(self.seed_input_str.strip())
                            except ValueError:
                                self.world_seed = abs(hash(self.seed_input_str.strip())) % (10**7)
                        self.entering_seed = False
                    elif event.key == pygame.K_ESCAPE:
                        self.entering_seed = False
                    elif event.key == pygame.K_BACKSPACE:
                        self.seed_input_str = self.seed_input_str[:-1]
                    else:
                        if event.unicode and len(self.seed_input_str) < 9:
                            if event.unicode.isdigit():
                                self.seed_input_str += event.unicode
                    continue

                if event.key in (pygame.K_d, pygame.K_RIGHT):
                    self.menu_strain_index = (self.menu_strain_index + 1) % len(ALL_STRAINS)
                elif event.key in (pygame.K_a, pygame.K_LEFT):
                    self.menu_strain_index = (self.menu_strain_index - 1) % len(ALL_STRAINS)
                elif event.key == pygame.K_r:
                    self.world_seed = random.randint(100000, 999999)
                elif event.key == pygame.K_s:
                    self.entering_seed = True
                    self.seed_input_str = str(self.world_seed)
                elif event.key == pygame.K_u:
                    # Try to unlock selected strain
                    strain = ALL_STRAINS[self.menu_strain_index]
                    if self.codex.unlock_strain(strain.strain_id):
                        self.audio.play("pickup", volume=1.0)
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    strain = ALL_STRAINS[self.menu_strain_index]
                    if strain.strain_id in self.codex.unlocked_strains:
                        self.start_new_run()
                elif event.key == pygame.K_c:
                    if self.save_manager.has_quicksave():
                        if self.save_manager.load_run(self):
                            self.audio.play("pickup", volume=1.0)
                elif event.key == pygame.K_o:
                    self.previous_state = STATE_MENU
                    self.state = STATE_SETTINGS
                elif event.key == pygame.K_F1:
                    self.toggle_display_resolution()
                elif event.key == pygame.K_F11:
                    self.toggle_fullscreen_mode()

    def _draw_menu(self) -> None:
        """Render main menu with strain unlocks and title."""
        self.screen.fill((12, 8, 16))
        view_w, view_h = self.screen_res

        # Title
        title = self.title_font.render("PY-NOITA // MIKROKOSMOS", True, (255, 60, 80))
        sub = self.font.render("Jeder Pixel physikalisch simuliert  •  Bio-Horror Deckbuilder", True, (190, 180, 170))
        self.screen.blit(title, (view_w // 2 - title.get_width() // 2, 70))
        self.screen.blit(sub, (view_w // 2 - sub.get_width() // 2, 105))

        # Mutagen Currency
        mut_surf = self.font.render(f"Mutagen-Essenz (Labor-Konto): {self.codex.mutagen_essence} M", True, (220, 50, 240))
        self.screen.blit(mut_surf, (view_w // 2 - mut_surf.get_width() // 2, 138))

        # Quicksave Resume Prompt (if active run exists)
        qs_info = self.save_manager.get_quicksave_info()
        card_y = 175
        if qs_info:
            qs_text = f"[C] RUN FORTSETZEN: {qs_info['biome_name']} (HP: {int(qs_info['player_hp'])}/{int(qs_info['player_max_hp'])}) • Seed: {qs_info['world_seed']}"
            qs_surf = self.font.render(qs_text, True, (80, 255, 210))
            box_w = qs_surf.get_width() + 24
            box_h = 24
            box_x = view_w // 2 - box_w // 2
            box_y = 160
            card_y = 194
            pygame.draw.rect(self.screen, (15, 35, 40), (box_x, box_y, box_w, box_h), border_radius=4)
            pygame.draw.rect(self.screen, (60, 210, 180), (box_x, box_y, box_w, box_h), 1, border_radius=4)
            self.screen.blit(qs_surf, (box_x + 12, box_y + 4))

        # Strain Card
        strain = ALL_STRAINS[self.menu_strain_index]
        is_unlocked = strain.strain_id in self.codex.unlocked_strains

        card_w, card_h = 360, 130
        card_x = view_w // 2 - card_w // 2
        pygame.draw.rect(self.screen, (25, 18, 30), (card_x, card_y, card_w, card_h), border_radius=6)
        pygame.draw.rect(self.screen, (160, 80, 110) if is_unlocked else (70, 60, 75), (card_x, card_y, card_w, card_h), 2, border_radius=6)

        strain_title = self.font.render(f"< {strain.name} >" if is_unlocked else f"< {strain.name} (GESPERRT) >", True, (255, 230, 120) if is_unlocked else (150, 140, 145))
        self.screen.blit(strain_title, (card_x + card_w // 2 - strain_title.get_width() // 2, card_y + 12))

        desc = self.font.render(strain.description, True, (210, 200, 190))
        self.screen.blit(desc, (card_x + card_w // 2 - desc.get_width() // 2, card_y + 40))

        if is_unlocked:
            start_prompt = self.font.render("[LEERTASTE] Abstieg in den Wirt beginnen", True, (80, 255, 120))
            self.screen.blit(start_prompt, (card_x + card_w // 2 - start_prompt.get_width() // 2, card_y + 85))
        else:
            unlock_prompt = self.font.render(f"[U] Freischalten ({strain.unlock_cost} Mutagen)", True, (240, 120, 220))
            self.screen.blit(unlock_prompt, (card_x + card_w // 2 - unlock_prompt.get_width() // 2, card_y + 85))

        # World Seed Bar
        seed_y = card_y + card_h + 14
        if self.entering_seed:
            seed_surf = self.font.render(f"WELT-SEED EINGEBEN: [ {self.seed_input_str}_ ]  (ENTER = Bestätigen, ESC = Abbrechen)", True, (255, 230, 80))
        else:
            seed_surf = self.font.render(f"WELT-SEED: [ {self.world_seed} ]  •  [R] Zufälliger Seed  •  [S] Seed eingeben", True, (175, 220, 240))
        self.screen.blit(seed_surf, (view_w // 2 - seed_surf.get_width() // 2, seed_y))

        # Controls info at bottom
        ctrl_info = self.font.render("[O] Einstellungen / Optionen  |  [F1] Auflösung  |  [F11] Vollbild  |  WASD + Maus", True, (150, 140, 160))
        self.screen.blit(ctrl_info, (view_w // 2 - ctrl_info.get_width() // 2, view_h - 40))

    def _update_playing(self, dt: float, events) -> None:
        """Handle active gameplay frame."""
        if self.quicksave_notice_timer > 0.0:
            self.quicksave_notice_timer = max(0.0, self.quicksave_notice_timer - dt)

        # 1. Process Input
        cam_x, cam_y = self.camera.get_offset()
        input_state = self.input.process_events(
            events,
            self.renderer.dest_rect,
            cam_x,
            cam_y,
            self.renderer.view_w,
            self.renderer.view_h,
            self.player.center_x,
            self.player.center_y,
        )
        self.last_input = input_state

        if input_state.toggle_fullscreen:
            self.toggle_fullscreen_mode()
        if input_state.toggle_resolution:
            self.toggle_display_resolution()
        if input_state.toggle_inventory:
            self.state = STATE_TUNING
            return
        if input_state.pause or any(e.type == pygame.KEYDOWN and e.key == pygame.K_o for e in events):
            self.previous_state = STATE_PLAYING
            self.state = STATE_SETTINGS
            return

        # F5 Quicksave shortcut
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F5:
                if self.save_manager.save_run(self):
                    self.quicksave_notice_timer = 2.5
                    self.audio.play("pickup", volume=0.8)

        # Weapon / Gland selection
        if input_state.select_cannula is not None and input_state.select_cannula < len(self.player.cannulas):
            self.player.active_cannula_index = input_state.select_cannula
        if input_state.select_gland is not None:
            self.player.active_gland_index = input_state.select_gland

        # Player Movement
        self.player.aim_angle = input_state.aim_angle
        self.player.apply_input(input_state.move_x, input_state.hover)

        # 2. Player Weapon Firing
        if self.player.cannulas and 0 <= self.player.active_cannula_index < len(self.player.cannulas):
            active_c = self.player.cannulas[self.player.active_cannula_index]
            active_c.update(dt)

            if input_state.fire_primary:
                new_projs = evaluate_cannula_fire(
                    active_c,
                    self.player.center_x,
                    self.player.center_y,
                    self.player.aim_angle,
                    owner="PLAYER",
                    shooter=self.player,
                )

                if new_projs:
                    available = max(0, MAX_ACTIVE_PROJECTILES - len(self.projectiles))
                    if available > 0:
                        for p in new_projs[:available]:
                            p.damage = self.perk_manager.modify_damage_dealt(p.damage)
                        self.projectiles.extend(new_projs[:available])
                    self.camera.add_shake(0.12)
                    launch_snd = "shot"
                    if active_c.genes:
                        gid = active_c.genes[0].id
                        if "CARTILAGE" in gid:
                            launch_snd = "proj_cartilage_shot"
                        elif "CYTOKINE" in gid or "LASER" in gid:
                            launch_snd = "proj_cytokine_laser"
                        elif "PLASMA" in gid or "TENDRIL" in gid:
                            launch_snd = "proj_plasma_tendril"
                        elif "SPORE" in gid:
                            launch_snd = "proj_spore_mortar"
                        elif "SLIME" in gid:
                            launch_snd = "proj_slime_glob"
                        elif "ACID" in gid:
                            launch_snd = "proj_acid_dart"
                        elif "NERVE" in gid or "SYNAPSE" in gid:
                            launch_snd = "proj_nerve_jolt"
                        elif "BLOOD" in gid:
                            launch_snd = "proj_blood_surge"
                        elif "BONE" in gid:
                            launch_snd = "proj_bone_boomerang"
                    self.audio.play(launch_snd, volume=0.8)

        # Player Liquid Gland Spraying / Sucking
        if input_state.fire_secondary:
            mat = self.player.spray_liquid(self.grid)
            if mat:
                self.audio.play("acid" if mat == MAT_ACID else "squelch", volume=0.4)

        if input_state.suck_liquid:
            if self.player.suck_liquid(self.grid):
                self.audio.play("squelch", volume=0.3)

        # 3. Update Physics & Fallingsand Simulation
        self.grid.update(cam_x, cam_y, self.renderer.view_w, self.renderer.view_h)
        self.player.update_physics(self.grid, gravity_multiplier=self.current_biome.gravity_multiplier)
        self.perk_manager.update(dt, self.player, self.grid)

        # Procedural footstep sounds matched to ground material (flesh, bone, slime)
        if self.player.on_ground and abs(self.player.vx) > 12.0:
            self.footstep_timer += dt
            if self.footstep_timer >= 0.26:
                self.footstep_timer = 0.0
                foot_y = int(self.player.y + self.player.height + 1)
                ground_mat = self.grid.get_pixel(int(self.player.center_x), foot_y)
                self.audio.play_footstep(
                    ground_mat,
                    self.player.center_x,
                    float(foot_y),
                    self.player.center_x,
                    self.player.center_y,
                    volume=0.55,
                )

        # 4. Update Projectiles
        targets = self.enemies
        spawned_child_projs: List[Projectile] = []
        for proj in self.projectiles:
            children = proj.update(self.grid, targets)
            if children:
                spawned_child_projs.extend(children)
        available_children = max(0, MAX_ACTIVE_PROJECTILES - len(self.projectiles))
        if available_children > 0:
            self.projectiles.extend(spawned_child_projs[:available_children])
        self.projectiles = [p for p in self.projectiles if p.alive]
        if len(self.projectiles) > MAX_ACTIVE_PROJECTILES:
            self.projectiles = self.projectiles[:MAX_ACTIVE_PROJECTILES]

        # Process physical projectile impacts on terrain
        if hasattr(self.grid, "pending_impacts"):
            for imp_mat, ix, iy in self.grid.pending_impacts:
                self.audio.play_material_impact(
                    imp_mat,
                    float(ix),
                    float(iy),
                    self.player.center_x,
                    self.player.center_y,
                    volume=0.65,
                )
            self.grid.pending_impacts.clear()

        # 5. Update Explosion Debris
        self.explosion_debris = [d for d in self.explosion_debris if d.update(self.grid)]

        # 5b. Update 2D Rigid-Body Physics
        self.physics_world.update(
            dt,
            cam_x,
            cam_y,
            self.renderer.view_w,
            self.renderer.view_h,
            enemies=self.enemies,
            player=self.player,
        )

        # 5c. Update World Chunk Streaming & Memory Management
        if self.streamer:
            self.streamer.update_streaming(
                self.player.center_x, self.player.center_y, self.grid
            )

        # 6. Update Enemies & AI
        spawned_hostile_projs: List[Projectile] = []
        spawned_minions: List[Enemy] = []
        for enemy in self.enemies:
            enemy.update_physics(self.grid)
            e_projs, e_minions = update_enemy_ai(enemy, self.player, self.grid, dt)
            spawned_hostile_projs.extend(e_projs)
            spawned_minions.extend(e_minions)

            # Check enemy death
            if not enemy.alive:
                self.kills_this_run += 1
                self.player.biomass_currency += enemy.biomass_value
                self.particles.spawn_blood_burst(enemy.center_x, enemy.center_y, count=18)
                self.audio.play_spatial("bone_crack", enemy.center_x, enemy.center_y, self.player.center_x, self.player.center_y, volume=0.8)
                # Visceral anatomical skeleton & permanent wall decals
                spawn_corpse_skeleton(self.grid, enemy.center_x, enemy.center_y, enemy.enemy_type, enemy.blood_mat)

                # Steam Achievements
                self.steam.unlock_achievement("ACH_FIRST_KILL", self.audio)
                if self.kills_this_run >= 50:
                    self.steam.unlock_achievement("ACH_KILLS_50", self.audio)
                if self.kills_this_run >= 200:
                    self.steam.unlock_achievement("ACH_KILLS_200", self.audio)
                if enemy.enemy_type == "FLESH_WORM":
                    self.steam.unlock_achievement("ACH_KILL_WORM", self.audio)
                elif enemy.enemy_type == "PARASITE_SPIDER":
                    self.steam.unlock_achievement("ACH_KILL_SPIDER", self.audio)
                elif enemy.enemy_type == "SYNAPTIC_SENTRY":
                    self.steam.unlock_achievement("ACH_KILL_SENTRY", self.audio)

        self.enemies.extend(spawned_minions)
        self.enemies = [e for e in self.enemies if e.alive]

        # Hostile projectiles targeting player
        for hp in spawned_hostile_projs:
            hp.update(self.grid, [self.player])
            self.projectiles.append(hp)

        # 7. Check Loot Cysts
        for cyst in self.loot_cysts:
            if cyst.alive:
                dist = math.hypot(cyst.x - self.player.center_x, cyst.y - self.player.center_y)
                if dist < 24.0:
                    cyst.alive = False
                    self.player.biomass_currency += 35
                    self.audio.play_spatial("pickup", cyst.x, cyst.y, self.player.center_x, self.player.center_y, volume=0.9)
                    self.particles.spawn_spore_puff(cyst.x, cyst.y, count=12)
                    if self.player.biomass_currency >= 200:
                        self.steam.unlock_achievement("ACH_ABSORB_GOLD", self.audio)

        # 7b. Check Gene Orbs & Secret Boss Attacks
        for orb in self.gene_orbs:
            new_gene = orb.update(self.player)
            if new_gene:
                self.audio.play_spatial("pickup", orb.x, orb.y, self.player.center_x, self.player.center_y, volume=1.0)
                self.particles.spawn_spore_puff(orb.x, orb.y, count=30)
                self.steam.unlock_achievement("ACH_SECRET_ORB", self.audio)
                if self.player.orbs_collected >= 5:
                    self.steam.unlock_achievement("ACH_ALL_ORBS", self.audio)

        # 7b2. Check Ancient DNA Tablets
        for tab in self.dna_tablets:
            dist = math.hypot(tab.x - self.player.center_x, tab.y - self.player.center_y)
            if dist < 36.0:
                self.discovered_tablets.add(tab.tablet_id)
                self.steam.unlock_achievement("ACH_DNA_TABLET", self.audio)
                if len(self.discovered_tablets) >= 5:
                    self.steam.unlock_achievement("ACH_ALL_TABLETS", self.audio)

        # 7b3. Check Organ Cannulas & Glands
        if len(self.player.cannulas) >= 4:
            self.steam.unlock_achievement("ACH_FOUR_CANNULAS", self.audio)
        distinct_mats = set()
        for gland in self.player.glands:
            if gland.current_amount >= gland.max_amount and gland.material_id:
                self.steam.unlock_achievement("ACH_FIRST_GLAND", self.audio)
            if gland.current_amount > 10 and gland.material_id:
                distinct_mats.add(gland.material_id)
        if len(distinct_mats) >= 4:
            self.steam.unlock_achievement("ACH_FULL_GLANDS", self.audio)

        if self.secret_boss and self.secret_boss.alive and hasattr(self.secret_boss, "update_boss"):
            b_projs, b_minions = self.secret_boss.update_boss(self.player, self.grid, dt)
            for bp in b_projs:
                bp.update(self.grid, [self.player])
                self.projectiles.append(bp)
            self.enemies.extend(b_minions)

        # Check secret boss defeat (Acquire Primordial Genome upon Brain Core destruction)
        if self.secret_boss and not self.secret_boss.alive:
            if getattr(self.secret_boss, "enemy_type", "") == "BRAIN_CORE_BOSS":
                if not self.core_boss_defeated:
                    self.core_boss_defeated = True
                    self.has_primordial_genome = True
                    self.particles.spawn_spore_puff(self.secret_boss.center_x, self.secret_boss.center_y, count=60)
                    self.ascent_return_gateway = AscentReturnGateway(self.secret_boss.center_x + 70, self.secret_boss.center_y)
                    self.steam.unlock_achievement("ACH_CORE_BOSS", self.audio)

        # 7c. Check Surface Cosmic Ascent Portal (Ending 3: Cosmic Metamorphosis)
        if self.ascent_portal:
            self.ascent_portal.update()
            if self.ascent_portal.is_player_inside(self.player.center_x, self.player.center_y):
                if self.has_primordial_genome:
                    self.trigger_ending(ENDING_COSMIC_METAMORPHOSIS)
                    return

        # 7d. Check Ascent Return Gateway (Back to Biome 1)
        if self.ascent_return_gateway:
            self.ascent_return_gateway.update()
            if self.ascent_return_gateway.is_player_inside(self.player.center_x, self.player.center_y):
                self.load_biome_level(0)
                self.audio.play("pickup", volume=1.0)
                return

        # 8. Check Exit Portal
        if self.exit_portal and self.exit_portal.is_player_inside(self.player.center_x, self.player.center_y):
            if self.current_biome.biome_id == "PRIMORDIAL_CORE":
                if self.core_boss_defeated or (self.secret_boss and not self.secret_boss.alive):
                    if self.player.orbs_collected >= 11:
                        self.trigger_ending(ENDING_SYMBIOSIS)
                        return
                    else:
                        self.trigger_ending(ENDING_HOST_DEATH)
                        return
            else:
                self.enter_incubation_node()


        # 9. Camera & Particles
        self.camera.update(
            self.player.center_x,
            self.player.center_y,
            input_state.aim_world_x,
            input_state.aim_world_y,
        )
        self.particles.update(self.grid)
        # Dynamic combat intensity for adaptive soundtrack cross-fade
        if hasattr(self.audio, "music") and self.audio.music:
            in_combat = False
            if self.secret_boss and getattr(self.secret_boss, "alive", True):
                in_combat = True
            else:
                p_cx, p_cy = self.player.center_x, self.player.center_y
                for e in self.enemies:
                    if getattr(e, "alive", True):
                        dx = e.center_x - p_cx
                        dy = e.center_y - p_cy
                        if dx * dx + dy * dy < 240.0 * 240.0:
                            in_combat = True
                            break
            self.audio.music.set_combat_intensity(1.0 if in_combat else 0.0)

        self.audio.update(dt, player=self.player, grid=self.grid)

        # 9b. Update Shader Post-Processing Effects (heat shimmer, acid refraction, shockwaves, low HP pulse)
        if hasattr(self.grid, "pending_explosions"):
            for ex_x, ex_y, ex_power in self.grid.pending_explosions:
                self.renderer.post_processor.trigger_detonation(ex_x, ex_y, cam_x, cam_y, ex_power)
                self.audio.play_spatial(
                    "explosion",
                    ex_x,
                    ex_y,
                    self.player.center_x,
                    self.player.center_y,
                    volume=min(1.0, 0.7 + ex_power * 0.05),
                )
            self.grid.pending_explosions.clear()

        heat_val = 0.8 if self.player.on_fire else (0.3 if self.player.fire_timer > 0 else 0.0)
        acid_val = min(1.0, self.player.acid_burn_timer / 45.0) if self.player.acid_burn_timer > 0 else 0.0
        hp_ratio = self.player.hp / max(1.0, self.player.max_hp)
        self.renderer.post_processor.update(dt, heat_val=heat_val, acid_val=acid_val, player_hp_ratio=hp_ratio)

        # 10. Check Player Death (Permadeath: Erase Quicksave)
        if not self.player.alive:
            self.save_manager.delete_quicksave()
            self.earned_mutagen = self.codex.record_run(
                self.current_biome_index + 1,
                self.kills_this_run,
                self.player.biomass_currency,
            )
            self.state = STATE_GAME_OVER

    def _update_incubation(self, dt: float, events) -> None:
        """Handle safe incubation node / holy mountain frame."""
        cam_x, cam_y = self.camera.get_offset()
        input_state = self.input.process_events(
            events,
            self.renderer.dest_rect,
            cam_x,
            cam_y,
            self.renderer.view_w,
            self.renderer.view_h,
            self.player.center_x,
            self.player.center_y,
        )
        self.last_input = input_state

        if input_state.toggle_fullscreen:
            self.toggle_fullscreen_mode()
        if input_state.toggle_resolution:
            self.toggle_display_resolution()
        if input_state.toggle_inventory:
            self.state = STATE_TUNING
            return
        if input_state.pause or any(e.type == pygame.KEYDOWN and e.key == pygame.K_o for e in events):
            self.previous_state = STATE_INCUBATION
            self.state = STATE_SETTINGS
            return

        self.player.aim_angle = input_state.aim_angle
        self.player.apply_input(input_state.move_x, input_state.hover)
        self.player.update_physics(self.grid)

        # Incubation interactions (Healing pool, Perks, Shop)
        new_perk = self.incubation_node.update(self.player)
        if new_perk:
            self.perk_manager.add_perk(new_perk, self.player)
            self.audio.play("pickup", volume=1.0)
            self.particles.spawn_spore_puff(self.player.center_x, self.player.center_y, count=25)
            if len(self.perk_manager.active_perks) >= 5:
                self.steam.unlock_achievement("ACH_PERK_SYNERGY", self.audio)

        # Check side portal transition (e.g. into Bile Lagoon)
        if self.incubation_node and self.incubation_node.is_player_in_side_portal(self.player):
            for i, b in enumerate(ALL_BIOMES):
                if b.biome_id == self.incubation_node.side_biome_id:
                    self.load_biome_level(i)
                    self.state = STATE_PLAYING
                    return

        # Exit shaft drop (advance to next biome level)
        ex, ey = self.incubation_node.exit_shaft_pos
        if abs(self.player.center_x - ex) < 20 and self.player.y > ey:
            # If leaving side biome (BILE_LAGOON), rejoin main path at INFECTED_LUNG
            if self.current_biome.is_side_path:
                for i, b in enumerate(ALL_BIOMES):
                    if b.biome_id == "INFECTED_LUNG":
                        self.load_biome_level(i)
                        self.state = STATE_PLAYING
                        return

            next_idx = self.current_biome_index + 1
            # If next_idx is side path (BILE_LAGOON), skip over to INFECTED_LUNG on main path
            if next_idx < len(ALL_BIOMES) and ALL_BIOMES[next_idx].is_side_path:
                next_idx += 1

            if next_idx >= len(ALL_BIOMES):
                # Victory!
                self.is_victory = True
                self.earned_mutagen = self.codex.record_run(
                    next_idx,
                    self.kills_this_run,
                    self.player.biomass_currency,
                )
                self.state = STATE_GAME_OVER
            else:
                self.load_biome_level(next_idx)
                self.state = STATE_PLAYING

        self.camera.update(self.player.center_x, self.player.center_y)
        self.physics_world.update(dt, cam_x, cam_y, self.renderer.view_w, self.renderer.view_h)
        self.particles.update(self.grid)
        self.audio.update(dt, player=self.player, grid=self.grid)

    def _update_tuning(self, events) -> None:
        """Handle organ-tuning deckbuilder GUI."""
        mouse_px, mouse_py = pygame.mouse.get_pos()
        dest = self.renderer.dest_rect

        # Map to internal simulation coordinates
        if dest.width > 0 and dest.height > 0:
            sim_mx = int(((mouse_px - dest.left) / dest.width) * self.renderer.view_w)
            sim_my = int(((mouse_py - dest.top) / dest.height) * self.renderer.view_h)
        else:
            sim_mx, sim_my = 0, 0

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_TAB, pygame.K_ESCAPE, pygame.K_e):
                    self.state = STATE_PLAYING if self.incubation_node is None else STATE_INCUBATION
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.editor.handle_click(sim_mx, sim_my, self.player)

    def _update_game_over(self, events) -> None:
        """Handle Game Over screen inputs."""
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.start_new_run()
                elif event.key == pygame.K_ESCAPE:
                    self.state = STATE_MENU

    def _draw_playing(self) -> None:
        """Render playing world, entities, lighting, and HUD."""
        cam_x, cam_y = self.camera.get_offset()

        # 1. Render Fallingsand Pixel World Grid with Decals
        self.renderer.render_grid(self.grid.grid, self.grid.color_var, cam_x, cam_y, stain_map=self.grid.stain_map)

        # 2. Draw Entities
        surf = self.renderer.sim_surface

        # Portal
        if self.exit_portal:
            psx = int(self.exit_portal.x - cam_x)
            psy = int(self.exit_portal.y - cam_y)
            pulse = math.sin(pygame.time.get_ticks() * 0.005) * 3.0
            pygame.draw.circle(surf, (180, 50, 240), (psx, psy), int(self.exit_portal.radius + pulse), 2)
            pygame.draw.circle(surf, (255, 120, 255), (psx, psy), int(self.exit_portal.radius * 0.5))

        # Surface Cosmic Ascent Portal (Biome 1)
        if self.ascent_portal:
            self.ascent_portal.draw(surf, cam_x, cam_y, self.font)

        # Core Ascent Return Gateway (Biome 8 post-boss)
        if self.ascent_return_gateway:
            self.ascent_return_gateway.draw(surf, cam_x, cam_y, self.font)


        # Incubation node room elements
        if self.state == STATE_INCUBATION and self.incubation_node:
            self.incubation_node.draw(surf, cam_x, cam_y, self.font)

        # Ancient DNA Lore Tablets
        for tab in self.dna_tablets:
            tab.draw(surf, cam_x, cam_y, self.font)

        # Gene Orbs
        for orb in self.gene_orbs:
            orb.draw(surf, cam_x, cam_y, self.font)

        # Loot Cysts
        for cyst in self.loot_cysts:
            if cyst.alive:
                csx = int(cyst.x - cam_x)
                csy = int(cyst.y - cam_y)
                pygame.draw.circle(surf, (220, 180, 50), (csx, csy), int(cyst.radius))

        # Enemies
        for enemy in self.enemies:
            enemy.draw(surf, cam_x, cam_y)

        # Projectiles
        for proj in self.projectiles:
            proj.draw(surf, cam_x, cam_y)

        # Rigid Bodies / Props
        self.physics_world.draw(surf, cam_x, cam_y)

        # Player
        if self.player:
            self.player.draw(surf, cam_x, cam_y)

        # Particles
        self.particles.draw(surf, cam_x, cam_y)

        # 3. Dynamic Bioluminescence Lighting Pass
        lights: List[LightSource] = []
        if self.player:
            lights.append(LightSource(self.player.center_x, self.player.center_y, radius=48.0, color=COLOR_PLAYER_GLOW, intensity=0.9))

        for proj in self.projectiles:
            lights.append(LightSource(proj.x, proj.y, radius=proj.radius * 6.0, color=proj.color, intensity=0.7))

        if self.physics_world:
            lights.extend(self.physics_world.get_lights())

        self.lighting.render(surf, cam_x, cam_y, lights, self.grid.grid)

        # 4. In-Game HUD & Hover Inspection
        hover_target = None
        mouse_pos = None
        if self.last_input is not None and self.last_input.mouse_in_bounds:
            mouse_pos = (self.last_input.sim_mouse_x, self.last_input.sim_mouse_y)
            hover_target = get_hover_target(
                self.grid,
                self.enemies,
                self.last_input.aim_world_x,
                self.last_input.aim_world_y,
                self.loot_cysts,
                rigid_bodies=self.physics_world.bodies,
                gene_orbs=self.gene_orbs,
                dna_tablets=self.dna_tablets,
            )

        self.hud.draw(
            surf,
            self.player,
            self.current_biome.name,
            self.current_biome.depth_level,
            hover_target=hover_target,
            mouse_pos=mouse_pos,
            active_boss=self.secret_boss if (self.secret_boss and self.secret_boss.alive) else None,
        )

        if self.quicksave_notice_timer > 0.0:
            qs_msg = self.font.render("[F5 QUICKSAVE GESPEICHERT]", True, (80, 255, 190))
            surf.blit(qs_msg, (self.renderer.view_w // 2 - qs_msg.get_width() // 2, 8))

        # 5. Present to window / Fullscreen display
        self.renderer.present(self.screen)

    def _draw_tuning(self) -> None:
        """Render organ-tuning deckbuilder on top of paused world."""
        # Draw world first
        self._draw_playing()

        # Overlay tuning editor
        dest = self.renderer.dest_rect
        mouse_px, mouse_py = pygame.mouse.get_pos()
        sim_mx = int(((mouse_px - dest.left) / max(1, dest.width)) * self.renderer.view_w)
        sim_my = int(((mouse_py - dest.top) / max(1, dest.height)) * self.renderer.view_h)

        self.editor.draw(self.renderer.sim_surface, self.player, (sim_mx, sim_my))
        self.renderer.present(self.screen)

    def _draw_game_over(self) -> None:
        """Render Game Over screen."""
        self._draw_playing()
        self.game_over_screen.draw(
            self.renderer.sim_surface,
            self.is_victory,
            self.current_biome_index + 1,
            self.kills_this_run,
            self.player.biomass_currency if self.player else 0,
            self.earned_mutagen,
            self.codex.mutagen_essence,
            ending_id=self.ending_id,
            orbs_collected=self.player.orbs_collected if self.player else 0,
        )
        self.renderer.present(self.screen)



def main() -> None:
    """Entry point for Py-Noita."""
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
