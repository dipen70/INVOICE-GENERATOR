"""Generate INVOICE_APP_GUIDE.pdf — a complete walkthrough of the codebase.

Run:  python build_docs.py
"""
import html as _html
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable, KeepTogether, PageBreak, Paragraph, Preformatted,
    SimpleDocTemplate, Spacer, Table, TableStyle,
)


OUTPUT = os.path.join(os.path.dirname(__file__), "INVOICE_APP_GUIDE.pdf")

DARK    = colors.HexColor("#2c3e50")
ACCENT  = colors.HexColor("#2980b9")
GREEN   = colors.HexColor("#1a7a4a")
MID     = colors.HexColor("#7f8c8d")
RULE    = colors.HexColor("#bdc3c7")
CODE_BG = colors.HexColor("#f4f6f7")
TBL_HDR = colors.HexColor("#2c3e50")
TBL_ALT = colors.HexColor("#f8fafb")

base = getSampleStyleSheet()

H1 = ParagraphStyle("H1", parent=base["Heading1"], textColor=DARK,
                    fontSize=24, leading=28, spaceAfter=4)
SUB = ParagraphStyle("Sub", parent=base["Normal"], textColor=MID,
                     fontSize=11, leading=14, spaceAfter=14)
H2 = ParagraphStyle("H2", parent=base["Heading2"], textColor=DARK,
                    fontSize=16, leading=20, spaceAfter=2, spaceBefore=14)
H3 = ParagraphStyle("H3", parent=base["Heading3"], textColor=DARK,
                    fontSize=12, leading=15, spaceAfter=4, spaceBefore=10)
H4 = ParagraphStyle("H4", parent=base["Heading4"], textColor=ACCENT,
                    fontSize=10, leading=13, spaceAfter=2, spaceBefore=8,
                    fontName="Helvetica-Bold")
BODY = ParagraphStyle("Body", parent=base["Normal"],
                      fontSize=10, leading=14, spaceAfter=6)
BULLET = ParagraphStyle("Bullet", parent=BODY,
                        leftIndent=14, bulletIndent=2, spaceAfter=3)
CODE = ParagraphStyle("Code", parent=base["Code"],
                      fontName="Courier", fontSize=8.5, leading=11,
                      textColor=colors.HexColor("#2c3e50"))


def _inline(text):
    """Replace <c>code</c> with monospaced inline spans for Paragraph."""
    return (text
            .replace("<c>", '<font face="Courier" color="#444444">')
            .replace("</c>", '</font>'))


def h1(t):  return Paragraph(_inline(t), H1)
def sub(t): return Paragraph(_inline(t), SUB)


def h2(t):
    return KeepTogether([
        Paragraph(_inline(t), H2),
        HRFlowable(width="100%", thickness=0.8, color=DARK,
                   spaceBefore=0, spaceAfter=6),
    ])


def h3(t): return Paragraph(_inline(t), H3)
def h4(t): return Paragraph(_inline(t), H4)
def p(t):  return Paragraph(_inline(t), BODY)


def bullets(items):
    return [Paragraph("• " + _inline(it), BULLET) for it in items]


def code(text):
    pre = Preformatted(_html.escape(text.rstrip("\n")), CODE)
    tbl = Table([[pre]], colWidths=["100%"])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), CODE_BG),
        ("BOX",          (0, 0), (-1, -1), 0.4, RULE),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
    ]))
    return tbl


def table(rows, col_widths=None, header=True):
    style = [
        ("FONT",         (0, 0),  (-1, -1), "Helvetica", 9),
        ("VALIGN",       (0, 0),  (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0),  (-1, -1), 6),
        ("RIGHTPADDING", (0, 0),  (-1, -1), 6),
        ("TOPPADDING",   (0, 0),  (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0),  (-1, -1), 4),
        ("BOX",          (0, 0),  (-1, -1), 0.4, RULE),
        ("INNERGRID",    (0, 0),  (-1, -1), 0.25, RULE),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), TBL_HDR),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONT",       (0, 0), (-1, 0), "Helvetica-Bold", 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, TBL_ALT]),
        ]
    wrapped = [[Paragraph(_inline(str(c)), BODY) for c in row] for row in rows]
    tbl = Table(wrapped, colWidths=col_widths, repeatRows=1 if header else 0)
    tbl.setStyle(TableStyle(style))
    return tbl


