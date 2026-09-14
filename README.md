# Py-Noita: Mikrokosmos Bio-Horror

Ein von **Noita** inspiriertes 2D-Action-Roguelite in Python, bei dem **jeder einzelne Pixel physikalisch und chemisch simuliert wird** ("Falling Sand" Zellulärer Automat).

Im Mikrokosmos-/Bio-Horror-Theme steuerst du einen lebenden Symbioten/Parasiten, der mit modifizierbaren **Organ-Kanülen** (Zauberstäben), Gen-Sequenzen (Spells) und Flüssigkeitsbeuteln durch die Organe eines riesigen infizierten Wirtsorganismus hinabsteigt.

---

## Features

- **Jeder Pixel physikalisch simuliert**:
  - **Feststoffe**: Fleischgewebe (`TISSUE`), Knochen (`BONE`), Chitin-Panzer (`CHITIN`), Nervenfasern (`NERVE`), Tentakelmasse (`TENTACLE_FLESH`).
  - **Granular/Pulver**: Sporen (`SPORES`), Parasiteneier (`EGGS`), Asche (`ASH`), Knochensplitter (`BONE_CHIP`).
  - **Flüssigkeiten**: Blut (`BLOOD`), Magensäure (`ACID`), Galle (`BILE`), Lymphe (`LYMPH`), Eiter (`PUS`), Mutagen-Schleim (`MUTAGEN`).
  - **Gase & Flammen**: Biogas/Methan (`BIOGAS`), Toxischer Dampf (`TOXIC_VAPOR`), Feuer (`FIRE`), Rauch (`SMOKE`).
- **Tiefes Reaktionsnetzwerk & Mutagen-Alchemie**:
  - Säure zersetzt organisches Fleisch und Knochen unter Biogas-Entwicklung.
  - Entzündetes Biogas führt zu massiven Kettenreaktionsexplosionen mit Kraterbildung.
  - Lymphe neutralisiert Magensäure zu harmlosem Salzwasser.
  - Mutagen-Schleim verwandelt Wirtsgewebe und Kreaturen in pulsierende Tentakelmassen.
  - Feuer verbrennt Fleisch zu Asche und Rauch.
- **Numba-beschleunigte 60+ FPS Physik**:
  - JIT-kompilierte C/LLVM-Kernels für hunderte Meter tiefe Höhlenwelten.
- **Vollständiges Noita-Waffen- & Deckbuilding-System**:
  - Organ-Kanülen mit Kapazität, Cast-Delay, Recharge-Time, Biomasse-Mana, Streuung und Shuffle.
  - Gen-Karten: Projektile, Trigger bei Aufprall / Timer, Modifikatoren (Pheromon-Peilung, nekrotischer Brand, Chitinspitzen) und Multicast (Doppel-, Dreifach-, Streu-Injektion).
- **Prozedurale Organ-Biome & Inkubations-Knoten (Heiliger Berg)**:
  - Schichtenweiser Abstieg: *Epidermis & Cutis* -> *Vaskulärer Muskel* -> *Magensäure-Kavernen* -> *Nervenkern & Ur-Zentrum*.
  - Inkubations-Sanktuarien mit Mitose-Heilpool, genetischen Mutations-Perks (inkl. High-Risk/Reward Trade-Offs) und Organ-Tuning-Tisch.
- **Wirtsabwehr & Feind-KI**:
  - Fresszellen (Makrophagen), fliegende Antikörper-Jäger (T-Zellen), gepanzerte Granulozyten-Säurewerfer, bodengrabende Fleischwürmer und Tumor-Zysten.
- **Flüssigkeits-Saugsystem (Drüsenbeutel)**:
  - Eigene Organ-Drüsen (Tasten 5–8) zum Aufsaugen von Flüssigkeiten aus der Spielwelt und gezielten Versprühen.
- **Display & Audio**:
  - Optimiert für **Full HD (1920x1080)** und **Ultrawide (2560x1080, 21:9)** sowie skalierbares Fenster.
  - Dynamische Biolumineszenz (Säure- und Nervenglühen, Spielerlicht).
  - Standalone prozedurale Audiosynthese (Schmatzen, Zischen, Herzschlag, Detonationen) ohne externe Audio-Dateien.
- **Meta-Progression & Bio-Kodex**:
  - Persistentes Speichern im Bio-Kodex (`bio_codex.json`).
  - Sammeln von Mutagen-Essenz zur Freischaltung alternativer Symbiot-Stämme (*Säure-Synthetisierer*, *Synaptischer Egel*).

---

## Installation & Spielstart

Das Projekt nutzt den modernen Python-Paketmanager `uv`:

```bash
# Projekt clonen oder im Projektordner öffnen
cd py-noita

# Abhängigkeiten installieren (pygame-ce, numpy, numba)
uv sync

# Spiel starten
uv run py-noita
```

*Alternativ direkt:*
```bash
uv run python -m py_noita.main
```

---

## Steuerung

### Tastatur & Maus
- **A / D** oder **Pfeiltasten**: Symbiot horizontal bewegen
- **W / Leertaste**: Flagellen-Schwebeflug (Levitation mit Ausdauerleiste)
- **S**: Schneller Sinkflug
- **Mauszeiger (360°)**: Zielen
- **Linksklick**: Aktive Organ-Kanüle abfeuern
- **Rechtsklick**: Flüssigkeit aus aktivem Drüsenbeutel versprühen
- **F**: Flüssigkeit aus der Umgebung in aktiven Drüsenbeutel aufsaugen
- **1, 2, 3, 4**: Organ-Kanülen (Waffen) wählen
- **5, 6, 7, 8**: Organ-Drüsen (Flüssigkeitsbeutel) wählen
- **TAB / I**: Organ-Tuning (Gen-Karten per Klick verschieben und austauschen)
- **F1**: Auflösung umschalten (16:9 Full HD ↔ 21:9 Ultrawide)
- **F11**: Vollbildmodus umschalten
- **ESC**: Pause / Menü

### Controller / Gamepad (Twin-Stick)
- **Linker Stick**: Bewegen & Schweben
- **Rechter Stick**: 360° Zielen
- **Rechter Trigger (RT)**: Abfeuern
- **Linker Trigger (LT)**: Drüsen-Flüssigkeit versprühen
- **A-Taste**: Schwebeflug
- **X-Taste**: Flüssigkeit aufsaugen
- **Y- / B-Taste**: Organ-Tuning öffnen
- **Schultertasten (LB / RB)**: Kanülen durchschalten

---

## Tests & Benchmarks ausführen

```bash
uv run python -m unittest discover -s tests
```
