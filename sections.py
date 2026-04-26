# Section builders for ui.py. Each section wires its widgets into the
# module-level `state` dict so the action bar can collect values for export.
import tkinter as tk
from tkinter import ttk
import datetime

from constants import (
    DARK, ACCENT, GREEN, ORANGE, RED, MIDGRAY, BG, WHITE, ALTROW,
    FONT, FONT_BOLD, FONT_LARGE, FONT_SMALL,
    _card, _field_row,
)
from exporters import open_in_browser, export_pdf
from currencies import display_options, code_from_label, symbol_for

try:
    from tkcalendar import DateEntry
    _HAS_TKCAL = True
except ImportError:
    DateEntry = None
    _HAS_TKCAL = False


state = {
    "from": {},
    "to": {},
    "details": {},
    "items": [],
    "items_frame": None,
    "totals": {},
    "bank": {},
    "notes": None,
    "terms": None,
    "signer": None,
    "signer_label": None,
}


def _header(parent, signer=None, root=None):
    bar = tk.Frame(parent, bg=DARK, height=64)
    bar.pack(fill="x")
    bar.pack_propagate(False)

    tk.Label(bar, text="  INVOICE GENERATOR",
             font=FONT_LARGE, bg=DARK, fg="#ecf0f1").pack(side="left", padx=20)
    tk.Label(bar, text="Professional Billing Tool",
             font=FONT, bg=DARK, fg=MIDGRAY).pack(side="left", padx=4)

    if signer:
        state["signer"] = signer

        right = tk.Frame(bar, bg=DARK)
        right.pack(side="right", padx=14)

        info = tk.Frame(right, bg=DARK)
        info.pack(side="left", padx=(0, 10))
        tk.Label(info, text=signer.get("name", ""),
                 font=FONT_BOLD, bg=DARK, fg="#ecf0f1",
                 anchor="e").pack(anchor="e")
        signer_lbl = tk.Label(
            info,
            text=f"{signer.get('position','')}  ·  {signer.get('email','')}",
            font=FONT_SMALL, bg=DARK, fg=MIDGRAY, anchor="e",
        )
        signer_lbl.pack(anchor="e")
        state["signer_label"] = signer_lbl

        tk.Button(right, text="Edit Position", font=FONT_SMALL,
                  bg=ACCENT, fg="white", relief="flat",
                  padx=8, pady=4, cursor="hand2",
                  command=lambda: _edit_position(root)).pack(
            side="left", padx=4)

        tk.Button(right, text="Logout", font=FONT_SMALL,
                  bg=RED, fg="white", relief="flat",
                  padx=8, pady=4, cursor="hand2",
                  command=lambda: _logout(root)).pack(
            side="left", padx=4)


def _edit_position(root):
    from auth import update_position
    signer = state.get("signer")
    if not signer:
        return
    new_pos = update_position(parent=root, signer=signer)
    if new_pos and state.get("signer_label"):
        state["signer_label"].config(
            text=f"{new_pos}  ·  {signer.get('email','')}"
        )


def _logout(root):
    from auth import logout, login_screen
    from ui import build_ui
    logout()
    if root is not None:
        root.destroy()

    def restart(signer):
        new_root = tk.Tk()
        build_ui(new_root, signer)
        new_root.mainloop()

    login_screen(on_success=restart)


def _date_field(parent, label, row, col, default):
    """Calendar dropdown date picker. Falls back to a plain Entry if
    tkcalendar isn't installed. The returned widget exposes .get() that
    yields a 'YYYY-MM-DD' string either way."""
    tk.Label(parent, text=label, font=FONT, bg=WHITE).grid(
        row=row, column=col, sticky="w", padx=(4, 2), pady=3)

    if _HAS_TKCAL:
        de = DateEntry(
            parent, width=14, font=FONT, date_pattern="yyyy-mm-dd",
            background=ACCENT, foreground="white", borderwidth=1,
            year=default.year, month=default.month, day=default.day,
        )
        de.grid(row=row, column=col + 1, sticky="w", padx=(0, 10), pady=3)
        return de

    # Fallback — plain entry
    e = tk.Entry(parent, font=FONT, width=16, relief="solid", bd=1)
    e.insert(0, default.strftime("%Y-%m-%d"))
    e.grid(row=row, column=col + 1, sticky="w", padx=(0, 10), pady=3)
    return e