def gap(mm_size): return Spacer(1, mm_size * mm)


# ─────────────────────────────────────────────────────────────────────────
# Content
# ─────────────────────────────────────────────────────────────────────────
story = []

story += [
    h1("Invoice Generator — Code Walkthrough"),
    sub("A complete tour of every module, function, and library feature used "
        "in this project. Built with tkinter (GUI) and reportlab (PDF export)."),
]

# ── 1. Overview
story += [
    h2("1. Overview"),
    p("The app is a desktop form for composing an invoice. The user fills in "
      "their company info, the client info, line items, taxes, and notes; "
      "the totals update live. Two action buttons let them either preview "
      "the result in a browser or export it as a PDF."),
    h3("Features"),
]
story += bullets([
    "Live total calculation: subtotal &rarr; global discount &rarr; tax &rarr; total.",
    "Per-line discount %.",
    "Add and remove line items dynamically.",
    "Currency selector (USD, EUR, GBP, INR, JPY, CAD, AUD).",
    "Browser preview via a temp HTML file.",
    "One-click PDF export to a path you pick.",
])

story += [
    h3("Project structure"),
    code(
"""invoice_app/
|-- ui.py           # entry point -- builds the scrollable shell
|-- sections.py     # form sections, shared state, totals math, action wiring
|-- exporters.py    # browser HTML preview + reportlab PDF export
|-- constants.py    # colours, fonts, _card / _field_row helpers
|-- build_docs.py   # generates this PDF
`-- README.md
"""),
    h3("How to run"),
    code("python ui.py\npython build_docs.py     # rebuild this guide"),
]

# ── 2. Architecture
story += [
    h2("2. Architecture at a glance"),
    p("A single module-level dict named <c>state</c> in <c>sections.py</c> "
      "is the bridge between the form widgets and the export handlers. "
      "Each section builder writes its widget references into <c>state</c>; "
      "the action handlers read from it."),
    code(
"""[Tk widgets] --user types--> [state dict] --<KeyRelease>--> _recalculate()
                                  |                              |
                                  |                              v
                                  |                     [Tk Labels updated]
                                  v
                          _collect_data() --> {plain dict}
                                                  |
                          +-----------------------+----------------------+
                          v                                              v
                   render_html(data)                          _build_pdf(data, path)
                          |                                              |
                  tempfile + webbrowser                         filedialog + reportlab
"""),
]

