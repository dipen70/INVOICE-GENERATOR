# Invoice Generator

A desktop invoice generator built with **tkinter** for the GUI and **reportlab** for PDF export. Fill in company / client / line-item details, see totals computed live, and either preview the result in your browser or export it as a styled PDF.

---

## Features

- Live total calculation (subtotal → global discount → tax → total)
- Per-line discount %
- Add and remove line items dynamically
- **Currency selector** with the full ISO 4217 list (~170 currencies, fetched from openexchangerates.org with bundled fallback)
- **Calendar date picker** for issue & due dates (`tkcalendar`)
- **Sign in with Google** — captures the user's name, email, and position; the signer is stamped on every invoice
- Browser preview via a temp HTML file
- One-click PDF export to a path you pick

---

## Project structure

```
invoice_app/
├── ui.py           # entry point — builds the scrollable shell
├── sections.py     # form sections, shared state, totals math, action wiring
├── exporters.py    # browser HTML preview + reportlab PDF export
├── constants.py    # colours, fonts, _card / _field_row helpers
├── build_docs.py   # generates INVOICE_APP_GUIDE.pdf
└── README.md
```

---

## Requirements

- Python 3.9+
- `tkinter` (ships with Python on Windows / macOS; on Linux: `sudo apt install python3-tk`)
- `reportlab` (PDF export)
- `tkcalendar` (date picker)
- `requests` (currency API)
- `google-auth`, `google-auth-oauthlib` (Sign in with Google)

```bash
pip install reportlab tkcalendar requests google-auth google-auth-oauthlib
```

---

## Google OAuth setup (one-time)

Sign-in needs your own OAuth client. Free, ~5 min:

1. Go to https://console.cloud.google.com/ and create a new project.
2. **APIs & Services → OAuth consent screen** — set User Type to *External*, fill in app name + support email, add yourself under **Test users**.
3. **APIs & Services → Credentials → + CREATE CREDENTIALS → OAuth client ID** — application type *Desktop app*. Download the JSON.
4. Rename the downloaded file to **`client_secret.json`** and drop it next to `main.py`.

The first time you launch, a browser window opens for sign-in. Tokens are cached in `~/.invoice_app/token.json`; your position is remembered per Google account in `~/.invoice_app/profile.json`.

> Both files are local-only and `.gitignore`d.

---

## Run

```bash
python main.py
```

To regenerate the code walkthrough PDF:

```bash
python build_docs.py
```

---

## Architecture at a glance

```
[Tk widgets] ──user types──▶ [state dict] ──<KeyRelease>──▶ _recalculate()
                                  │                              │
                                  │                              ▼
                                  │                      [Tk Labels updated]
                                  ▼
                           _collect_data() ──▶ {plain dict}
                                                    │
                              ┌─────────────────────┴─────────────────────┐
                              ▼                                           ▼
                       render_html(data)                         _build_pdf(data, path)
                              │                                           │
                       tempfile + webbrowser                       filedialog + reportlab
```

`state` (a module-level dict in `sections.py`) is the single source of truth for the form. Section builders write widget references into it; handlers read from it.

---

## constants.py

Centralised palette, fonts, and two small UI factory helpers.

### Colour palette

| Name      | Hex       | Used for                       |
|-----------|-----------|--------------------------------|
| `DARK`    | `#2c3e50` | Header bar, section accents    |
| `ACCENT`  | `#2980b9` | Primary action (Add Item)      |
| `GREEN`   | `#27ae60` | "Open in Browser" button       |
| `ORANGE`  | `#e67e22` | "Export PDF" button            |
| `RED`     | `#e74c3c` | Destructive (delete row)       |
| `BG`      | `#f0f4f8` | Page background                |
| `WHITE`   | `#ffffff` | Card background                |
| `ALTROW`  | `#f4f6f7` | Zebra row shade, output cells  |
| `MIDGRAY` | `#95a5a6` | Secondary text                 |

### Fonts

Tuples of the form `(family, size[, "bold"])` that Tk's `font=` argument consumes. `FONT`, `FONT_BOLD`, `FONT_LARGE`, `FONT_TITLE`, `FONT_SMALL`.

### `_card(parent, title, pack_kw=None) -> tk.LabelFrame`

Creates a `tk.LabelFrame` styled as a white card with a dark title. Returns the frame so callers can `.pack()` it and add children. (`pack_kw` is kept for legacy call-site compatibility but unused inside.)

### `_field_row(parent, label, row, col=0, default="", width=26) -> tk.Entry`

Places a `Label` at `(row, col)` and an `Entry` at `(row, col+1)` using `grid`. Pre-fills `default` if given, returns the Entry so callers can store the reference in `state`.

### `_apply_styles()`

Configures the global `ttk` Style — picks the `clam` theme and overrides backgrounds for `TFrame`, `TLabel`, `TLabelframe`, `TEntry`, `TCombobox`, `TScrollbar`. Called once at startup from `build_ui`.