def _from_to(parent):
    outer = tk.Frame(parent, bg=BG)
    outer.pack(fill="x", padx=18, pady=(8, 4))

    from_card = _card(outer, "From  (Your Company)")
    from_card.pack(side="left", fill="both", expand=True, padx=(0, 6))

    state["from"]["company"]      = _field_row(from_card, "Company Name:",       0)
    state["from"]["address"]      = _field_row(from_card, "Address:",            1)
    state["from"]["citystatezip"] = _field_row(from_card, "City / State / ZIP:", 2)
    state["from"]["email"]        = _field_row(from_card, "Email:",              3)
    state["from"]["phone"]        = _field_row(from_card, "Phone:",              4)
    state["from"]["website"]      = _field_row(from_card, "Website:",            5)

    to_card = _card(outer, "Bill To  (Client)")
    to_card.pack(side="left", fill="both", expand=True, padx=(6, 0))

    state["to"]["client"]       = _field_row(to_card, "Client Name:",        0)
    state["to"]["company"]      = _field_row(to_card, "Company:",            1)
    state["to"]["address"]      = _field_row(to_card, "Address:",            2)
    state["to"]["citystatezip"] = _field_row(to_card, "City / State / ZIP:", 3)
    state["to"]["email"]        = _field_row(to_card, "Email:",              4)
    state["to"]["phone"]        = _field_row(to_card, "Phone:",              5)


def _invoice_details(parent):
    card = _card(parent, "Invoice Details")
    card.pack(fill="x", padx=18, pady=4)

    today = datetime.date.today()
    due   = today + datetime.timedelta(days=30)

    state["details"]["invoice_no"] = _field_row(card, "Invoice #:",  0, col=0, default="INV-001")

    state["details"]["issue_date"] = _date_field(card, "Issue Date:", 0, col=2, default=today)
    state["details"]["due_date"]   = _date_field(card, "Due Date:",   0, col=4, default=due)

    state["details"]["po_number"]  = _field_row(card, "PO Number:", 1, col=0)

    tk.Label(card, text="Currency:", font=FONT, bg=WHITE).grid(
        row=1, column=2, sticky="w", padx=(4, 2), pady=3)
    options = display_options()
    default = next((o for o in options if o.startswith("USD ")), options[0])
    cb_currency = ttk.Combobox(card, width=32, state="readonly", values=options)
    cb_currency.set(default)
    cb_currency.grid(row=1, column=3, sticky="w", padx=(0, 10), pady=3)
    cb_currency.bind("<<ComboboxSelected>>", lambda _e: _recalculate())
    state["details"]["currency"] = cb_currency

    tk.Label(card, text="Payment Terms:", font=FONT, bg=WHITE).grid(
        row=1, column=4, sticky="w", padx=(4, 2), pady=3)
    cb_terms = ttk.Combobox(card, width=16, state="readonly",
        values=["Net 30", "Net 15", "Net 60", "Due on Receipt", "Net 90", "2/10 Net 30"])
    cb_terms.set("Net 30")
    cb_terms.grid(row=1, column=5, sticky="w", padx=(0, 10), pady=3)
    state["details"]["payment_terms"] = cb_terms

    tk.Label(card, text="Payment Method:", font=FONT, bg=WHITE).grid(
        row=2, column=0, sticky="w", padx=(4, 2), pady=3)
    cb_method = ttk.Combobox(card, width=16, state="readonly",
        values=["Bank Transfer", "Credit Card", "PayPal", "Check", "Cash", "Crypto"])
    cb_method.set("Bank Transfer")
    cb_method.grid(row=2, column=1, sticky="w", padx=(0, 10), pady=3)
    state["details"]["payment_method"] = cb_method


