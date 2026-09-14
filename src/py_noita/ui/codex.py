"""Bio-Codex and Meta-Progression: Persistent strain unlocks and discovered catalog."""

import json
import os
from typing import Dict, List, Optional
import pygame

CODEX_FILE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "bio_codex.json")


class Strain:
    """A playable Symbiote strain with distinct starting loadout and traits."""
    def __init__(
        self,
        strain_id: str,
        name: str,
        description: str,
        unlock_cost: int,
        starter_gene_ids: List[str],
        starter_gland_mat: int,
        bonus_perk_id: Optional[str] = None,
    ):
        self.strain_id = strain_id
        self.name = name
        self.description = description
        self.unlock_cost = unlock_cost
        self.starter_gene_ids = starter_gene_ids
        self.starter_gland_mat = starter_gland_mat
        self.bonus_perk_id = bonus_perk_id


ALL_STRAINS = [
    Strain(
        strain_id="STRAIN_DEFAULT",
        name="Ur-Parasit (Standard)",
        description="Agiler Parasit mit Knochenspeer und regenerierendem Blutbeutel.",
        unlock_cost=0,
        starter_gene_ids=["BONE_SPIKE"],
        starter_gland_mat=20,  # MAT_BLOOD
    ),
    Strain(
        strain_id="STRAIN_ACID_SYNTH",
        name="Säure-Synthetisierer",
        description="Verätzt Wirtsgewebe mit Säuregalle und immuner Chitinmembran.",
        unlock_cost=80,
        starter_gene_ids=["ACID_GLOBULE"],
        starter_gland_mat=21,  # MAT_ACID
        bonus_perk_id="ACID_IMMUNITY",
    ),
    Strain(
        strain_id="STRAIN_SYNAPTIC",
        name="Synaptischer Egel",
        description="Feuert blitzschnelle Nervenimpulse mit beschleunigtem Geißelantrieb.",
        unlock_cost=150,
        starter_gene_ids=["NERVE_BOLT"],
        starter_gland_mat=23,  # MAT_LYMPH
        bonus_perk_id="FLAGELLA_TURBO",
    ),
]


class BioCodex:
    """Manages persistent achievements, discovered elements, and meta-currency."""

    def __init__(self, filepath: str = CODEX_FILE_PATH):
        self.filepath = os.path.abspath(filepath)
        self.mutagen_essence: int = 0
        self.unlocked_strains: List[str] = ["STRAIN_DEFAULT"]
        self.discovered_genes: List[str] = ["BONE_SPIKE", "ACID_GLOBULE"]
        self.discovered_enemies: List[str] = ["MACROPHAGE", "ANTIBODY"]
        self.best_depth: int = 1
        self.total_kills: int = 0
        self.selected_strain_id: str = "STRAIN_DEFAULT"

        self.load()

    def load(self) -> None:
        """Load codex from persistent JSON file."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.mutagen_essence = data.get("mutagen_essence", 0)
                    self.unlocked_strains = data.get("unlocked_strains", ["STRAIN_DEFAULT"])
                    self.discovered_genes = data.get("discovered_genes", ["BONE_SPIKE"])
                    self.discovered_enemies = data.get("discovered_enemies", ["MACROPHAGE"])
                    self.best_depth = data.get("best_depth", 1)
                    self.total_kills = data.get("total_kills", 0)
                    self.selected_strain_id = data.get("selected_strain_id", "STRAIN_DEFAULT")
            except Exception:
                pass

    def save(self) -> None:
        """Save codex to persistent JSON file."""
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            data = {
                "mutagen_essence": self.mutagen_essence,
                "unlocked_strains": self.unlocked_strains,
                "discovered_genes": self.discovered_genes,
                "discovered_enemies": self.discovered_enemies,
                "best_depth": self.best_depth,
                "total_kills": self.total_kills,
                "selected_strain_id": self.selected_strain_id,
            }
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def record_run(self, depth: int, kills: int, biomass: int) -> int:
        """Record run statistics and reward Mutagen-Essence."""
        self.best_depth = max(self.best_depth, depth)
        self.total_kills += kills
        earned_mutagen = depth * 25 + kills * 2 + (biomass // 10)
        self.mutagen_essence += earned_mutagen
        self.save()
        return earned_mutagen

    def unlock_strain(self, strain_id: str) -> bool:
        """Unlock a strain if player has enough mutagen essence."""
        strain = next((s for s in ALL_STRAINS if s.strain_id == strain_id), None)
        if strain and strain_id not in self.unlocked_strains:
            if self.mutagen_essence >= strain.unlock_cost:
                self.mutagen_essence -= strain.unlock_cost
                self.unlocked_strains.append(strain_id)
                self.save()
                return True
        return False
