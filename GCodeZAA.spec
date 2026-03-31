# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — GCodeZAA macOS .app
# Build: cd /tmp && /opt/homebrew/bin/python3.12 -m PyInstaller /path/to/GCodeZAA.spec

import os, sys, glob

SITE  = "/opt/homebrew/lib/python3.12/site-packages"
ROOT  = "/Volumes/roztisk/Platform.io/non planární 3D Gkod/GCodeZAA"

# ── Datas ───────────────────────────────────────────────────────────────────
datas = [
    (f"{SITE}/customtkinter",  "customtkinter"),
    (f"{SITE}/open3d",         "open3d"),
    (f"{SITE}/tkinterdnd2",    "tkinterdnd2"),
    (os.path.join(ROOT, "gcodezaa"), "gcodezaa"),
]

# ── Hidden imports ──────────────────────────────────────────────────────────
hiddenimports = [
    "customtkinter",
    "tkinterdnd2",
    "PIL", "PIL._tkinter_finder",
    "addict", "yaml", "tqdm",
    "sklearn", "sklearn.utils._cython_blas",
    "sklearn.neighbors._partition_nodes",
    "pandas", "pandas._libs.tslibs.np_datetime",
    "pandas._libs.tslibs.nattype",
    "scipy", "scipy.spatial",
    "scipy.spatial.transform",
    "scipy.spatial.transform._rotation_groups",
    "scipy.special._cdflib",
    "open3d",
]

# ── Binaries ────────────────────────────────────────────────────────────────
binaries = [
    (f"{SITE}/open3d/libtbb.12.dylib",  "."),
    (f"{SITE}/open3d/libomp.dylib",     "."),
    (f"{SITE}/open3d/cpu/pybind.cpython-312-darwin.so", "open3d/cpu"),
]

# ── Analysis ────────────────────────────────────────────────────────────────
a = Analysis(
    [os.path.join(ROOT, "gui.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib", "IPython", "jupyter", "notebook",
        "PyQt5", "PyQt6", "wx", "gi",
        "_pytest", "pytest",
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)  # noqa

exe = EXE(  # noqa
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GCodeZAA",
    debug=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(  # noqa
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="GCodeZAA",
)

app = BUNDLE(  # noqa
    coll,
    name="GCodeZAA.app",
    icon=os.path.join(ROOT, "assets", "AppIcon.icns"),
    bundle_identifier="cz.roztisk.gcodezaa",
    version="0.1.0",
    info_plist={
        "CFBundleName":               "GCodeZAA",
        "CFBundleDisplayName":        "GCodeZAA",
        "CFBundleVersion":            "0.1.0",
        "CFBundleShortVersionString": "0.1",
        "CFBundleIdentifier":         "cz.roztisk.gcodezaa",
        "NSHighResolutionCapable":    True,
        "NSHumanReadableCopyright":   "GPL-3.0 • Thea Schöbl / GUI by roztisk",
        "LSMinimumSystemVersion":     "12.0",
        "CFBundleDocumentTypes": [{
            "CFBundleTypeName":       "G-code File",
            "CFBundleTypeRole":       "Editor",
            "CFBundleTypeExtensions": ["gcode", "gc", "g"],
            "LSHandlerRank":          "Alternate",
        }],
    },
)