def _line_items(parent):
    card = _card(parent, "Line Items")
    card.pack(fill="x", padx=18, pady=4)

    hdr = tk.Frame(card, bg=DARK)
    hdr.pack(fill="x", pady=(0, 3))

    columns = [
        ("Description", 38), 
        ("Qty",          7),
        ("Unit Price",  12),
        ("Disc %",       7),
        ("Amount",      12),
        ("",             4),
    ]
    for text, w in columns:
        tk.Label(hdr, text=text, font=FONT_BOLD, bg=DARK, fg="white",
                 width=w, anchor="center", padx=4, pady=5).pack(side="left", padx=1)

    rows_frame = tk.Frame(card, bg=WHITE)
    rows_frame.pack(fill="x")
    state["items_frame"] = rows_frame

    for _ in range(3):
        _add_line_item()

    btn_row = tk.Frame(card, bg=WHITE)
    btn_row.pack(fill="x", pady=(6, 2))
    tk.Button(btn_row, text="+ Add Line Item",
              font=FONT_BOLD, bg=ACCENT, fg="white",
              relief="flat", padx=10, pady=5,
              cursor="hand2", command=_add_line_item).pack(side="left", padx=2)


def _add_line_item():
    rows_frame = state["items_frame"]
    idx = len(state["items"])
    bg = ALTROW if idx % 2 == 1 else WHITE
    row = tk.Frame(rows_frame, bg=bg)
    row.pack(fill="x", pady=1)

    desc_e = tk.Entry(row, font=FONT, relief="solid", bd=1, width=39, bg=bg)
    desc_e.grid(row=0, column=0, padx=1, pady=3)

    qty_e = tk.Entry(row, font=FONT, relief="solid", bd=1, width=8,
                     justify="center", bg=bg)
    qty_e.insert(0, "1")
    qty_e.grid(row=0, column=1, padx=1)

    price_e = tk.Entry(row, font=FONT, relief="solid", bd=1, width=13,
                       justify="right", bg=bg)
    price_e.insert(0, "0.00")
    price_e.grid(row=0, column=2, padx=1)

    disc_e = tk.Entry(row, font=FONT, relief="solid", bd=1, width=8,
                      justify="center", bg=bg)
    disc_e.insert(0, "0")
    disc_e.grid(row=0, column=3, padx=1)

    amt_lbl = tk.Label(row, text="0.00", font=FONT, relief="solid", bd=1,
                       width=13, anchor="e", bg=ALTROW, padx=4)
    amt_lbl.grid(row=0, column=4, padx=1, sticky="nsew")

    item = {"row": row, "desc": desc_e, "qty": qty_e,
            "price": price_e, "disc": disc_e, "amount": amt_lbl}

    tk.Button(row, text="✕", font=FONT, bg=RED, fg="white",
              relief="flat", width=3, cursor="hand2",
              command=lambda i=item: _remove_line_item(i)).grid(
        row=0, column=5, padx=2)

    for entry in (qty_e, price_e, disc_e):
        entry.bind("<KeyRelease>", lambda _e: _recalculate())

    state["items"].append(item)
    _recalculate()


def _remove_line_item(item):
    if len(state["items"]) <= 1:
        return
    item["row"].destroy()
    state["items"].remove(item)
    _recalculate()