# ── 3. constants.py
story += [
    h2("3. constants.py"),
    p("Centralised palette, fonts, and two small UI factory helpers."),

    h3("Colour palette"),
    table(
        [["Name", "Hex", "Used for"],
         ["DARK",    "#2c3e50", "Header bar, section accents"],
         ["ACCENT",  "#2980b9", "Primary action (Add Item)"],
         ["GREEN",   "#27ae60", '"Open in Browser" button'],
         ["ORANGE",  "#e67e22", '"Export PDF" button'],
         ["RED",     "#e74c3c", "Destructive (delete row)"],
         ["BG",      "#f0f4f8", "Page background"],
         ["WHITE",   "#ffffff", "Card background"],
         ["ALTROW",  "#f4f6f7", "Zebra row shade, output cells"],
         ["MIDGRAY", "#95a5a6", "Secondary text"]],
        col_widths=[26 * mm, 26 * mm, None]),

    h3("Fonts"),
    p("Tuples of the form <c>(family, size[, &quot;bold&quot;])</c> that "
      "Tk's <c>font=</c> argument consumes: <c>FONT</c>, <c>FONT_BOLD</c>, "
      "<c>FONT_LARGE</c>, <c>FONT_TITLE</c>, <c>FONT_SMALL</c>."),

    h4("_card(parent, title, pack_kw=None) -&gt; tk.LabelFrame"),
    p("Creates a <c>tk.LabelFrame</c> styled as a white card with a dark "
      "title. Returns the frame so callers can <c>.pack()</c> it and add "
      "children. <c>pack_kw</c> is kept for legacy call-site compatibility "
      "but unused inside."),

    h4("_field_row(parent, label, row, col=0, default=&quot;&quot;, width=26) -&gt; tk.Entry"),
    p("Places a <c>Label</c> at <c>(row, col)</c> and an <c>Entry</c> at "
      "<c>(row, col+1)</c> using <c>grid</c>. Pre-fills <c>default</c> if "
      "given, returns the Entry so callers can store the reference in "
      "<c>state</c>."),

    h4("_apply_styles()"),
    p("Configures the global <c>ttk</c> Style. Picks the <c>clam</c> theme "
      "and overrides backgrounds for <c>TFrame</c>, <c>TLabel</c>, "
      "<c>TLabelframe</c>, <c>TEntry</c>, <c>TCombobox</c>, "
      "<c>TScrollbar</c>. Called once at startup from <c>build_ui</c>."),
]

story.append(PageBreak())

# ── 4. ui.py
story += [
    h2("4. ui.py"),
    p("A single function plus a <c>__main__</c> guard."),

    h4("build_ui(root)"),
    p("Sizes the window, applies styles, builds a scrollable canvas, then "
      "calls every section builder in order: "
      "<c>_header &rarr; _from_to &rarr; _invoice_details &rarr; _line_items "
      "&rarr; _totals &rarr; _notes_terms &rarr; _action_bar</c>."),

    h3("Scrollable canvas pattern"),
    p("A classic tkinter idiom for adding scrolling to arbitrarily tall "
      "content."),
    code(
"""container        (Frame)
+-- canvas       (Canvas -- scroll surface)
    +-- scroll_frame   (Frame -- embedded via canvas.create_window)
        +-- all sections packed here
"""),
]
story += bullets([
    "<c>scroll_frame</c> is embedded inside <c>canvas</c> via "
    "<c>canvas.create_window((0,0), window=scroll_frame, anchor=&quot;nw&quot;)</c>.",
    "<c>&lt;Configure&gt;</c> on <c>scroll_frame</c> updates "
    "<c>scrollregion = canvas.bbox(&quot;all&quot;)</c> so the scrollbar "
    "always knows the content height.",
    "<c>&lt;Configure&gt;</c> on <c>canvas</c> resizes the embedded frame "
    "to match the canvas width (so children fill horizontally).",
    "<c>&lt;MouseWheel&gt;</c> is bound globally and translated to "
    "<c>yview_scroll</c>. Windows reports <c>event.delta</c> in multiples "
    "of 120; dividing by 120 normalises it to a click count.",
])

story += [
    h3("Entry point"),
    code(
"""if __name__ == "__main__":
    root = tk.Tk()
    build_ui(root)
    root.mainloop()
"""),
]

story.append(PageBreak())

