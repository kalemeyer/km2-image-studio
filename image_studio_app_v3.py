import json
import os
import re
import datetime

CONFIG_PATH = os.path.expanduser("~/.km2studio/config.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {}

config = load_config()

def _seo_slug(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    text = re.sub(r"-{2,}", "-", text)
    return text

def ai_build_filename(product_type: str, colors: list[str], brand_keywords: list[str]) -> str:
    """
    Heuristic 'AI-style' SEO filename:
    - includes brand keywords (deduped)
    - includes colors (primary first)
    - includes product type
    - adds a compact timestamp for uniqueness
    Example:
    km2-custom-leather-patch-trucker-hat-black-white-20251030-1254
    """
    # Clean pieces
    kw = [_seo_slug(k) for k in (brand_keywords or []) if k.strip()]
    kw = list(dict.fromkeys(kw))[:4]  # keep order, de-dupe, cap to 4

    color_part = _seo_slug("-".join([c for c in colors if c])) if colors else ""
    prod_part = _seo_slug(product_type or "hat")

    parts = [*kw, prod_part]
    if color_part:
        parts.append(color_part)

    base = "-".join([p for p in parts if p])
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    return f"{base}-{stamp}" if base else stamp


DEFAULT_INPUT_DIR = config.get("default_input_folder", os.path.expanduser("~"))
DEFAULT_OUTPUT_DIR = config.get("default_output_folder", os.path.expanduser("~"))

print("Loaded KM2 Config:", config)


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KM2 Image Studio — by Vera (v3 UX refresh)
- Cleaner, guided GUI with inline notes
- Drag & Drop images (requires tkinterdnd2; falls back gracefully with instructions)
- Background removal (rembg) optional
- Export white-canvas JPG and optional transparent PNG
- Auto rename, alt text + SEO tags, CSV manifest
- After successful processing, moves ORIGINAL files to a configurable "Finished (originals)" folder

Install (recommended):
    pip install pillow rembg tkinterdnd2
"""

import os, sys, csv, math, datetime, shutil
from dataclasses import dataclass
from typing import List, Tuple, Optional

try:
    from PIL import Image, ImageDraw, ImageFilter
except ImportError:
    print("This app requires Pillow. Install it with: pip install pillow")
    sys.exit(1)

_HAVE_REMBG = True
try:
    from rembg import remove as rembg_remove
except Exception:
    _HAVE_REMBG = False

_HAVE_DND = True
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except Exception:
    _HAVE_DND = False
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
else:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

BASIC_PALETTE = {
    "black": (0,0,0), "white": (255,255,255), "gray": (128,128,128),
    "red": (220,20,60), "maroon": (128,0,0),
    "orange": (255,140,0), "brown": (139,69,19), "tan": (210,180,140),
    "yellow": (255,215,0), "gold": (218,165,32),
    "green": (34,139,34), "olive": (107,142,35),
    "teal": (0,128,128), "cyan": (0,139,139), "turquoise": (64,224,208),
    "blue": (30,144,255), "navy": (0,0,128), "royal": (65,105,225),
    "purple": (128,0,128), "violet": (138,43,226),
    "pink": (255,105,180), "magenta": (255,0,255),
    "burgundy": (128,0,32), "charcoal": (54,69,79)
}

SOCIAL_PRESETS = [
    ("Instagram Post", 1080, 1080, 0),
    ("Instagram Story", 1080, 1920, 0),
    ("Facebook Post", 1200, 630, 0),
    ("LinkedIn Post", 1200, 627, 0),
    ("Pinterest Pin", 1000, 1500, 0),
    ("YouTube Thumbnail", 1280, 720, 0),
]

def _rgb_dist(a, b):
    return sum((a[i]-b[i])**2 for i in range(3))

def nearest_basic_color(rgb):
    best, bestd = None, 10**9
    for name, val in BASIC_PALETTE.items():
        d = _rgb_dist(rgb, val)
        if d < bestd:
            bestd, best = d, name
    return best

def get_dominant_colors(img, top_k=3):
    small = img.convert("RGB").resize((64, 64))
    pal_img = small.quantize(colors=32).convert("RGB")
    colors = pal_img.getcolors(64*64) or []
    colors.sort(reverse=True, key=lambda x: x[0])
    names = []
    for count, rgb in colors[:top_k*2]:
        name = nearest_basic_color(rgb)
        if name not in names:
            names.append(name)
        if len(names) >= top_k:
            break
    return names or ["unknown"]

@dataclass
class Config:
    target_w: int = 1600
    target_h: int = 1600
    margin: int = 60
    add_watermark: bool = True
    wm_path: Optional[str] = None
    wm_opacity: float = 0.08
    wm_scale: float = 0.4
    product_type: str = "custom hat"
    rename_template: str = "{product}-{colors}-{timestamp}"
    add_shadow: bool = True
    use_rembg: bool = True
    export_jpg: bool = True
    export_png: bool = False
    move_originals: bool = True
    finished_folder: Optional[str] = None

def fit_within(img, max_w, max_h):
    img = img.copy()
    img.thumbnail((max_w, max_h), Image.LANCZOS)
    return img

def sanitize_slug(s: str) -> str:
    keep = "abcdefghijklmnopqrstuvwxyz0123456789-_"
    s = s.lower().replace(" ", "-")
    s = "".join(ch for ch in s if ch in keep)
    while "--" in s:
        s = s.replace("--", "-")
    return s.strip("-") or "image"

def timestamp_str() -> str:
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

def build_filename(tmpl: str, product: str, colors: List[str]) -> str:
    return tmpl.format(
        product=sanitize_slug(product),
        colors="-".join(colors),
        timestamp=timestamp_str()
    )

def generate_alt_text(product: str, colors: List[str], bg_removed: bool) -> str:
    mc = ", ".join(colors[:2]) if colors else "neutral"
    return (f"{product.title()} with {mc} tones on a transparent or clean background, e-commerce ready product photo."
            if bg_removed else
            f"{product.title()} with {mc} tones on a white studio background, angled product photo for e-commerce.")

def generate_tags(product: str, colors: List[str]) -> List[str]:
    base = [product, "custom", "laser engraved", "KM2", "leather patch", "snapback", "trucker hat",
            "premium", "gift", "local business", "Florida", "Lynn Haven"]
    seen, out = set(), []
    for x in base + colors:
        if x not in seen:
            out.append(x); seen.add(x)
    return out

def process_one(path: str, outdir: str, cfg: Config):
    im = Image.open(path).convert("RGBA")
    bg_removed = False
    subject = im
    if cfg.use_rembg:
        if not _HAVE_REMBG:
            raise RuntimeError("Background removal requested but 'rembg' is not installed. pip install rembg")
        subject = rembg_remove(im)
        bg_removed = True

    colors = get_dominant_colors(subject.convert("RGB"), top_k=3)

    canvas = Image.new("RGBA", (cfg.target_w, cfg.target_h), (255,255,255,255))
    avail_w = cfg.target_w - cfg.margin*2
    avail_h = cfg.target_h - cfg.margin*2
    fitted = fit_within(subject, avail_w, avail_h)

    if cfg.add_shadow:
        shadow = Image.new("RGBA", fitted.size, (0,0,0,0))
        sd = ImageDraw.Draw(shadow)
        sx, sy = fitted.size
        sd.ellipse([int(sx*0.1), int(sy*0.75), int(sx*0.9), int(sy*0.95)], fill=(0,0,0,40))
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=12))
        cx = (cfg.target_w - sx)//2
        cy = (cfg.target_h - sy)//2 + int(sy*0.08)
        canvas.alpha_composite(shadow, (cx, cy))
        canvas.alpha_composite(fitted, (cx, cy))
    else:
        cx = (cfg.target_w - fitted.size[0])//2
        cy = (cfg.target_h - fitted.size[1])//2
        canvas.alpha_composite(fitted, (cx, cy))

    if cfg.add_watermark and cfg.wm_path and os.path.isfile(cfg.wm_path):
        try:
            logo = Image.open(cfg.wm_path)
            target_w = int(cfg.target_w * cfg.wm_scale)
            aspect = logo.size[1]/logo.size[0]
            logo = logo.resize((target_w, int(target_w*aspect)))
            if logo.mode != "RGBA":
                logo = logo.convert("RGBA")
            alpha = logo.split()[-1].point(lambda p: int(p * cfg.wm_opacity))
            logo.putalpha(alpha)
            logo = logo.filter(ImageFilter.GaussianBlur(radius=1.0))
            lx = (cfg.target_w - logo.size[0])//2
            ly = int(cfg.target_h * 0.1)
            canvas.alpha_composite(logo, (lx, ly))
        except Exception:
            pass

    if config.get("enable_ai_filenames", False):
        base_name = ai_build_filename(cfg.product_type, colors, config.get("brand_keywords", []))
    else:
        base_name = build_filename(cfg.rename_template, cfg.product_type, colors)


    jpg_name = f"{base_name}.jpg"
    out_jpg = os.path.join(outdir, jpg_name)
    canvas.convert("RGB").save(out_jpg, "JPEG", quality=92, optimize=True)

    transparent_png = None
    if bg_removed and cfg.export_png:
        transparent_png = f"{base_name}.png"
        out_png = os.path.join(outdir, transparent_png)
        trans_canvas = Image.new("RGBA", (cfg.target_w, cfg.target_h), (0,0,0,0))
        fitted_alpha = fit_within(subject, avail_w, avail_h)
        tx = (cfg.target_w - fitted_alpha.size[0])//2
        ty = (cfg.target_h - fitted_alpha.size[1])//2
        trans_canvas.alpha_composite(fitted_alpha, (tx, ty))
        trans_canvas.save(out_png, "PNG", optimize=True)

    alt_text = generate_alt_text(cfg.product_type, colors, bg_removed)
    tags = generate_tags(cfg.product_type, colors)

    return {
        "original": os.path.basename(path),
        "jpg": jpg_name,
        "png": transparent_png,
        "alt_text": alt_text,
        "tags": tags,
        "colors": colors
    }

class AppBase:
    def __init__(self):
        self.root = TkinterDnD.Tk() if _HAVE_DND else tk.Tk()
        self.root.title("KM2 Image Studio — Vera (v3)")
        self.root.geometry("880x700")
        self.root.minsize(820, 640)

        self._init_vars()
        self._style()
        self._build_layout()

    def _init_vars(self):
        self.product_type = tk.StringVar(value="custom hat")
        self.rename_template = tk.StringVar(value="{product}-{colors}-{timestamp}")
        self.target_w = tk.StringVar(value="1600")
        self.target_h = tk.StringVar(value="1600")
        self.margin = tk.StringVar(value="60")
        self.logo_path = tk.StringVar(value="")
        self.add_wm = tk.BooleanVar(value=True)
        self.wm_opacity = tk.DoubleVar(value=0.08)
        self.wm_scale = tk.DoubleVar(value=0.4)
        self.add_shadow = tk.BooleanVar(value=True)
        self.use_rembg = tk.BooleanVar(value=True)
        self.export_jpg = tk.BooleanVar(value=True)
        self.export_png = tk.BooleanVar(value=False)
        self.move_originals = tk.BooleanVar(value=True)

        self.finished_folder = tk.StringVar(value="")
        self.output_folder = tk.StringVar(value="")
        self.input_folder = tk.StringVar(value="")

        # defaults from config
        self.input_folder.set(DEFAULT_INPUT_DIR)
        self.output_folder.set(DEFAULT_OUTPUT_DIR)

        self.file_list = []



    def _style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass

    def _build_layout(self):
        container = ttk.Frame(self.root, padding=10)
        container.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        container.columnconfigure(0, weight=1, minsize=380)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(2, weight=1)

        header = ttk.Label(container, text="KM2 Image Studio", font=("Segoe UI", 16, "bold"))
        header.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,6))

        note = ttk.Label(container, foreground="#444",
                         text=("Tip: Drag & drop images into the box on the right.\n"
                               "I’ll standardize them, auto-name with colors, and export JPGs (and PNGs if you want)."))
        note.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0,10))

        left = ttk.LabelFrame(container, text="Settings")
        left.grid(row=2, column=0, sticky="nsew", padx=(0,8))
        for i in range(14):
            left.rowconfigure(i, weight=0)
        left.columnconfigure(1, weight=1)

        ttk.Label(left, text="Product type").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(left, textvariable=self.product_type).grid(row=0, column=1, sticky="ew", padx=6, pady=4)

        ttk.Label(left, text="Rename template").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(left, textvariable=self.rename_template).grid(row=1, column=1, sticky="ew", padx=6, pady=4)
        ttk.Label(left, text="Use {product}, {colors}, {timestamp}", foreground="#666").grid(row=2, column=1, sticky="w", padx=6, pady=(0,8))

        ttk.Label(left, text="Export size (px)").grid(row=3, column=0, sticky="w", padx=6, pady=4)
        size_frame = ttk.Frame(left)
        ttk.Entry(size_frame, width=8, textvariable=self.target_w).pack(side="left")
        ttk.Label(size_frame, text="×").pack(side="left", padx=4)
        ttk.Entry(size_frame, width=8, textvariable=self.target_h).pack(side="left")
        size_frame.grid(row=3, column=1, sticky="w", padx=6, pady=4)

        ttk.Label(left, text="Social presets").grid(row=4, column=0, sticky="nw", padx=6, pady=(0,4))
        preset_frame = ttk.Frame(left)
        for idx, (label, _, _, _) in enumerate(SOCIAL_PRESETS):
            btn = ttk.Button(preset_frame, text=label, command=lambda n=label: self._apply_preset(n))
            btn.grid(row=idx//2, column=idx%2, sticky="ew", padx=2, pady=2)
        for col in range(2):
            preset_frame.columnconfigure(col, weight=1)
        preset_frame.grid(row=4, column=1, sticky="ew", padx=6, pady=(0,4))

        ttk.Label(left, text="Margin (px)").grid(row=5, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(left, width=8, textvariable=self.margin).grid(row=5, column=1, sticky="w", padx=6, pady=4)

        ttk.Label(left, text="Logo (PNG, optional)").grid(row=6, column=0, sticky="w", padx=6, pady=4)
        logo_row = ttk.Frame(left)
        ttk.Entry(logo_row, textvariable=self.logo_path).pack(side="left", fill="x", expand=True)
        ttk.Button(logo_row, text="Browse", command=self._pick_logo).pack(side="left", padx=4)
        logo_row.grid(row=6, column=1, sticky="ew", padx=6, pady=4)

        wm_row = ttk.Frame(left)
        ttk.Checkbutton(wm_row, text="Add soft logo projection", variable=self.add_wm).pack(side="left")
        ttk.Label(wm_row, text="Opacity").pack(side="left", padx=(10,2))
        ttk.Spinbox(wm_row, width=5, from_=0.0, to=0.6, increment=0.01, textvariable=self.wm_opacity).pack(side="left")
        ttk.Label(wm_row, text="Scale").pack(side="left", padx=(10,2))
        ttk.Spinbox(wm_row, width=5, from_=0.1, to=0.9, increment=0.05, textvariable=self.wm_scale).pack(side="left")
        wm_row.grid(row=7, column=1, sticky="w", padx=6, pady=4)

        opt_row = ttk.Frame(left)
        # Export & processing options
        self.export_jpg = tk.BooleanVar(value=True)
        self.export_png = tk.BooleanVar(value=False)

        ttk.Checkbutton(opt_row, text="Export JPG", variable=self.export_jpg).pack(side="left")
        ttk.Checkbutton(opt_row, text="Export PNG", variable=self.export_png).pack(side="left", padx=10)
        ttk.Checkbutton(opt_row, text="Remove background", variable=self.use_rembg).pack(side="left", padx=10)
        ttk.Checkbutton(opt_row, text="Add product shadow", variable=self.add_shadow).pack(side="left", padx=10)
        opt_row.grid(row=8, column=0, columnspan=2, sticky="w", padx=6, pady=4)


        ttk.Label(left, text="Output folder").grid(row=9, column=0, sticky="w", padx=6, pady=4)
        out_row = ttk.Frame(left)
        self.output_entry = ttk.Entry(out_row, textvariable=self.output_folder)
        self.output_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(out_row, text="Browse", command=self._pick_output).pack(side="left", padx=4)
        out_row.grid(row=9, column=1, sticky="ew", padx=6, pady=4)
        ttk.Label(left, text="Processed JPG/PNG and the CSV manifest go here.", foreground="#666").grid(row=10, column=1, sticky="w", padx=6, pady=(0,8))

        ttk.Label(left, text="Finished (originals) folder").grid(row=11, column=0, sticky="w", padx=6, pady=4)
        fin_row = ttk.Frame(left)
        self.finished_entry = ttk.Entry(fin_row, textvariable=self.finished_folder)
        self.finished_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(fin_row, text="Browse", command=self._pick_finished).pack(side="left", padx=4)
        fin_row.grid(row=11, column=1, sticky="ew", padx=6, pady=4)
        ttk.Label(left, text="After success, ORIGINAL files are moved here (keeps your raw folder clean).", foreground="#666").grid(row=12, column=1, sticky="w", padx=6, pady=(0,8))

        act = ttk.Frame(left)
        ttk.Button(act, text="Process Queue", command=self._process_queue).pack(side="left", padx=4)
        ttk.Button(act, text="Clear Queue", command=self._clear_queue).pack(side="left", padx=4)
        ttk.Button(act, text="Add Files…", command=self._add_files).pack(side="left", padx=4)
        ttk.Button(act, text="Help", command=self._help).pack(side="left", padx=4)
        act.grid(row=13, column=0, columnspan=2, sticky="w", padx=6, pady=8)

        right = ttk.LabelFrame(container, text="Drop Zone & Progress")
        right.grid(row=2, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        self.drop_lbl = ttk.Label(right, text=("Drop images here\n(PNG/JPG/WEBP)\n\n"
                                               + ("✅ Drag & drop enabled"
                                                  if _HAVE_DND else
                                                  "⚠️ Install tkinterdnd2 to enable drag & drop:\n   pip install tkinterdnd2")),
                                  relief="ridge", anchor="center")
        self.drop_lbl.grid(row=0, column=0, sticky="ew", padx=8, pady=8, ipadx=12, ipady=24)

        if _HAVE_DND:
            self.drop_lbl.drop_target_register(DND_FILES)
            self.drop_lbl.dnd_bind("<<Drop>>", self._on_drop)

        self.listbox = tk.Listbox(right, height=10, selectmode="extended")
        self.listbox.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0,8))

        self.log = tk.Text(right, height=10)
        self.log.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0,8))

    def _log(self, s: str):
        self.log.insert("end", s + "\n")
        self.log.see("end")
        self.root.update_idletasks()

    def _apply_preset(self, name: str):
        for label, w, h, margin in SOCIAL_PRESETS:
            if label == name:
                self.target_w.set(str(w))
                self.target_h.set(str(h))
                self.margin.set(str(margin))
                self._log(f"Applied preset: {label} → {w}×{h}px (margin {margin}px)")
                break

    def _pick_logo(self):
        f = filedialog.askopenfilename(filetypes=[("Image files","*.png;*.jpg;*.jpeg")])
        if f: self.logo_path.set(f)

    def _pick_output(self):
        d = filedialog.askdirectory(initialdir=DEFAULT_OUTPUT_DIR)
        if d: self.output_folder.set(d)

    def _pick_finished(self):
        d = filedialog.askdirectory(initialdir=DEFAULT_INPUT_DIR)
        if d: self.finished_folder.set(d)

    def _help(self):
        msg = ("Workflow:\n"
               "1) Set product type, size, and options on the left.\n"
               "2) Drag images into the drop zone (or use Add Files…).\n"
               "3) Choose your Output folder.\n"
               "4) (Optional) Choose a Finished folder — originals will be MOVED there after success.\n"
               "5) Click Process Queue.\n\n"
               f"Background removal: {'ON by default' if self.use_rembg.get() else 'OFF by default'}"
               + ("" if _HAVE_REMBG else "\nNOTE: rembg not detected. Install: pip install rembg"))
        messagebox.showinfo("Help", msg)

    def _add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Images","*.png;*.jpg;*.jpeg;*.webp")])
        self._add_paths(files)

    def _on_drop(self, event):
        raw = event.data
        paths, buf, in_brace = [], "", False
        for ch in raw:
            if ch == "{":
                in_brace = True; buf = ""; continue
            if ch == "}":
                in_brace = False; paths.append(buf); buf = ""; continue
            if ch == " " and not in_brace:
                if buf: paths.append(buf); buf = ""
            else:
                buf += ch
        if buf: paths.append(buf)
        self._add_paths(paths)

    def _add_paths(self, paths):
        exts = {".png",".jpg",".jpeg",".webp"}
        count = 0
        for p in paths:
            if not p: continue
            if os.path.isdir(p):
                for fname in os.listdir(p):
                    ext = os.path.splitext(fname.lower())[1]
                    if ext in exts:
                        full = os.path.join(p, fname)
                        if full not in self.file_list:
                            self.file_list.append(full)
                            self.listbox.insert("end", full)
                            count += 1
            else:
                ext = os.path.splitext(p.lower())[1]
                if ext in exts and p not in self.file_list:
                    self.file_list.append(p)
                    self.listbox.insert("end", p)
                    count += 1
        if count:
            self._log(f"Added {count} file(s) to queue.")

    def _clear_queue(self):
        self.file_list = []
        self.listbox.delete(0, "end")
        self._log("Queue cleared.")

    def _process_queue(self):
        if not self.file_list:
            messagebox.showwarning("No files", "Add or drop some images first.")
            return
        outdir = self.output_folder.get().strip()
        if not outdir or not os.path.isdir(outdir):
            messagebox.showerror("Missing output", "Please choose a valid Output folder.")
            return

        fin_dir = self.finished_folder.get().strip()
        if not fin_dir:
           # Default archive next to the source photos
           base_input = self.input_folder.get().strip() or (os.path.dirname(self.file_list[0]) if self.file_list       else outdir)
           fin_dir = os.path.join(base_input, "Finished_Originals")
           os.makedirs(fin_dir, exist_ok=True)


        try:
            cfg = Config(
                target_w = int(self.target_w.get() or "1600"),
                target_h = int(self.target_h.get() or "1600"),
                margin = int(self.margin.get() or "60"),
                add_watermark = bool(self.add_wm.get()),
                wm_path = self.logo_path.get().strip() or None,
                wm_opacity = float(self.wm_opacity.get() or 0.08),
                wm_scale = float(self.wm_scale.get() or 0.4),
                product_type = self.product_type.get().strip() or "custom hat",
                rename_template = self.rename_template.get().strip() or "{product}-{colors}-{timestamp}",
                add_shadow = bool(self.add_shadow.get()),
                use_rembg = bool(self.use_rembg.get()),
                export_jpg = bool(self.export_jpg.get()),
		export_png = bool(self.export_png.get()),

                move_originals = True,
                finished_folder = fin_dir
            )
        except Exception as e:
            messagebox.showerror("Invalid settings", f"Please check settings: {e}")
            return

        manifest_path = os.path.join(outdir, f"km2_manifest_{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.csv")
        with open(manifest_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            extra = ["transparent_png"] if (cfg.use_rembg and cfg.export_png) else []
            writer.writerow(["original_name","new_filename","alt_text","tags"] + extra)

            total = len(self.file_list)
            self._log(f"Processing {total} image(s)...")
            if cfg.use_rembg and not _HAVE_REMBG:
                self._log("⚠️ Background removal requested but 'rembg' not installed. Install: pip install rembg")

            ok = 0
            for i, fpath in enumerate(list(self.file_list), 1):
                try:
                    info = process_one(fpath, outdir, cfg)
                    row = [info["original"], info["jpg"], info["alt_text"], "|".join(info["tags"])]
                    if cfg.use_rembg and cfg.export_png:
                        row.append(info["png"] or "")
                    writer.writerow(row)
                    ok += 1
                    self._log(f"[{i}/{total}] ✅ {os.path.basename(fpath)} → {info['jpg']}" + (f" (+ {info['png']})" if info['png'] else ""))

                    # Move original file on success
                    dest = os.path.join(cfg.finished_folder, os.path.basename(fpath))
                    try:
                        if os.path.abspath(fpath) != os.path.abspath(dest):
                            shutil.move(fpath, dest)
                            self._log(f"   ↳ moved original → {dest}")
                    except Exception as me:
                        self._log(f"   ↳ ⚠️ couldn't move original: {me}")

                except Exception as e:
                    self._log(f"[{i}/{total}] ❌ {os.path.basename(fpath)}: {e}")

        self._log(f"Done. {ok}/{total} succeeded. Manifest: {manifest_path}")
        self._clear_queue()
        messagebox.showinfo("Complete", f"All set.\n{ok}/{total} succeeded.\nManifest:\n{manifest_path}")

def main():
    AppBase().root.mainloop()

if __name__ == "__main__":
    main()