def _totals(parent):
    outer = tk.Frame(parent, bg=BG)
    outer.pack(fill="x", padx=18, pady=4)

    bank = _card(outer, "Payment / Bank Info")
    bank.pack(side="left", fill="both", expand=True, padx=(0, 6))

    bank_fields = [
        ("bank_name",      "Bank / Account Name:"),
        ("account_no",     "Account Number:"),
        ("routing_swift",  "Routing / SWIFT:"),
        ("iban",           "IBAN:"),
    ]
    for i, (key, label) in enumerate(bank_fields):
        tk.Label(bank, text=label, font=FONT, bg=WHITE).grid(
            row=i, column=0, sticky="w", padx=(4, 2), pady=4)
        e = tk.Entry(bank, font=FONT, relief="solid", bd=1, width=32)
        e.grid(row=i, column=1, sticky="ew", padx=(0, 10), pady=4)
        state["bank"][key] = e

    totals = _card(outer, "Totals")
    totals.pack(side="right", padx=(6, 0))

    def _total_row(label, row, bold=False, color="#333333"):
        font = FONT_BOLD if bold else FONT
        tk.Label(totals, text=label, font=font, bg=WHITE,
                 anchor="e", width=20).grid(row=row, column=0, sticky="e", padx=4, pady=4)
        val = tk.Label(totals, text="0.00", font=font, bg=ALTROW,
                       anchor="e", width=14, fg=color,
                       relief="solid", bd=1, padx=6)
        val.grid(row=row, column=1, sticky="e", padx=4, pady=4)
        return val

    state["totals"]["subtotal"] = _total_row("Subtotal:", 0)

    tk.Label(totals, text="Global Discount %:", font=FONT, bg=WHITE).grid(
        row=1, column=0, sticky="e", padx=4, pady=3)
    disc_e = tk.Entry(totals, font=FONT, width=8, justify="center", relief="solid", bd=1)
    disc_e.insert(0, "0")
    disc_e.grid(row=1, column=1, sticky="e", padx=4, pady=3)
    disc_e.bind("<KeyRelease>", lambda _e: _recalculate())
    state["totals"]["disc_pct"] = disc_e

    state["totals"]["disc_amt"] = _total_row("Discount Amount:", 2)

    tk.Label(totals, text="Tax %:", font=FONT, bg=WHITE).grid(
        row=3, column=0, sticky="e", padx=4, pady=3)
    tax_e = tk.Entry(totals, font=FONT, width=8, justify="center", relief="solid", bd=1)
    tax_e.insert(0, "0")
    tax_e.grid(row=3, column=1, sticky="e", padx=4, pady=3)
    tax_e.bind("<KeyRelease>", lambda _e: _recalculate())
    state["totals"]["tax_pct"] = tax_e

    state["totals"]["tax_amt"] = _total_row("Tax Amount:", 4)

    ttk.Separator(totals, orient="horizontal").grid(
        row=5, column=0, columnspan=2, sticky="ew", pady=5)

    state["totals"]["total"] = _total_row("TOTAL:", 6, bold=True, color="#1a7a4a")


def _notes_terms(parent):
    card = _card(parent, "Notes & Terms")
    card.pack(fill="x", padx=18, pady=4)

    inner = tk.Frame(card, bg=WHITE)
    inner.pack(fill="x")
    inner.columnconfigure((0, 1), weight=1)

    for col, title in enumerate(["Notes:", "Terms & Conditions:"]):
        tk.Label(inner, text=title, font=FONT_BOLD, bg=WHITE,
                 fg=DARK).grid(row=0, column=col, sticky="w", padx=4)

    notes_t = tk.Text(inner, height=4, width=44, font=FONT,
                      relief="solid", bd=1, wrap="word")
    notes_t.grid(row=1, column=0, sticky="ew", padx=4, pady=4)
    state["notes"] = notes_t

    default_terms = (
        "Payment is due within the agreed timeframe.\n"
        "Late payments may incur a 1.5% monthly fee.\n"
        "All prices are in the stated currency."
    )
    terms_t = tk.Text(inner, height=4, width=44, font=FONT,
                      relief="solid", bd=1, wrap="word")
    terms_t.insert("1.0", default_terms)
    terms_t.grid(row=1, column=1, sticky="ew", padx=4, pady=4)
    state["terms"] = terms_t


