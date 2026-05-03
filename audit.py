"""
Invoice activity log. Append-only JSON file at ~/.invoice_app/invoice_log.json
plus a parallel CSV mirror at ~/.invoice_app/invoice_log.csv that opens
cleanly in Excel / Sheets.

Every PDF export or browser preview records:
  timestamp · action · invoice_no · client · total · currency
  created_by  {name, email, position}   ← the signed-in Google user
  authorized_by {name, email, position} ← defaults to created_by

Provides a Treeview-based viewer window.
"""
from __future__ import annotations

import csv
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
CSV_FILE = APP_DIR / "invoice_log.csv"

CSV_FIELDS = [
    "timestamp", "date", "time",
    "action", "invoice_no", "issue_date", "due_date",
    "client", "total", "currency_code",
    "created_by_name", "created_by_email", "created_by_position",
    "authorized_by_name", "authorized_by_email", "authorized_by_position",
]


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


def _append_csv(entry: dict) -> None:
    """Mirror a log entry into the CSV file. Writes the header row the first
    time the file is created."""
    _ensure_app_dir()
    new_file = not CSV_FILE.exists()
    creator = entry.get("created_by", {}) or {}
    authorizer = entry.get("authorized_by", {}) or {}

    ts = entry.get("timestamp", "")
    date_part, _, time_part = ts.partition("T")

    row = {
        "timestamp":              ts,
        "date":                   date_part,
        "time":                   time_part,
        "action":                 entry.get("action", ""),
        "invoice_no":             entry.get("invoice_no", ""),
        "issue_date":             entry.get("issue_date", ""),
        "due_date":               entry.get("due_date", ""),
        "client":                 entry.get("client", ""),
        "total":                  entry.get("total", 0.0),
        "currency_code":          entry.get("currency_code", ""),
        "created_by_name":        creator.get("name", ""),
        "created_by_email":       creator.get("email", ""),
        "created_by_position":    creator.get("position", ""),
        "authorized_by_name":     authorizer.get("name", ""),
        "authorized_by_email":    authorizer.get("email", ""),
        "authorized_by_position": authorizer.get("position", ""),
    }

    # newline="" keeps csv module from doubling line endings on Windows.
    with open(CSV_FILE, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow(row)


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
    _append_csv(entry)
    return entry


def _open_externally(path: Path) -> None:
    try:
        if platform.system() == "Windows":
            os.startfile(str(path))
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as exc:
        messagebox.showerror("Could not open file", str(exc))


def open_log_file_externally() -> None:
    """Open invoice_log.json in the OS's default JSON handler."""
    if not LOG_FILE.exists():
        _ensure_app_dir()
        _save_entries([])
    _open_externally(LOG_FILE)


def rebuild_csv_from_json() -> int:
    """Recreate the CSV mirror from the JSON log. Returns row count.
    Useful if the CSV is missing or got corrupted."""
    entries = load_entries()
    _ensure_app_dir()
    if CSV_FILE.exists():
        CSV_FILE.unlink()
    for entry in entries:
        _append_csv(entry)
    return len(entries)


def open_csv_file_externally() -> None:
    """Open invoice_log.csv in the OS's default CSV handler (Excel, etc.).
    Builds it from the JSON log if it doesn't exist yet."""
    if not CSV_FILE.exists():
        rebuild_csv_from_json()
    _open_externally(CSV_FILE)


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
        top, text="Open CSV file",
        bg="#16a085", fg="white", relief="flat",
        font=("Segoe UI", 9, "bold"),
        padx=10, pady=4, cursor="hand2",
        command=open_csv_file_externally,
    ).pack(side="right", padx=4)

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