# ── 5. sections.py
story += [
    h2("5. sections.py"),

    h3("Module-level state"),
    p("A single dict avoids threading widget references through every helper."),
    code(
"""state = {
    "from": {},          # dict[str, Entry]      -- your-company fields
    "to": {},            # dict[str, Entry]      -- bill-to fields
    "details": {},       # dict[str, Entry|Combobox]
    "items": [],         # list[dict]            -- one per line-item row
    "items_frame": None, # parent Frame for line-item rows
    "totals": {},        # dict[str, Entry|Label] -- subtotal label etc.
    "bank": {},          # dict[str, Entry]
    "notes": None,       # Text widget
    "terms": None,       # Text widget
}
"""),

    h3("Section builders"),
    p("Each takes the scrollable parent frame, packs its UI, and stores its "
      "widgets in <c>state</c>."),
    table(
        [["Function", "What it builds"],
         ["_header(parent)",     "Dark bar at the top with the app title."],
         ["_from_to(parent)",    "Two side-by-side cards (From + Bill To)."],
         ["_invoice_details",    "Invoice #, dates, PO, currency / terms / "
                                 "payment-method comboboxes."],
         ["_line_items(parent)", "Header row + dynamic rows + the "
                                 "+ Add Line Item button."],
         ["_totals(parent)",     "Bank info card on the left; "
                                 "subtotal/discount/tax/total card on the right."],
         ["_notes_terms",        "Two Text widgets (terms pre-filled)."],
         ["_action_bar(parent)", "The two action buttons."]],
        col_widths=[42 * mm, None]),

    p("Currency / discount % / tax % each call <c>_recalculate()</c> on "
      "change so the totals stay live."),

    h4("_add_line_item()"),
]
story += bullets([
    "Builds Description Entry + Qty Entry + Unit Price Entry + Disc % Entry "
    "+ Amount Label + Delete Button inside <c>state[&quot;items_frame&quot;]</c>.",
    "Stores them as a dict appended to <c>state[&quot;items&quot;]</c>.",
    "Binds <c>&lt;KeyRelease&gt;</c> on qty / price / disc to "
    "<c>_recalculate</c>.",
    "Delete button uses <c>lambda i=item: _remove_line_item(i)</c> -- the "
    "default-arg capture trick. Without <c>i=item</c>, Python would look up "
    "<c>item</c> at click time and find whatever it's bound to <i>now</i> "
    "(usually the last loop iteration).",
    "Calls <c>_recalculate()</c> once at the end so the new row's amount "
    "label shows <c>0.00</c>.",
])

story += [
    h4("_remove_line_item(item)"),
    p("Refuses if there's only one row left (the form is never empty). "
      "Destroys the row's frame, removes it from <c>state[&quot;items&quot;]</c>, "
      "recalculates."),

    h4("_recalculate()"),
    p("Reads every line, computes amounts and totals, updates the matching "
      "labels."),
    code(
"""amount       = qty * price * (1 - line_disc / 100)
subtotal     = sum(amounts)
disc_amount  = subtotal * global_disc_pct / 100
after_disc   = subtotal - disc_amount
tax_amount   = after_disc * tax_pct / 100
total        = after_disc + tax_amount
"""),
    p("Each line's amount Label and the four total Labels are updated with "
      "the active currency symbol."),

    h4("_collect_data()"),
    p("Snapshots the form into a plain dict suitable for <c>render_html</c> "
      "and <c>_build_pdf</c>. Same math as <c>_recalculate()</c> but returns "
      "values instead of mutating widgets. Output keys: <c>from</c>, "
      "<c>to</c>, <c>details</c>, <c>items</c>, <c>bank</c>, <c>notes</c>, "
      "<c>terms</c>, <c>subtotal</c>, <c>discount_pct</c>, "
      "<c>discount_amount</c>, <c>tax_pct</c>, <c>tax_amount</c>, "
      "<c>total</c>, <c>currency_symbol</c>."),

    h4("_safe_float(s, default=0.0)"),
    p("Forgiving string &rarr; float converter. Strips whitespace, removes "
      "thousands separators (<c>,</c>), returns <c>default</c> on failure. "
      "Lets the user type <c>1,250.00</c> or leave a field blank without "
      "crashing the math."),

    h4("_currency_symbol()"),
    p("Parses <c>&quot;USD ($)&quot;</c> &rarr; <c>&quot;$&quot;</c> by "
      "extracting whatever is between the parens. Falls back to "
      "<c>&quot;$&quot;</c> if no parens."),
]

story.append(PageBreak())