def _action_bar(parent):
    bar = tk.Frame(parent, bg=DARK)
    bar.pack(fill="x", pady=(10, 0))

    tk.Button(bar, text="Open in Browser", font=FONT_BOLD,
              bg=GREEN, fg="white", relief="flat",
              padx=14, pady=8, cursor="hand2",
              command=lambda: open_in_browser(_collect_data())).pack(
        side="left", padx=10, pady=10)

    tk.Button(bar, text="Export PDF", font=FONT_BOLD,
              bg=ORANGE, fg="white", relief="flat",
              padx=14, pady=8, cursor="hand2",
              command=lambda: export_pdf(_collect_data())).pack(
        side="left", padx=10, pady=10)


def _safe_float(s, default=0.0):
    try:
        return float(str(s).strip().replace(",", ""))
    except (ValueError, AttributeError):
        return default


def _currency_symbol():
    cb = state["details"].get("currency")
    if not cb:
        return "$"
    text = cb.get()
    code = code_from_label(text)
    return symbol_for(code) if code else "$"


def _currency_code():
    cb = state["details"].get("currency")
    if not cb:
        return "USD"
    return code_from_label(cb.get()) or "USD"


def _recalculate():
    subtotal = 0.0
    for item in state["items"]:
        qty   = _safe_float(item["qty"].get(), 0)
        price = _safe_float(item["price"].get(), 0)
        disc  = _safe_float(item["disc"].get(), 0)
        amount = qty * price * (1 - disc / 100.0)
        item["amount"].config(text=f"{amount:,.2f}")
        subtotal += amount

    if "disc_pct" not in state["totals"]:
        return

    disc_pct  = _safe_float(state["totals"]["disc_pct"].get(), 0)
    disc_amt  = subtotal * disc_pct / 100.0
    after     = subtotal - disc_amt
    tax_pct   = _safe_float(state["totals"]["tax_pct"].get(), 0)
    tax_amt   = after * tax_pct / 100.0
    total     = after + tax_amt

    sym = _currency_symbol()
    state["totals"]["subtotal"].config(text=f"{sym} {subtotal:,.2f}")
    state["totals"]["disc_amt"].config(text=f"{sym} {disc_amt:,.2f}")
    state["totals"]["tax_amt"].config(text=f"{sym} {tax_amt:,.2f}")
    state["totals"]["total"].config(text=f"{sym} {total:,.2f}")


def _collect_data():
    def vals(d):
        return {k: v.get().strip() for k, v in d.items()}

    items = []
    for it in state["items"]:
        qty   = _safe_float(it["qty"].get(), 0)
        price = _safe_float(it["price"].get(), 0)
        disc  = _safe_float(it["disc"].get(), 0)
        items.append({
            "description": it["desc"].get().strip(),
            "qty":         qty,
            "price":       price,
            "discount":    disc,
            "amount":      qty * price * (1 - disc / 100.0),
        })

    subtotal = sum(i["amount"] for i in items)
    disc_pct = _safe_float(state["totals"]["disc_pct"].get(), 0)
    disc_amt = subtotal * disc_pct / 100.0
    after    = subtotal - disc_amt
    tax_pct  = _safe_float(state["totals"]["tax_pct"].get(), 0)
    tax_amt  = after * tax_pct / 100.0

    return {
        "from":            vals(state["from"]),
        "to":              vals(state["to"]),
        "details":         vals(state["details"]),
        "items":           items,
        "bank":            vals(state["bank"]),
        "notes":           state["notes"].get("1.0", "end").strip(),
        "terms":           state["terms"].get("1.0", "end").strip(),
        "subtotal":        subtotal,
        "discount_pct":    disc_pct,
        "discount_amount": disc_amt,
        "tax_pct":         tax_pct,
        "tax_amount":      tax_amt,
        "total":           after + tax_amt,
        "currency_symbol": _currency_symbol(),
        "currency_code":   _currency_code(),
        "signer":          state.get("signer"),
    }
