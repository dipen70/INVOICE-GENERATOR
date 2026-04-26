"""
Invoice activity log. Append-only JSON file at ~/.invoice_app/invoice_log.json.

Every PDF export or browser preview records:
  timestamp · action · invoice_no · client · total · currency
  created_by  {name, email, position}   ← the signed-in Google user
  authorized_by {name, email, position} ← defaults to created_by

Provides a Treeview-based viewer window.
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Optional

APP_DIR = Path.home() / ".invoice_app"
LOG_FILE = APP_DIR / "invoice_log.json"


def _ensure_app_dir() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)


def load_entries() -> list[dict]:
    if not LOG_FILE.exists():
        return []
    try:
        data = json.loads(LOG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, dict):
        return list(data.get("entries", []))
    if isinstance(data, list):
        return data
    return []


def _save_entries(entries: list[dict]) -> None:
    _ensure_app_dir()
    payload = {"entries": entries}
    LOG_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _signer_record(signer: Optional[dict]) -> dict:
    if not signer:
        return {"name": "", "email": "", "position": ""}
    return {
        "name":     signer.get("name", ""),
        "email":    signer.get("email", ""),
        "position": signer.get("position", ""),
    }


def log_event(action: str, data: dict,
              authorized_by: Optional[dict] = None) -> dict:
    """Append a log entry for the given action ('exported_pdf', 'previewed').
    `data` is the invoice dict produced by sections._collect_data().
    `authorized_by` defaults to the signed-in user (self-authorized)."""
    signer = data.get("signer")
    creator = _signer_record(signer)
    authorizer = _signer_record(authorized_by) if authorized_by else creator

    details = data.get("details", {}) or {}
    to = data.get("to", {}) or {}
    client = to.get("company") or to.get("client") or ""

    entry = {
        "timestamp":     datetime.now().isoformat(timespec="seconds"),
        "action":        action,
        "invoice_no":    details.get("invoice_no", ""),
        "issue_date":    details.get("issue_date", ""),
        "due_date":      details.get("due_date", ""),
        "client":        client,
        "total":         round(float(data.get("total", 0.0) or 0.0), 2),
        "currency_code": data.get("currency_code", ""),
        "created_by":    creator,
        "authorized_by": authorizer,
    }

    entries = load_entries()
    entries.append(entry)
    _save_entries(entries)
    return entry


def open_log_file_externally() -> None:
    """Open invoice_log.json in the OS's default JSON handler."""
    if not LOG_FILE.exists():
        _ensure_app_dir()
        _save_entries([])
    path = str(LOG_FILE)
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as exc:
        messagebox.showerror("Could not open log file", str(exc))


def _fmt_money(total: float, code: str) -> str:
    return f"{code} {total:,.2f}".strip()


def show_log_window(parent: tk.Misc | None = None) -> None:
    """Open a modal-ish Toplevel listing every logged action in a sortable
    table. Includes an 'Open JSON file' button."""
    win = tk.Toplevel(parent)
    win.title("Invoice Activity Log")
    win.geometry("1100x500")
    win.configure(bg="#f0f4f8")

    top = tk.Frame(win, bg="#f0f4f8")
    top.pack(fill="x", padx=10, pady=(10, 4))
    tk.Label(
        top, text="Activity Log",
        font=("Segoe UI", 14, "bold"),
        bg="#f0f4f8", fg="#2c3e50",
    ).pack(side="left")

    tk.Button(
        top, text="Open JSON file",
        bg="#2980b9", fg="white", relief="flat",
        font=("Segoe UI", 9, "bold"),
        padx=10, pady=4, cursor="hand2",
        command=open_log_file_externally,
    ).pack(side="right", padx=4)

    tk.Button(
        top, text="Refresh",
        bg="#27ae60", fg="white", relief="flat",
        font=("Segoe UI", 9, "bold"),
        padx=10, pady=4, cursor="hand2",
        command=lambda: _populate(tree),
    ).pack(side="right", padx=4)

    columns = (
        "timestamp", "action", "invoice_no", "client",
        "total", "created_by", "position", "authorized_by",
    )
    headings = {
        "timestamp":     ("When",          150),
        "action":        ("Action",         110),
        "invoice_no":    ("Invoice #",      100),
        "client":        ("Client",         180),
        "total":         ("Total",          120),
        "created_by":    ("Created By",     160),
        "position":      ("Position",       120),
        "authorized_by": ("Authorized By",  160),
    }

    table_frame = tk.Frame(win)
    table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    tree = ttk.Treeview(
        table_frame, columns=columns, show="headings", height=18,
    )
    for col in columns:
        label, width = headings[col]
        tree.heading(col, text=label,
                     command=lambda c=col: _sort_by(tree, c, False))
        anchor = "e" if col == "total" else "w"
        tree.column(col, width=width, anchor=anchor, stretch=True)

    vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)

    style = ttk.Style()
    style.configure("Treeview", rowheight=24, font=("Segoe UI", 9))
    style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    _populate(tree)

    status = tk.Label(
        win, text="", bg="#f0f4f8", fg="#7f8c8d",
        font=("Segoe UI", 8), anchor="w",
    )
    status.pack(fill="x", padx=10, pady=(0, 6))
    status.config(text=f"Log file: {LOG_FILE}")


def _populate(tree: ttk.Treeview) -> None:
    tree.delete(*tree.get_children())
    entries = load_entries()
    # Newest first
    entries = sorted(entries, key=lambda e: e.get("timestamp", ""), reverse=True)
    for e in entries:
        creator = e.get("created_by", {}) or {}
        authorizer = e.get("authorized_by", {}) or {}
        tree.insert("", "end", values=(
            e.get("timestamp", ""),
            e.get("action", ""),
            e.get("invoice_no", ""),
            e.get("client", ""),
            _fmt_money(e.get("total", 0.0), e.get("currency_code", "")),
            creator.get("name", ""),
            creator.get("position", ""),
            authorizer.get("name", ""),
        ))


def _sort_by(tree: ttk.Treeview, col: str, descending: bool) -> None:
    rows = [(tree.set(k, col), k) for k in tree.get_children("")]
    try:
        rows.sort(key=lambda r: float(str(r[0]).split()[-1].replace(",", "")),
                  reverse=descending)
    except (ValueError, IndexError):
        rows.sort(key=lambda r: r[0].lower(), reverse=descending)
    for index, (_, k) in enumerate(rows):
        tree.move(k, "", index)
    tree.heading(col, command=lambda: _sort_by(tree, col, not descending))