# ── 6. exporters.py
story += [
    h2("6. exporters.py"),
    p("Two public entry points plus their internals."),

    h4("open_in_browser(data)"),
]
story += bullets([
    "<c>render_html(data)</c> -- produce an HTML string.",
    "Write to a tempfile created with "
    "<c>tempfile.mkstemp(suffix=&quot;.html&quot;, prefix=&quot;invoice_preview_&quot;)</c>.",
    "<c>webbrowser.open(&quot;file:///&quot; + path)</c> -- backslashes "
    "converted to forward slashes for the URL.",
])
story += [
    p("<c>mkstemp</c> returns <c>(fd, path)</c>. The fd is closed immediately "
      "so we can re-open the path in text mode with explicit "
      "<c>utf-8</c> encoding."),

    h4("export_pdf(data)"),
]
story += bullets([
    "Try to <c>import reportlab</c>. If missing, show "
    "<c>messagebox.showerror</c> with install instructions and return.",
    "Sanitise the invoice number for use as a filename (anything "
    "non-alphanumeric becomes <c>_</c>).",
    "<c>filedialog.asksaveasfilename</c> -- if the user cancels, return "
    "silently.",
    "Call <c>_build_pdf(data, path)</c>. On exception, show the error in a "
    "<c>messagebox</c>.",
    "On success, show a confirmation dialog with the saved path.",
])

story += [
    h4("_build_pdf(data, path)"),
    p("Uses <b>reportlab Platypus</b> -- a high-level document model. Every "
      '"thing" on the page is a <i>flowable</i> (Paragraph, Spacer, Table, '
      "Image&hellip;) appended to a <c>story</c> list. <c>doc.build(story)</c> "
      "runs them through page layout, handling pagination automatically."),
    h4("Flowables used"),
]
story += bullets([
    "<c>SimpleDocTemplate</c> -- the document. A4, 15&nbsp;mm margins.",
    "<c>Paragraph(text, style)</c> -- text block. Supports a small subset of "
    "HTML (<c>&lt;b&gt;</c>, <c>&lt;i&gt;</c>, <c>&lt;br/&gt;</c>, "
    "<c>&lt;font&gt;</c>).",
    "<c>Spacer(width, height)</c> -- vertical gap.",
    "<c>Table(rows, colWidths=&hellip;, hAlign=&hellip;)</c> -- grid of "
    "flowables / strings.",
    "<c>TableStyle([commands])</c> -- formats cells. Each command is a tuple "
    "<c>(op, (col0,row0), (col1,row1), &hellip;args)</c>.",
])

story += [
    p("<c>TableStyle</c> ops used here: <c>BACKGROUND</c>, <c>TEXTCOLOR</c>, "
      "<c>FONT</c>, <c>ALIGN</c>, <c>VALIGN</c>, <c>BOX</c>, "
      "<c>INNERGRID</c>, <c>LINEABOVE</c>, padding ops, and "
      "<c>ROWBACKGROUNDS</c> (zebra stripes)."),

    h4("Document layout (top to bottom)"),
]
story += bullets([
    "Title row -- &quot;INVOICE&quot; left, meta table (invoice #, dates, PO, "
    "terms, method) right.",
    "From / Bill To -- two-column Table with paragraphs containing newline-"
    "separated address lines.",
    "Line items Table -- dark header row, zebra-striped data rows, "
    "<c>repeatRows=1</c> so the header repeats on overflow.",
    "Totals -- right-aligned Table; discount and tax rows are skipped if "
    "zero. Last row is bold green with a top rule.",
    "Bank info, notes, terms -- only if non-empty.",
])