---

## ui.py

A single function and a `__main__` guard.

### `build_ui(root)`

Sizes the window, applies styles, builds a scrollable canvas, then calls every section builder in order: `_header → _from_to → _invoice_details → _line_items → _totals → _notes_terms → _action_bar`.

### Scrollable canvas pattern

```
container        (Frame)
└── canvas       (Canvas — scroll surface)
    └── scroll_frame   (Frame — embedded via canvas.create_window)
        └── all sections packed here
```

- `scroll_frame` is embedded inside `canvas` with `canvas.create_window((0,0), window=scroll_frame, anchor="nw")`.
- `<Configure>` on `scroll_frame` updates `scrollregion = canvas.bbox("all")` so the scrollbar always knows the content height.
- `<Configure>` on `canvas` resizes the embedded frame to the canvas's width (so children fill horizontally).
- `<MouseWheel>` is bound globally and translated to `yview_scroll`. Windows reports `event.delta` in multiples of 120 — dividing by 120 normalises it to a "click count".

### Entry point

```python
if __name__ == "__main__":
    root = tk.Tk()
    build_ui(root)
    root.mainloop()
```

---

## sections.py

### Module-level `state`

```python
state = {
    "from": {},          # dict[str, Entry]      — your-company fields
    "to": {},            # dict[str, Entry]      — bill-to fields
    "details": {},       # dict[str, Entry|Combobox]
    "items": [],         # list[dict]            — one per line-item row
    "items_frame": None, # parent Frame for line-item rows
    "totals": {},        # dict[str, Entry|Label] — subtotal label etc.
    "bank": {},          # dict[str, Entry]
    "notes": None,       # Text widget
    "terms": None,       # Text widget
}
```

A single dict avoids threading widget references through every helper.

### Section builders

Each takes the scrollable parent frame, packs its UI, and stores its widgets in `state`.

| Function              | What it builds                                                  |
|-----------------------|------------------------------------------------------------------|
| `_header(parent)`     | Dark bar at the top with the app title.                          |
| `_from_to(parent)`    | Two side-by-side cards for **From** and **Bill To**.             |
| `_invoice_details`    | Invoice #, dates, PO, currency / terms / payment-method comboboxes. |
| `_line_items(parent)` | Header row + dynamic rows + **+ Add Line Item** button.          |
| `_totals(parent)`     | Bank info card on the left; subtotal/discount/tax/total card on the right. |
| `_notes_terms`        | Two `Text` widgets — Notes and Terms (terms pre-filled).         |
| `_action_bar(parent)` | The two action buttons.                                          |

Currency / discount % / tax % each call `_recalculate()` on change so the totals stay live.

### `_add_line_item()`

Builds a row inside `state["items_frame"]`:

- Description Entry + Qty Entry + Unit Price Entry + Disc % Entry + Amount Label + Delete Button.
- Stores them as a dict in `state["items"]`.
- Binds `<KeyRelease>` on qty / price / disc to call `_recalculate`.
- Delete button uses `lambda i=item: _remove_line_item(i)` — see *lambda default-arg capture* below.
- Calls `_recalculate()` once so the new row's amount label shows `0.00`.

### `_remove_line_item(item)`

Refuses if there's only one row left (the form is never empty). Destroys the row's frame, removes it from `state["items"]`, recalculates.

### `_recalculate()`

The pure-UI side-effect engine. Reads every line and computes:

```
amount       = qty * price * (1 - line_disc / 100)
subtotal     = sum(amounts)
disc_amount  = subtotal * global_disc_pct / 100
after_disc   = subtotal - disc_amount
tax_amount   = after_disc * tax_pct / 100
total        = after_disc + tax_amount
```

Then updates each line's amount Label and the four total Labels with the active currency symbol.

### `_collect_data()`

Snapshots the form into a plain dict suitable for `render_html` and `_build_pdf`. Same math as `_recalculate()` but returns values instead of mutating widgets.

Output keys: `from`, `to`, `details`, `items`, `bank`, `notes`, `terms`, `subtotal`, `discount_pct`, `discount_amount`, `tax_pct`, `tax_amount`, `total`, `currency_symbol`.

### `_safe_float(s, default=0.0)`

Forgiving string→float converter. Strips whitespace, removes thousands separators (`,`), returns `default` on failure. Lets the user type `1,250.00` or leave a field blank without crashing the math.

### `_currency_symbol()`

Parses `"USD ($)"` → `"$"` by extracting whatever is between the parens. Falls back to `"$"` if no parens.

---

## exporters.py

Two public entry points plus their internals.

### `open_in_browser(data)`

1. `render_html(data)` — produce an HTML string.
2. Write to a tempfile created with `tempfile.mkstemp(suffix=".html", prefix="invoice_preview_")`.
3. `webbrowser.open("file:///" + path)` — backslashes converted to forward slashes for the URL.

