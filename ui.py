"""
Invoice Generator — Main UI entry point.
Builds the scrollable shell and delegates each section to sections.py.
"""
import tkinter as tk
from tkinter import ttk

from constants import BG, _apply_styles
from sections import (
    _header, _from_to, _invoice_details,
    _line_items, _totals, _notes_terms, _action_bar,
)


def build_ui(root):
    root.title("Invoice Generator")
    root.geometry("1020x820")
    root.configure(bg=BG)
    root.minsize(900, 640)

    _apply_styles()

    # ── Outer scrollable canvas
    container = tk.Frame(root, bg=BG)
    container.pack(fill="both", expand=True)

    canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
    vsb    = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)

    vsb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    scroll_frame = tk.Frame(canvas, bg=BG)
    win_id = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

    scroll_frame.bind("<Configure>",
        lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>",
        lambda e: canvas.itemconfig(win_id, width=e.width))
    canvas.bind_all("<MouseWheel>",
        lambda e: canvas.yview_scroll(int(-1 * e.delta / 120), "units"))

    # ── Build each section
    _header(scroll_frame)
    _from_to(scroll_frame)
    _invoice_details(scroll_frame)
    _line_items(scroll_frame)
    _totals(scroll_frame)
    _notes_terms(scroll_frame)
    _action_bar(scroll_frame)


if __name__ == "__main__":
    root = tk.Tk()
    build_ui(root)
    root.mainloop()