story += [
    p("<c>html.escape</c> is applied wherever user text reaches a Paragraph "
      "because Paragraph parses inline HTML."),

    h4("render_html(data)"),
    p("Generates a self-contained HTML document with inline CSS. Same input "
      "shape as <c>_build_pdf</c>. Empty rows / sections are skipped the "
      "same way. The CSS includes a <c>@media print</c> block so Ctrl+P in "
      "the browser produces a clean print version."),
    h4("CSS notes"),
]
story += bullets([
    "<c>box-sizing: border-box</c> for predictable widths.",
    "Flexbox for the top header (title left, meta right) and the parties "
    "row (From / Bill To).",
    "<c>font-variant-numeric: tabular-nums</c> on numeric columns so digits "
    "align vertically.",
])

story.append(PageBreak())

# ── 7. tkinter cheat sheet
story += [
    h2("7. tkinter cheat sheet"),
]
story += bullets([
    "<b>pack vs grid</b> -- they manage <i>children</i> of a parent. The "
    "same parent can use only one of them. Frames are laid out with "
    "<c>pack</c>; form fields inside cards use <c>grid</c> because we want "
    "labelled rows aligned in columns.",
    "<b>Event binding</b> -- <c>widget.bind(&quot;&lt;Event&gt;&quot;, callback)</c>. "
    "The callback receives an <c>event</c> object (we ignore it via "
    "<c>lambda _e: ...</c>).",
    "<b>Events used here</b> -- <c>&lt;Configure&gt;</c> (resize), "
    "<c>&lt;MouseWheel&gt;</c> (scroll), <c>&lt;KeyRelease&gt;</c> (after a "
    "keystroke commits), <c>&lt;&lt;ComboboxSelected&gt;&gt;</c> "
    "(virtual events use double brackets).",
    "<b>Lambda default-arg capture</b> -- <c>command=lambda i=item: f(i)</c> "
    "snapshots <c>item</c> at definition time. Critical inside loops.",
    "<b>messagebox and filedialog</b> -- top-level modal dialogs.",
])

# ── 8. reportlab cheat sheet
story += [
    h2("8. reportlab cheat sheet"),
]
story += bullets([
    "<b>Platypus</b> -- <i>Page Layout And Typography Using Scripts</i>. "
    "You build a flat list of flowables; the engine handles pagination.",
    "<b>Coords in TableStyle</b> -- <c>(col, row)</c>, <b>not</b> "
    "<c>(row, col)</c>. <c>(0, 0)</c> is top-left, <c>(-1, -1)</c> is "
    "bottom-right.",
    "<b>Units</b> -- <c>from reportlab.lib.units import mm</c>, then "
    "<c>15 * mm</c>. Internally everything is in points (1 pt = 1/72 inch).",
    "<b>Colours</b> -- <c>colors.HexColor(&quot;#2c3e50&quot;)</c> accepts "
    "CSS-style hex.",
    "<b>hAlign=&quot;RIGHT&quot;</b> on a Table aligns the entire table "
    "within its frame (used for the totals box).",
])

# ── 9. Calculation reference
story += [
    h2("9. Calculation reference"),
    table(
        [["Quantity", "Formula"],
         ["Line amount",     "qty * unit_price * (1 - line_disc / 100)"],
         ["Subtotal",        "sum of all line amounts"],
         ["Discount amount", "subtotal * global_disc_pct / 100"],
         ["After discount",  "subtotal - discount_amount"],
         ["Tax amount",      "after_discount * tax_pct / 100"],
         ["Total",           "after_discount + tax_amount"]],
        col_widths=[42 * mm, None]),
    p("The order matters: tax applies <i>after</i> the global discount."),
]


# ─────────────────────────────────────────────────────────────────────────
# Page footer
# ─────────────────────────────────────────────────────────────────────────
def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MID)
    canvas.drawString(15 * mm, 10 * mm,
                      "Invoice Generator -- Code Walkthrough")
    canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build():
    doc = SimpleDocTemplate(
        OUTPUT, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title="Invoice Generator -- Code Walkthrough",
        author="Invoice Generator project",
    )
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    print(f"Wrote {OUTPUT} ({os.path.getsize(OUTPUT):,} bytes)")


if __name__ == "__main__":
    build()