`mkstemp` returns `(fd, path)`. The fd is closed immediately so we can re-open the path in text mode with explicit `utf-8` encoding.

### `export_pdf(data)`

1. Try to `import reportlab`. If missing, show `messagebox.showerror` with install instructions and return.
2. Sanitise the invoice number for use as a filename (anything non-alphanumeric becomes `_`).
3. `filedialog.asksaveasfilename` — if the user cancels, return silently.
4. Call `_build_pdf(data, path)`. On exception, show the error in a `messagebox`.
5. On success, show a confirmation dialog with the saved path.

### `_build_pdf(data, path)`

Uses **reportlab Platypus** — a high-level document model. Every "thing" on the page is a *flowable* (Paragraph, Spacer, Table, Image…) appended to a `story` list. `doc.build(story)` runs them through page layout, handling pagination automatically.

Flowables used:

- **`SimpleDocTemplate`** — the document. A4, 15 mm margins.
- **`Paragraph(text, style)`** — text block. Supports a small subset of HTML (`<b>`, `<i>`, `<br/>`, `<font>`).
- **`Spacer(width, height)`** — vertical gap.
- **`Table(rows, colWidths=…, hAlign=…)`** — grid of flowables / strings.
- **`TableStyle([commands])`** — formats cells. Each command is a tuple `(op, (col0,row0), (col1,row1), …args)`.

`TableStyle` ops used here: `BACKGROUND`, `TEXTCOLOR`, `FONT`, `ALIGN`, `VALIGN`, `BOX`, `INNERGRID`, `LINEABOVE`, `LEFTPADDING` / `RIGHTPADDING` / `TOPPADDING` / `BOTTOMPADDING`, and `ROWBACKGROUNDS` (zebra stripes).

Document layout (top to bottom):

1. Title row — "INVOICE" left, meta table (invoice #, dates, PO, terms, method) right.
2. From / Bill To — two-column Table with paragraphs containing newline-separated address lines.
3. Line items Table — dark header row, zebra-striped data rows, `repeatRows=1` so the header repeats on overflow.
4. Totals — right-aligned Table; discount and tax rows are skipped if zero. The last row is bold green with a top rule.
5. Bank info, notes, terms — only if non-empty.

`html.escape` is applied wherever user text reaches a Paragraph because Paragraph parses inline HTML.

### `render_html(data)`

Generates a self-contained HTML document with inline CSS. Same input shape as `_build_pdf`. Empty rows / sections are skipped the same way. The CSS includes a `@media print` block so Ctrl+P in the browser produces a clean print version.

CSS notes:
- `box-sizing: border-box` for predictable widths.
- Flexbox for the top header (title left, meta right) and the parties row (From / Bill To).
- `font-variant-numeric: tabular-nums` on numeric columns so digits align vertically.

---

## tkinter cheat sheet

- **`pack` vs `grid`** — they manage *children* of a parent. The same parent can use only one of them. Frames are laid out with `pack`; form fields inside cards use `grid` because we want labelled rows aligned in columns.
- **Event binding** — `widget.bind("<Event>", callback)`. The callback receives an `event` object (we ignore it via `lambda _e: ...`).
- **Events used here** — `<Configure>` (resize), `<MouseWheel>` (scroll), `<KeyRelease>` (after a keystroke commits), `<<ComboboxSelected>>` (Combobox value change — virtual events use double brackets).
- **Lambda default-arg capture** — `command=lambda i=item: f(i)` snapshots `item` at definition time. Without `i=item`, Python would look up `item` at click time and find whatever it's bound to *now* (often the last loop iteration). Critical inside loops.
- **`messagebox` and `filedialog`** — top-level modal dialogs.

---

## reportlab cheat sheet

- **Platypus** — *Page Layout And Typography Using Scripts*. You build a flat list of flowables; the engine handles pagination.
- **Coords in `TableStyle`** — `(col, row)`, **not** `(row, col)`. `(0, 0)` is top-left, `(-1, -1)` is bottom-right.
- **Units** — `from reportlab.lib.units import mm`, then `15 * mm`. Internally everything is in points (1 pt = 1/72 inch).
- **Colours** — `colors.HexColor("#2c3e50")` accepts CSS-style hex.
- **`hAlign="RIGHT"`** on a Table aligns the entire table within its frame (used for the totals box).

---

## Calculation reference

| Quantity        | Formula                                       |
|-----------------|-----------------------------------------------|
| Line amount     | `qty * unit_price * (1 - line_disc / 100)`    |
| Subtotal        | sum of all line amounts                       |
| Discount amount | `subtotal * global_disc_pct / 100`            |
| After discount  | `subtotal - discount_amount`                  |
| Tax amount      | `after_discount * tax_pct / 100`              |
| **Total**       | `after_discount + tax_amount`                 |

The order matters: tax applies *after* the global discount.
