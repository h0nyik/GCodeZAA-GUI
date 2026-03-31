# GCodeZAA — Projektová dokumentace

> Poslední aktualizace: 2026-03-30

---

## Co je GCodeZAA

Post-processing Python skript, který přidává **Z Anti-Aliasing** (ZAA) do G-code souborů z 3D slicerů.
Technika se nazývá „Surface Layer Contouring" — tryska se při tisku horních vrstev pohybuje v ose Z
tak, aby kopírovala skutečný 3D tvar povrchu STL modelu. Výsledek: hladší povrch bez viditelných
schodků mezi vrstvami, téměř bez extra čas tisku.

**Autor originálu:** Thea Schöbl ([@Theaninova](https://github.com/Theaninova/GCodeZAA))
**Licence:** GPL-3.0
**GUI:** roztisk / Claude Code — 2026-03-30

---

## Omezení originálu

| Podmínka | Detail |
|----------|--------|
| Slicery | OrcaSlicer, BambuStudio, PrusaSlicer |
| Firmware | Klipper (OrcaSlicer mode), nebo Bambu mode |
| Soubory | Pouze STL |
| Arc moves | G2/G3 zatím nepodporováno (TODO v kódu) |

---

## Jak skript funguje (interně)

1. **Detekce sliceru** — z prvních 10 řádků `.gcode` (`OrcaSlicer` / `BambuStudio` / `PrusaSlicer`)
2. **Parsování config bloku** — embedded konfigurace v `.gcode` (výška vrstvy, šířka linky…)
3. **Načtení STL modelů** — `open3d` vytvoří `RaycastingScene` pro každý objekt
4. **Iterace G-code** — pro každý pohybový příkaz (G0/G1) na vrstvách `Top surface`, `Outer wall`, `Inner wall`, `Ironing`:
   - Rozdělí segment na úseky po 0.1 mm
   - Provede raycasting nahoru i dolů od aktuální Z pozice
   - Vypočítá odchylku `d` od povrchu modelu
   - Přepíše Z souřadnici každého bodu
   - Přepočítá E (extruze) úměrně nové výšce segmentu
5. **Výstup** — přepíše G-code soubor (nebo uloží jako nový)

---

## CLI použití (bez GUI)

```bash
# Základní použití (OrcaSlicer + Klipper)
python -m gcodezaa input.gcode \
  -m ./stl_modely \        # složka se STL soubory
  -o output.gcode          # volitelné — bez -o přepíše vstup

# Bambu Studio / jednoobjektový mód
python -m gcodezaa input.gcode \
  -m ./stl_modely \
  -o output.gcode \
  -p "125.5,110.2" \       # X,Y pozice objektu na podložce
  -n "model.stl"           # název STL souboru
```

### Argumenty

| Arg | Popis |
|-----|-------|
| `input_gcode` | Cesta ke vstupnímu `.gcode` souboru |
| `-m / --models` | Složka obsahující STL soubory objektů |
| `-o / --output` | Výstupní cesta (bez = přepíše vstup) |
| `-p / --position` | `X,Y` pozice objektu (jen Bambu/single-object) |
| `-n / --name` | Název STL souboru (jen Bambu/single-object) |

---

## Workflow pro OrcaSlicer + Klipper

1. V OrcaSlicer: **pravý klik na objekt → Export as individual STL** pro každý objekt
2. Ulož STL soubory do jedné složky — názvy musí přesně odpovídat názvům v G-code
3. Slicuj normálně → exportuj `.gcode`
4. Spusť skript (CLI nebo GUI) s cestou ke složce STL a ke `.gcode`
5. Nahraj upravený G-code do tiskárny

> **Důležité:** Názvy STL v `EXCLUDE_OBJECT_DEFINE NAME=nazev.stl_...` jsou oříznuty na `nazev.stl`
> a hledány v zadané složce. Přesná shoda názvů je povinná.

---

## Struktura projektu

```
GCodeZAA/
├── gui.py                    ← GUI aplikace (CustomTkinter, Python 3.12)
├── GCodeZAA.spec             ← PyInstaller konfigurace pro .app build
├── build.sh                  ← Build skript pro macOS .app
├── requirements-gui.txt      ← GUI závislosti (pip)
├── PROJEKT.md                ← Tato dokumentace
│
├── gcodezaa/                 ← Originální Python modul
│   ├── __main__.py           ← CLI entry point (argparse)
│   ├── process.py            ← Hlavní logika zpracování G-code
│   ├── context.py            ← ProcessorContext — stav zpracování
│   ├── extrusion.py          ← Třída Extrusion + raycasting logika
│   └── slicer_syntax.py      ← Detekce sliceru + syntax konstanty
│
├── assets/
│   ├── AppIcon.icns          ← Ikona aplikace pro macOS .app
│   └── AppIcon.iconset/      ← PNG zdroje ikony (16px–1024px)
│
└── dist/
    └── GCodeZAA.app          ← Sestavená macOS aplikace (≈304 MB)
```

---

## Python závislosti (kompletní)

### Skript (originál)
```
python >= 3.11
open3d >= 0.18.0       ← max Python 3.12 ! (PyPI nemá 3.13+)
numpy >= 2.2.1
scikit-learn >= 1.6.0
pyyaml >= 6.0.2
addict >= 2.4.0
pillow >= 11.0.0
pandas >= 2.2.3
tqdm >= 4.67.1
```

### GUI
```
customtkinter >= 5.2.2
tkinterdnd2 >= 0.3.0   ← volitelné, drag & drop (graceful fallback)
```

---

## Prostředí a instalace

### Kritické: open3d podporuje max Python 3.12

```bash
# Python 3.12 přes Homebrew (nutné — open3d nepodporuje 3.13/3.14)
brew install python@3.12
brew install python-tk@3.12    # tkinter pro Python 3.12

# Instalace všech závislostí
/opt/homebrew/bin/python3.12 -m pip install --break-system-packages \
  open3d numpy scikit-learn pyyaml addict pillow pandas tqdm \
  customtkinter tkinterdnd2

# PyInstaller pro build .app
/opt/homebrew/bin/python3.12 -m pip install --break-system-packages pyinstaller
```

### Spuštění GUI (bez buildu)
```bash
/opt/homebrew/bin/python3.12 gui.py
```

---

## Sestavení macOS .app

```bash
cd "/Volumes/roztisk/Platform.io/non planární 3D Gkod/GCodeZAA"

./build.sh           # normální build
./build.sh --clean   # vyčistit vše + rebuild od nuly
./build.sh --open    # build + rovnou spustit aplikaci
```

### Proč build probíhá v /tmp a výstup je DMG
Dva problémy externích disků (exFAT/APFS external):
1. **codesign** selhává kvůli resource forkům → PyInstaller musí buildovat na lokálním FS (`/tmp`)
2. **cp -r .app** selhává na `.dylib` souborech kvůli xattr/permission omezením externího disku

**Řešení:** Build v `/tmp/gcodezaa_build/`, výstup zabalený jako **DMG** (`hdiutil create -format UDZO`).
DMG je jeden komprimovaný soubor — kopie na externí disk funguje bez jakýchkoliv problémů.

### Gatekeeper (první spuštění)
Aplikace není podepsána Apple Developer certifikátem.
**Řešení:** Pravý klik na `.app` → **Otevřít** → **Otevřít**

---

## GUI — architektura

### Technologie
- **Python 3.12** + **CustomTkinter 5.2.2**
- Async zpracování přes `threading` + `queue.Queue` (UI nefreezenuje)
- Drag & drop: `tkinterdnd2` (volitelné, graceful fallback)

### Layout — 3 sloupce
```
┌─ VSTUP (30%) ────┐  ┌─ NASTAVENÍ (30%) ─┐  ┌─ LOG (40%) ──────┐
│ Drop zone        │  │ Výstup (radio)    │  │ Live log výstup  │
│ Složka STL       │  │ Rozšířené (Bambu) │  │ Progress bar     │
│ Info o souboru   │  │ ▶ ZPRACOVAT       │  │ Status           │
└──────────────────┘  └───────────────────┘  └──────────────────┘
```

### Design tokeny (2026 Dark Mode 2.0)

| Token | Hodnota | Použití |
|-------|---------|---------|
| `BG` | `#0a0e1a` | Pozadí okna (tmavá modrá, ne šedá) |
| `CARD` | `#111827` | Karty / panely |
| `BORDER` | `#1c2b45` | Ohraničení karet |
| `ACCENT` | `#00d4ff` | Elektrická tyrkysová — primární akcent |
| `SUCCESS` | `#22c55e` | Úspěch |
| `ERROR` | `#ef4444` | Chyba |
| `WARN` | `#f59e0b` | Varování |

### Vizuální trendy 2026 použité v GUI
- **Dark Mode 2.0** — tmavě modrá základna, ne neutrální šedá
- **Liquid Glass cards** — karty s border a průhledným efektem
- **Elektrická tyrkysová** jako dominantní akcent (evokuje preciznost, techniku)
- **SF Pro Display/Text/Mono** — nativní macOS font stack
- **Physics-based motion** — animovaný progress bar

---

## Roadmap (originál + GUI)

### Originální skript (TODO z kódu)
- [ ] G2/G3 arc moves podpora
- [ ] Ironing vylepšení
- [ ] Flow transitions
- [ ] Relative positioning support v `contour_z`
- [ ] OrcaSlicer nativní integrace (PR probíhá)

### GUI Phase 2 (budoucí)
- [ ] Drag & drop s animací
- [ ] Historie zpracovaných souborů
- [ ] G-code vizualizace (náhled vrstev)
- [ ] Nastavení: resolution, které vrstvy zpracovat
- [ ] Auto-detekce složky STL modelů ze `.gcode`
- [ ] Notifikace po dokončení (macOS UserNotifications)
- [ ] Electron/Tauri rewrite pro plnou 2026 vizuální sadu

---

## Soubory generované při buildu (ignorovat v gitu)

```
build/          ← PyInstaller work directory
dist/           ← Hotová .app (velká, negitovat)
assets/AppIcon.iconset/  ← Generováno automaticky build.sh
/tmp/gcodezaa_build/     ← Dočasný build adresář
```

---

## Verze

| Verze | Datum | Co se změnilo |
|-------|-------|---------------|
| 0.1.0 | 2026-03-30 | Inicální GUI, macOS .app build, ikona |
