"""
Invoice Generator — Colours, fonts, and   fUI helpers.
"""
import tkinter as tk
from tkinter import ttk

# ── Colour palette
DARK    = "#2c3e50"
ACCENT  = "#2980b9"
GREEN   = "#27ae60"
ORANGE  = "#e67e22"
RED     = "#e74c3c"
LGRAY   = "#ecf0f1"
MIDGRAY = "#95a5a6"
BG      = "#f0f4f8"
WHITE   = "#ffffff"
ALTROW  = "#f4f6f7"

# ── Fonts
FONT        = ("Segoe UI", 9)
FONT_BOLD   = ("Segoe UI", 9, "bold")
FONT_SMALL  = ("Segoe UI", 8)
FONT_LARGE  = ("Segoe UI", 20, "bold")
FONT_TITLE  = ("Segoe UI", 11, "bold")


def _card(parent, title, pack_kw=None):
    """LabelFrame styled as a white card.  Returns the inner frame."""
    frame = tk.LabelFrame(parent, text=f"  {title}  ",
                          font=FONT_BOLD, bg=WHITE, fg=DARK,
                          relief="solid", bd=1, padx=10, pady=8)
    if pack_kw is None:
        pack_kw = {}
    return frame


def _field_row(parent, label, row, col=0, default="", width=26):
    """Label + Entry pair placed via grid."""
    tk.Label(parent, text=label, font=FONT, bg=WHITE).grid(
        row=row, column=col, sticky="w", padx=(4, 2), pady=3)
    e = tk.Entry(parent, font=FONT, width=width, relief="solid", bd=1)
    if default:
        e.insert(0, default)
    e.grid(row=row, column=col + 1, sticky="ew", padx=(0, 10), pady=3)
    return e


def _apply_styles():
    s = ttk.Style()
    s.theme_use("clam")
    s.configure("TFrame",            background=BG)
    s.configure("TLabel",            background=BG, font=FONT)
    s.configure("TLabelframe",       background=WHITE, relief="flat", borderwidth=1)
    s.configure("TLabelframe.Label", background=WHITE, font=FONT_BOLD, foreground=DARK)
    s.configure("TEntry",            padding=4, relief="flat")
    s.configure("TCombobox",         padding=4)
    s.configure("TScrollbar",        background=MIDGRAY)
