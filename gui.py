#!/usr/bin/env python3
"""
GCodeZAA GUI
Modern 3-column desktop interface for Z Anti-Aliasing G-code post-processing
Design: Dark Mode 2.0 + Liquid Glass cards — 2026 visual trends
"""

import sys
import os
import io
import queue
import threading
from pathlib import Path

# Add project root to path so gcodezaa module is found
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog

# Optional drag & drop (pip install tkinterdnd2)
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False


# ─── Design tokens ─────────────────────────────────────────────────────────────
BG       = "#0a0e1a"
CARD     = "#111827"
CARD_ALT = "#0c1423"
BORDER   = "#1c2b45"
BDR_HL   = "#2a4070"
ACCENT   = "#00d4ff"
ACC_BTN  = "#0099bb"
ACC_DIM  = "#005f75"
TEXT     = "#e2e8f0"
MUTED    = "#4a6080"
DIM      = "#2a3d55"
SUCCESS  = "#22c55e"
ERROR    = "#ef4444"
WARN     = "#f59e0b"
INPUT    = "#080c18"

SLICER_COLORS = {
    "OrcaSlicer":  "#22c55e",
    "BambuStudio": "#3b82f6",
    "PrusaSlicer": "#f59e0b",
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

_IS_MAC = sys.platform == "darwin"


def fui(size=12, weight="normal"):
    family = "SF Pro Text" if _IS_MAC else "Segoe UI"
    return (family, size, weight)


def fmono(size=11):
    family = "SF Pro Mono" if _IS_MAC else "Consolas"
    return (family, size)


def fdisplay(size=14, weight="bold"):
    family = "SF Pro Display" if _IS_MAC else "Segoe UI"
    return (family, size, weight)


# ─── G-code analyzer (fast, no open3d) ─────────────────────────────────────────
def analyze_gcode(path: str) -> dict:
    info = {"slicer": "Neznámý", "layers": 0, "objects": 0, "layer_height": "?"}
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines[:10]:
            if "OrcaSlicer"  in line: info["slicer"] = "OrcaSlicer";  break
            if "BambuStudio" in line: info["slicer"] = "BambuStudio"; break
            if "PrusaSlicer" in line: info["slicer"] = "PrusaSlicer"; break

        in_cfg = False
        for line in lines:
            if "; CONFIG_BLOCK_START"  in line: in_cfg = True;  continue
            if "; CONFIG_BLOCK_END"    in line: in_cfg = False; continue
            if in_cfg and line.startswith("; layer_height"):
                try:
                    info["layer_height"] = line.split("=")[1].strip() + " mm"
                except Exception:
                    pass
            if ";LAYER_CHANGE" in line or "; CHANGE_LAYER" in line:
                info["layers"] += 1
            if "EXCLUDE_OBJECT_DEFINE" in line:
                info["objects"] += 1
    except Exception:
        pass
    return info


# ─── Background processing worker ───────────────────────────────────────────────
def run_worker(input_path: str, models_dir, output_path, plate_model, log_q: queue.Queue):
    class QueueWriter(io.TextIOBase):
        def write(self, s):
            if s.strip():
                log_q.put(("log", s.rstrip()))
            return len(s)

        def flush(self):
            pass

    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = QueueWriter()
    try:
        from gcodezaa.process import process_gcode
        log_q.put(("log", f"Načítám {Path(input_path).name}…"))

        with open(input_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        log_q.put(("log", f"Celkem {len(lines):,} řádků G-code"))
        result = process_gcode(lines, models_dir, plate_model)

        out = output_path or input_path
        with open(out, "w", encoding="utf-8") as f:
            f.writelines(result)

        log_q.put(("done", f"Hotovo → {Path(out).name}"))
    except Exception as exc:
        log_q.put(("error", str(exc)))
    finally:
        sys.stdout, sys.stderr = old_out, old_err


# ─── Main application ────────────────────────────────────────────────────────────
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Load tkdnd into the CTk window without needing TkinterDnD.Tk as base class
        global HAS_DND
        if HAS_DND:
            try:
                TkinterDnD._require(self)
            except Exception:
                HAS_DND = False

        # ── State ──
        self.input_path  = tk.StringVar()
        self.models_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.out_mode    = tk.StringVar(value="overwrite")
        self.pos_x       = tk.StringVar()
        self.pos_y       = tk.StringVar()
        self.stl_name    = tk.StringVar()
        self._log_q      = queue.Queue()
        self._processing = False
        self._prog_dir   = 1
        self._gcode_info = {}

        # ── Window ──
        self.title("GCodeZAA")
        self.geometry("1300x800")
        self.minsize(960, 620)
        self.configure(fg_color=BG)

        self._build()
        self._poll()

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_header()

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=30)
        content.grid_columnconfigure(1, weight=30)
        content.grid_columnconfigure(2, weight=40)

        self._build_col_left(content)
        self._build_col_mid(content)
        self._build_col_right(content)

    def _build_header(self):
        h = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0, height=54)
        h.grid(row=0, column=0, sticky="ew")
        h.grid_columnconfigure(1, weight=1)
        h.grid_propagate(False)

        logo = ctk.CTkFrame(h, fg_color="transparent")
        logo.grid(row=0, column=0, padx=18, sticky="ns")
        ctk.CTkLabel(logo, text="⬡", font=fdisplay(20), text_color=ACCENT).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(logo, text="GCodeZAA", font=fdisplay(15, "bold"), text_color=TEXT).pack(side="left")
        ctk.CTkLabel(logo, text="Z Anti-Aliasing", font=fui(11), text_color=MUTED).pack(side="left", padx=(10, 0))

        self._slicer_badge = ctk.CTkLabel(
            h, text="  Čeká na soubor  ", font=fui(11),
            text_color=MUTED, fg_color=CARD_ALT, corner_radius=4,
        )
        self._slicer_badge.grid(row=0, column=1, sticky="e", padx=18)
        ctk.CTkLabel(h, text="v0.1", font=fmono(11), text_color=DIM).grid(row=0, column=2, padx=18)

    def _card(self, parent, title=None, col=0, row=0, rowspan=1,
              padx=(0, 0), pady=(0, 8), sticky="nsew"):
        """Factory: styled glass card with optional section title."""
        f = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=12,
                         border_width=1, border_color=BORDER)
        f.grid(row=row, column=col, rowspan=rowspan, sticky=sticky,
               padx=padx, pady=pady)
        if title:
            ctk.CTkLabel(f, text=title.upper(), font=fui(9, "bold"),
                         text_color=MUTED).pack(anchor="w", padx=16, pady=(13, 5))
            ctk.CTkFrame(f, fg_color=BORDER, height=1, corner_radius=0).pack(
                fill="x", padx=16, pady=(0, 10))
        return f

    # ── Left column: file input + info ────────────────────────────────────────

    def _build_col_left(self, parent):
        col = ctk.CTkFrame(parent, fg_color="transparent")
        col.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        col.grid_columnconfigure(0, weight=1)
        col.grid_rowconfigure(2, weight=1)

        # ─ Drop zone card ─
        drop = ctk.CTkFrame(col, fg_color=CARD, corner_radius=12,
                            border_width=1, border_color=BORDER)
        drop.grid(row=0, column=0, sticky="ew", pady=(0, 7))
        ctk.CTkLabel(drop, text="VSTUPNÍ SOUBOR", font=fui(9, "bold"),
                     text_color=MUTED).pack(anchor="w", padx=16, pady=(13, 5))
        ctk.CTkFrame(drop, fg_color=BORDER, height=1, corner_radius=0).pack(
            fill="x", padx=16, pady=(0, 10))

        self._dz = ctk.CTkFrame(drop, fg_color=INPUT, corner_radius=8,
                                border_width=1, border_color=BORDER)
        self._dz.pack(fill="x", padx=14, pady=(0, 10))

        ctk.CTkLabel(self._dz, text="🗂", font=(fmono(30)[0], 30)).pack(pady=(18, 3))
        self._dz_label = ctk.CTkLabel(self._dz, text="Přetáhni .gcode soubor",
                                      font=fui(13, "bold"), text_color=TEXT)
        self._dz_label.pack()
        ctk.CTkLabel(self._dz, text="nebo", font=fui(11), text_color=MUTED).pack(pady=2)
        ctk.CTkButton(
            self._dz, text="Vybrat soubor", font=fui(12),
            fg_color=ACC_DIM, hover_color=ACC_BTN, text_color=TEXT,
            corner_radius=6, height=30, command=self._pick_gcode,
        ).pack(pady=(2, 16))

        self._fname_label = ctk.CTkLabel(drop, text="", font=fmono(10),
                                         text_color=MUTED, wraplength=260)
        self._fname_label.pack(padx=14, pady=(0, 12))

        if HAS_DND:
            self._dz.drop_target_register(DND_FILES)
            self._dz.dnd_bind("<<Drop>>",      self._on_drop)
            self._dz.dnd_bind("<<DragEnter>>", lambda e: self._dz.configure(border_color=ACCENT))
            self._dz.dnd_bind("<<DragLeave>>", lambda e: self._dz.configure(border_color=BORDER))

        # ─ Models folder card ─
        mc = self._card(col, "Složka modelů (STL)", row=1, pady=(0, 7))
        mr = ctk.CTkFrame(mc, fg_color="transparent")
        mr.pack(fill="x", padx=14, pady=(0, 6))
        mr.grid_columnconfigure(0, weight=1)

        self._models_entry = ctk.CTkEntry(
            mr, textvariable=self.models_path,
            placeholder_text="/cesta/ke/stl/složce",
            font=fmono(10), fg_color=INPUT, border_color=BORDER,
            text_color=TEXT, height=32, corner_radius=6,
        )
        self._models_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(mr, text="📁", width=36, height=32, fg_color=BORDER,
                      hover_color=BDR_HL, corner_radius=6,
                      command=self._pick_models_dir).grid(row=0, column=1)

        ctk.CTkLabel(mc, text="STL modely pro raycasting (OrcaSlicer / Klipper)",
                     font=fui(10), text_color=MUTED).pack(anchor="w", padx=14, pady=(0, 12))

        # ─ Info card ─
        ic = self._card(col, "Info", row=2, sticky="new", pady=(0, 0))
        self._i_slicer  = self._irow(ic, "Slicer",        "—")
        self._i_layers  = self._irow(ic, "Vrstvy",        "—")
        self._i_objects = self._irow(ic, "Objekty",       "—")
        self._i_height  = self._irow(ic, "Výška vrstvy",  "—", last=True)

    def _irow(self, parent, label: str, val: str, last=False):
        r = ctk.CTkFrame(parent, fg_color="transparent")
        r.pack(fill="x", padx=16, pady=(0, 4))
        ctk.CTkLabel(r, text=label, font=fui(11), text_color=MUTED,
                     anchor="w", width=110).pack(side="left")
        lbl = ctk.CTkLabel(r, text=val, font=fmono(11), text_color=ACCENT, anchor="e")
        lbl.pack(side="right")
        if last:
            ctk.CTkFrame(parent, fg_color="transparent", height=10).pack()
        return lbl

    # ── Middle column: settings + run ─────────────────────────────────────────

    def _build_col_mid(self, parent):
        col = ctk.CTkFrame(parent, fg_color="transparent")
        col.grid(row=0, column=1, sticky="nsew", padx=7)
        col.grid_columnconfigure(0, weight=1)
        col.grid_rowconfigure(2, weight=1)   # spacer row

        # ─ Output card ─
        oc = self._card(col, "Výstup", row=0, pady=(0, 7))
        ctk.CTkRadioButton(
            oc, text="Přepsat vstupní soubor",
            variable=self.out_mode, value="overwrite",
            font=fui(12), text_color=TEXT, fg_color=ACCENT, hover_color=ACC_BTN,
            command=self._toggle_out,
        ).pack(anchor="w", padx=16, pady=(0, 6))
        ctk.CTkRadioButton(
            oc, text="Uložit jako nový soubor",
            variable=self.out_mode, value="saveas",
            font=fui(12), text_color=TEXT, fg_color=ACCENT, hover_color=ACC_BTN,
            command=self._toggle_out,
        ).pack(anchor="w", padx=16, pady=(0, 10))

        outr = ctk.CTkFrame(oc, fg_color="transparent")
        outr.pack(fill="x", padx=14, pady=(0, 14))
        outr.grid_columnconfigure(0, weight=1)

        self._out_entry = ctk.CTkEntry(
            outr, textvariable=self.output_path,
            placeholder_text="Výstupní cesta…",
            font=fmono(10), fg_color=INPUT, border_color=BORDER,
            text_color=TEXT, height=32, corner_radius=6, state="disabled",
        )
        self._out_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._out_btn = ctk.CTkButton(
            outr, text="💾", width=36, height=32,
            fg_color=BORDER, hover_color=BDR_HL, corner_radius=6,
            state="disabled", command=self._pick_output,
        )
        self._out_btn.grid(row=0, column=1)

        # ─ Advanced (Bambu) card ─
        adv = self._card(col, "Rozšířené — Bambu / Jednoobjektový", row=1, pady=(0, 7))
        ctk.CTkLabel(
            adv, text="Pro Bambu Studio nebo single-object mód bez Klipper",
            font=fui(10), text_color=MUTED, wraplength=280,
        ).pack(anchor="w", padx=16, pady=(0, 10))

        pf = ctk.CTkFrame(adv, fg_color="transparent")
        pf.pack(fill="x", padx=14)
        pf.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(pf, text="Pozice X", font=fui(10), text_color=MUTED).grid(
            row=0, column=0, sticky="w")
        ctk.CTkLabel(pf, text="Pozice Y", font=fui(10), text_color=MUTED).grid(
            row=0, column=1, sticky="w", padx=(6, 0))
        ctk.CTkEntry(
            pf, textvariable=self.pos_x, placeholder_text="125.5",
            font=fmono(11), fg_color=INPUT, border_color=BORDER,
            text_color=TEXT, height=32, corner_radius=6,
        ).grid(row=1, column=0, sticky="ew", padx=(0, 3))
        ctk.CTkEntry(
            pf, textvariable=self.pos_y, placeholder_text="110.2",
            font=fmono(11), fg_color=INPUT, border_color=BORDER,
            text_color=TEXT, height=32, corner_radius=6,
        ).grid(row=1, column=1, sticky="ew", padx=(3, 0))

        ctk.CTkLabel(adv, text="Název STL", font=fui(10), text_color=MUTED).pack(
            anchor="w", padx=16, pady=(10, 2))
        ctk.CTkEntry(
            adv, textvariable=self.stl_name, placeholder_text="model.stl",
            font=fmono(11), fg_color=INPUT, border_color=BORDER,
            text_color=TEXT, height=32, corner_radius=6,
        ).pack(fill="x", padx=14, pady=(0, 14))

        # ─ Spacer ─
        ctk.CTkFrame(col, fg_color="transparent").grid(row=2, column=0, sticky="nsew")

        # ─ Run button ─
        self._run_btn = ctk.CTkButton(
            col, text="▶   ZPRACOVAT GCODE",
            font=fdisplay(14, "bold"),
            fg_color=ACC_DIM, hover_color=ACC_BTN,
            text_color=TEXT, corner_radius=10, height=52,
            command=self._run,
        )
        self._run_btn.grid(row=3, column=0, sticky="ew", pady=(8, 0))

    # ── Right column: log ──────────────────────────────────────────────────────

    def _build_col_right(self, parent):
        col = ctk.CTkFrame(parent, fg_color="transparent")
        col.grid(row=0, column=2, sticky="nsew", padx=(7, 0))
        col.grid_rowconfigure(0, weight=1)
        col.grid_columnconfigure(0, weight=1)

        log = ctk.CTkFrame(col, fg_color=CARD, corner_radius=12,
                           border_width=1, border_color=BORDER)
        log.grid(row=0, column=0, sticky="nsew")
        log.grid_rowconfigure(1, weight=1)
        log.grid_columnconfigure(0, weight=1)

        # Header
        lh = ctk.CTkFrame(log, fg_color="transparent")
        lh.grid(row=0, column=0, sticky="ew", padx=16, pady=(13, 0))
        lh.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(lh, text="LOG", font=fui(9, "bold"), text_color=MUTED).grid(
            row=0, column=0, sticky="w")
        ctk.CTkButton(
            lh, text="Vymazat", font=fui(10), text_color=MUTED,
            fg_color="transparent", hover_color=BORDER,
            width=60, height=22, corner_radius=4, command=self._clear_log,
        ).grid(row=0, column=1, sticky="e")
        ctk.CTkFrame(log, fg_color=BORDER, height=1, corner_radius=0).grid(
            row=0, column=0, sticky="ews", padx=16)

        # Log textbox — uses underlying tk.Text for per-line color tags
        self._logbox = ctk.CTkTextbox(
            log, font=fmono(11), fg_color="transparent", text_color=MUTED,
            wrap="word", corner_radius=0, activate_scrollbars=True,
            scrollbar_button_color=BORDER, scrollbar_button_hover_color=BDR_HL,
        )
        self._logbox.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        # Pre-configure color tags on the underlying tk.Text widget
        tb = self._logbox._textbox
        tb.tag_configure("accent",  foreground=ACCENT)
        tb.tag_configure("success", foreground=SUCCESS)
        tb.tag_configure("error",   foreground=ERROR)
        tb.tag_configure("warn",    foreground=WARN)
        tb.tag_configure("muted",   foreground=MUTED)

        # Progress area
        pf = ctk.CTkFrame(log, fg_color=CARD_ALT, corner_radius=8)
        pf.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 12))
        pf.grid_columnconfigure(0, weight=1)

        ph = ctk.CTkFrame(pf, fg_color="transparent")
        ph.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        ph.grid_columnconfigure(0, weight=1)

        self._prog_label = ctk.CTkLabel(ph, text="Připraven", font=fui(11), text_color=MUTED)
        self._prog_label.grid(row=0, column=0, sticky="w")
        self._prog_pct = ctk.CTkLabel(ph, text="", font=fmono(11), text_color=ACCENT)
        self._prog_pct.grid(row=0, column=1, sticky="e")

        self._pbar = ctk.CTkProgressBar(
            pf, fg_color=BORDER, progress_color=ACCENT, corner_radius=4, height=5,
        )
        self._pbar.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
        self._pbar.set(0)

    # ── File actions ────────────────────────────────────────────────────────────

    def _pick_gcode(self):
        path = filedialog.askopenfilename(
            title="Vybrat G-code soubor",
            filetypes=[("G-code", "*.gcode *.gc *.g"), ("Vše", "*.*")],
        )
        if path:
            self._set_gcode(path)

    def _on_drop(self, event):
        path = event.data.strip().strip("{}")
        if path.lower().endswith((".gcode", ".gc", ".g")):
            self._set_gcode(path)
        self._dz.configure(border_color=BORDER)

    def _set_gcode(self, path: str):
        self.input_path.set(path)
        name = Path(path).name
        self._fname_label.configure(text=f"📄 {name}", text_color=TEXT)
        self._dz_label.configure(text=name, text_color=ACCENT)

        if self.out_mode.get() == "saveas" and not self.output_path.get():
            p = Path(path)
            self.output_path.set(str(p.parent / f"{p.stem}_zaa.gcode"))

        self._log(f"Načítám informace o souboru…", "muted")
        threading.Thread(target=self._do_analyze, args=(path,), daemon=True).start()
        self._update_run_btn()

    def _do_analyze(self, path: str):
        info = analyze_gcode(path)
        self._gcode_info = info
        self.after(0, self._update_info_labels)

    def _update_info_labels(self):
        i = self._gcode_info
        slicer  = i.get("slicer", "—")
        layers  = i.get("layers", 0)
        objects = i.get("objects", 0)
        height  = i.get("layer_height", "—")

        self._i_slicer.configure(text=slicer)
        self._i_layers.configure(text=str(layers) if layers else "—")
        self._i_objects.configure(text=str(objects) if objects else "—")
        self._i_height.configure(text=height)

        color = SLICER_COLORS.get(slicer, MUTED)
        self._slicer_badge.configure(text=f"  {slicer}  ", text_color=color)

        self._log(f"Detekováno: {slicer} | Vrstvy: {layers} | Objekty: {objects} | Výška: {height}", "accent")

    def _pick_models_dir(self):
        path = filedialog.askdirectory(title="Vybrat složku STL modelů")
        if path:
            self.models_path.set(path)
            self._update_run_btn()

    def _pick_output(self):
        path = filedialog.asksaveasfilename(
            title="Uložit výstup jako",
            defaultextension=".gcode",
            filetypes=[("G-code", "*.gcode"), ("Vše", "*.*")],
        )
        if path:
            self.output_path.set(path)

    def _toggle_out(self):
        is_saveas = self.out_mode.get() == "saveas"
        state = "normal" if is_saveas else "disabled"
        self._out_entry.configure(state=state)
        self._out_btn.configure(state=state)
        if is_saveas and self.input_path.get() and not self.output_path.get():
            p = Path(self.input_path.get())
            self.output_path.set(str(p.parent / f"{p.stem}_zaa.gcode"))

    def _update_run_btn(self):
        if self._processing:
            return
        has_input = bool(self.input_path.get())
        if has_input:
            self._run_btn.configure(
                fg_color=ACC_BTN, hover_color=ACCENT, text_color="#000000")
        else:
            self._run_btn.configure(
                fg_color=ACC_DIM, hover_color=ACC_BTN, text_color=TEXT)

    # ── Run ─────────────────────────────────────────────────────────────────────

    def _run(self):
        if self._processing:
            return

        inp = self.input_path.get()
        if not inp:
            self._log("⚠ Nejprve vyberte vstupní .gcode soubor.", "warn")
            return

        models = self.models_path.get() or None
        out    = self.output_path.get() if self.out_mode.get() == "saveas" else None

        plate_model = None
        if self.pos_x.get() and self.pos_y.get() and self.stl_name.get():
            try:
                plate_model = (self.stl_name.get(),
                               float(self.pos_x.get()),
                               float(self.pos_y.get()))
            except ValueError:
                self._log("⚠ Pozice X/Y musí být čísla (např. 125.5).", "warn")
                return

        self._processing = True
        self._run_btn.configure(
            text="⏳   ZPRACOVÁVÁM…", fg_color=BORDER,
            hover_color=BORDER, text_color=MUTED, state="disabled",
        )
        self._prog_label.configure(text="Zpracovávám…", text_color=MUTED)
        self._pbar.set(0.05)
        self._animate_progress()

        self._log(f"\n▶ Spouštím: {Path(inp).name}", "accent")

        threading.Thread(
            target=run_worker,
            args=(inp, models, out, plate_model, self._log_q),
            daemon=True,
        ).start()

    def _animate_progress(self):
        """Indeterminate progress bar animation while processing."""
        if not self._processing:
            return
        val = self._pbar.get()
        val += 0.018 * self._prog_dir
        if val >= 0.92:
            self._prog_dir = -1
        elif val <= 0.05:
            self._prog_dir = 1
        self._pbar.set(val)
        self.after(60, self._animate_progress)

    # ── Log helpers ──────────────────────────────────────────────────────────────

    def _log(self, msg: str, tag: str = "muted"):
        tb = self._logbox._textbox
        tb.configure(state="normal")
        tb.insert("end", msg + "\n", tag)
        tb.configure(state="disabled")
        tb.see("end")

    def _clear_log(self):
        tb = self._logbox._textbox
        tb.configure(state="normal")
        tb.delete("1.0", "end")
        tb.configure(state="disabled")

    # ── Queue poller ─────────────────────────────────────────────────────────────

    def _poll(self):
        try:
            while True:
                kind, msg = self._log_q.get_nowait()
                if kind == "log":
                    self._log(f"  {msg}")
                elif kind == "done":
                    self._processing = False
                    self._prog_dir = 1
                    self._pbar.set(1.0)
                    self._prog_label.configure(text="✓ Hotovo", text_color=SUCCESS)
                    self._log(f"\n✓ {msg}\n", "success")
                    self._run_btn.configure(
                        text="▶   ZPRACOVAT GCODE", state="normal")
                    self._update_run_btn()
                elif kind == "error":
                    self._processing = False
                    self._prog_dir = 1
                    self._pbar.set(0)
                    self._prog_label.configure(text="✗ Chyba", text_color=ERROR)
                    self._log(f"\n✗ Chyba: {msg}\n", "error")
                    self._run_btn.configure(
                        text="▶   ZPRACOVAT GCODE", state="normal")
                    self._update_run_btn()
        except queue.Empty:
            pass
        self.after(100, self._poll)


# ─── Entry point ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
