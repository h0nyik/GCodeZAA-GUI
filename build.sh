#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# GCodeZAA — macOS .app build script
# Použití: ./build.sh [--clean] [--open]
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

PYTHON="/opt/homebrew/bin/python3.12"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_TMP="/tmp/gcodezaa_build"
DIST_DIR="$SCRIPT_DIR/dist"
APP_NAME="GCodeZAA.app"
APP="$DIST_DIR/$APP_NAME"

# ── Barvy ───────────────────────────────────────────────────────────────────
CYAN="\033[0;36m"; GREEN="\033[0;32m"; RED="\033[0;31m"; YELLOW="\033[1;33m"; BOLD="\033[1m"; RESET="\033[0m"
info()    { echo -e "${CYAN}▶  $*${RESET}"; }
success() { echo -e "${GREEN}✓  $*${RESET}"; }
warn()    { echo -e "${YELLOW}⚠  $*${RESET}"; }
error()   { echo -e "${RED}✗  $*${RESET}"; exit 1; }

echo ""
echo -e "${CYAN}${BOLD}╔══════════════════════════════════════╗${RESET}"
echo -e "${CYAN}${BOLD}║      GCodeZAA — Build .app  v0.1    ║${RESET}"
echo -e "${CYAN}${BOLD}╚══════════════════════════════════════╝${RESET}"
echo ""

# ── Parametry ───────────────────────────────────────────────────────────────
DO_CLEAN=0; DO_OPEN=0
for arg in "$@"; do
    case $arg in --clean) DO_CLEAN=1 ;; --open) DO_OPEN=1 ;; esac
done

# ── Kontrola Pythonu a závislostí ────────────────────────────────────────────
info "Kontroluji prostředí ($("$PYTHON" --version 2>&1))…"
"$PYTHON" -c "import open3d, customtkinter, tkinterdnd2, gcodezaa" 2>/dev/null \
    || { warn "Chybí závislosti. Instaluji…"
         "$PYTHON" -m pip install --break-system-packages \
             open3d numpy scikit-learn pyyaml addict pillow pandas tqdm \
             customtkinter tkinterdnd2
       }
success "Závislosti OK."

# ── Vyčistit ────────────────────────────────────────────────────────────────
if [[ $DO_CLEAN -eq 1 ]]; then
    info "Čistím předchozí build…"
    rm -rf "$BUILD_TMP" "$DIST_DIR"
fi
mkdir -p "$BUILD_TMP" "$DIST_DIR"

# ── Regenerace ikony ─────────────────────────────────────────────────────────
info "Generuji ikonu…"
"$PYTHON" - << 'PYEOF'
from PIL import Image, ImageDraw, ImageFont
import math, os, sys

def make_icon(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = size * 0.06; r = size * 0.22
    d.rounded_rectangle([pad, pad, size-pad, size-pad], radius=r, fill=(10, 14, 26, 255))
    for i in range(size):
        alpha = int(18 * math.sin(math.pi * i / size))
        d.line([(pad, pad+i), (size-pad, pad+i)], fill=(0, 212, 255, max(0, alpha)))
    cx, cy = size / 2, size * 0.42
    hex_r = size * 0.28
    pts = [(cx + hex_r*math.cos(math.radians(90+60*k)),
            cy + hex_r*math.sin(math.radians(90+60*k))) for k in range(6)]
    gp  = [(cx + (hex_r+size*0.045)*math.cos(math.radians(90+60*k)),
            cy + (hex_r+size*0.045)*math.sin(math.radians(90+60*k))) for k in range(6)]
    d.polygon(gp, fill=(0, 212, 255, 30))
    d.polygon(pts, fill=(0, 212, 255, 38))
    lw = max(2, int(size * 0.028))
    for k in range(6): d.line([pts[k], pts[(k+1)%6]], fill=(0,212,255,255), width=lw)
    try:    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", int(size*0.30))
    except: font = ImageFont.load_default()
    bb = d.textbbox((0,0), "Z", font=font)
    tx = cx-(bb[2]-bb[0])/2-bb[0]; ty = cy-(bb[3]-bb[1])/2-bb[1]-size*0.01
    d.text((tx+lw, ty+lw), "Z", font=font, fill=(0,0,0,120))
    d.text((tx, ty),       "Z", font=font, fill=(255,255,255,240))
    try:    sf = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", max(8,int(size*0.14)))
    except: sf = ImageFont.load_default()
    sb = d.textbbox((0,0), "AA", font=sf)
    d.text((cx-(sb[2]-sb[0])/2, cy+size*0.14), "AA", font=sf, fill=(0,212,255,200))
    return img

root = os.environ.get("GCODEZAA_ROOT", os.getcwd())
out  = os.path.join(root, "assets", "AppIcon.iconset")
os.makedirs(out, exist_ok=True)
for s in [16,32,64,128,256,512,1024]:
    make_icon(s).save(f"{out}/icon_{s}x{s}.png")
    if s <= 512: make_icon(s*2).save(f"{out}/icon_{s}x{s}@2x.png")
print("Iconset OK")
PYEOF

GCODEZAA_ROOT="$SCRIPT_DIR" iconutil -c icns \
    "$SCRIPT_DIR/assets/AppIcon.iconset" \
    -o "$SCRIPT_DIR/assets/AppIcon.icns"
success "Ikona vygenerována → assets/AppIcon.icns"

# ── PyInstaller ──────────────────────────────────────────────────────────────
info "Spouštím PyInstaller (build v /tmp)…"
# Buildujeme do /tmp — lokální FS, bez xattr problémů s externími disky
cd "$BUILD_TMP"
"$PYTHON" -m PyInstaller \
    --noconfirm \
    --log-level WARN \
    --distpath "$BUILD_TMP/dist" \
    --workpath "$BUILD_TMP/work" \
    "$SCRIPT_DIR/GCodeZAA.spec"

# ── Build DMG (bezpečné pro kopii na externí disky) ──────────────────────────
SRC="$BUILD_TMP/dist/$APP_NAME"
[[ -d "$SRC" ]] || error "Build selhal — $SRC nenalezeno."

info "Vytvářím DMG installer…"
DMG_TMP="$BUILD_TMP/GCodeZAA.dmg"
DMG_OUT="$DIST_DIR/GCodeZAA.dmg"

hdiutil create \
    -volname "GCodeZAA" \
    -srcfolder "$SRC" \
    -ov \
    -format UDZO \
    "$DMG_TMP" 2>&1 | grep -v "^$" || true

[[ -f "$DMG_TMP" ]] || error "DMG vytvoření selhalo."

# DMG je jeden soubor — kopie na externí disk funguje bez permission problémů
rm -f "$DMG_OUT"
cp "$DMG_TMP" "$DMG_OUT"

SIZE=$(du -sh "$DMG_OUT" | cut -f1)
success "Hotovo!  →  $DMG_OUT  ($SIZE)"
echo ""
echo -e "  ${CYAN}Instalace:${RESET}"
echo -e "  open \"$DMG_OUT\""
echo -e "  → přetáhni GCodeZAA.app do /Applications"
echo ""
echo -e "  ${CYAN}Nebo spustit přímo z /tmp (bez instalace):${RESET}"
echo -e "  open \"$SRC\""
echo ""

# ── Automaticky otevřít ──────────────────────────────────────────────────────
if [[ $DO_OPEN -eq 1 ]]; then
    info "Spouštím aplikaci…"
    open "$APP"
fi
