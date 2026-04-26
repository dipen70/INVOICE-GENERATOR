"""Invoice rendering: HTML preview in browser, PDF export via reportlab."""
import html
import os
import tempfile
import webbrowser
from tkinter import filedialog, messagebox

from audit import log_event


def open_in_browser(data):
    html_str = render_html(data)
    fd, path = tempfile.mkstemp(suffix=".html", prefix="invoice_preview_")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_str)
    webbrowser.open("file:///" + path.replace(os.sep, "/"))
    log_event("previewed", data)


def export_pdf(data):
    try:
        import reportlab  # noqa: F401
    except ImportError:
        messagebox.showerror(
            "Missing Dependency",
            "PDF export requires the 'reportlab' package.\n\n"
            "Install it with:\n    pip install reportlab",
        )
        return

    invoice_no = data["details"].get("invoice_no") or "invoice"
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in invoice_no) 

    path = filedialog.asksaveasfilename( 
        title="Save Invoice as PDF",
        defaultextension=".pdf",
        initialfile=f"{safe_name}.pdf",
        filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
    )
    if not path:
        return

    try:
        _build_pdf(data, path)
    except Exception as exc:
        messagebox.showerror("PDF Export Failed", str(exc))
        return

    messagebox.showinfo("Saved", f"Invoice saved to:\n{path}")


def _build_pdf(data, path):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )

    sym = data["currency_symbol"]
    base = getSampleStyleSheet()

    h_title = ParagraphStyle("h_title", parent=base["Heading1"],
                             textColor=colors.HexColor("#2c3e50"),
                             fontSize=28, leading=32, spaceAfter=2)
    h_section = ParagraphStyle("h_section", parent=base["Heading4"],
                               textColor=colors.HexColor("#2c3e50"),
                               fontSize=10, leading=12, spaceAfter=4)
    body = ParagraphStyle("body", parent=base["Normal"],
                          fontSize=9, leading=12)

    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
        title=f"Invoice {data['details'].get('invoice_no', '')}",
    )
    story = []

    # ── Top: title + meta
    details = data["details"]
    meta_rows = []
    for key, label in [
        ("invoice_no",     "Invoice #"),
        ("issue_date",     "Issue Date"),
        ("due_date",       "Due Date"),
        ("po_number",      "PO #"),
        ("payment_terms",  "Payment Terms"),
        ("payment_method", "Payment Method"),
    ]:
        v = details.get(key, "")
        if v:
            meta_rows.append([f"{label}:", v])

    meta_tbl = Table(meta_rows, colWidths=[32 * mm, 50 * mm], hAlign="RIGHT")
    meta_tbl.setStyle(TableStyle([
        ("FONT",        (0, 0), (-1, -1), "Helvetica", 9),
        ("FONT",        (0, 0), (0, -1),  "Helvetica-Bold", 9), 
        ("TEXTCOLOR",   (0, 0), (0, -1),  colors.HexColor("#2c3e50")),
        ("ALIGN",       (0, 0), (0, -1),  "RIGHT"),
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    top = Table([[Paragraph("INVOICE", h_title), meta_tbl]],
                colWidths=[90 * mm, 90 * mm])
    top.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN",  (1, 0), (1, 0),   "RIGHT"),
    ]))
    story.append(top)
    story.append(Spacer(1, 6 * mm))

    # ── From / Bill To
    def addr_para(title, info, keys):
        lines = [f"<b>{title}</b>"]
        for k in keys:
            v = info.get(k, "")
            if v:
                lines.append(html.escape(v))
        return Paragraph("<br/>".join(lines), body)

    from_p = addr_para("FROM", data["from"],
                       ["company", "address", "citystatezip", "email", "phone", "website"])
    to_p   = addr_para("BILL TO", data["to"],
                       ["client", "company", "address", "citystatezip", "email", "phone"])

    addr_tbl = Table([[from_p, to_p]], colWidths=[90 * mm, 90 * mm])
    addr_tbl.setStyle(TableStyle([
        ("BOX",          (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7")), 
        ("INNERGRID",    (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7")),
        ("VALIGN",       (0, 0), (-1, -1), "TOP"), 
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING",   (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ("BACKGROUND",   (0, 0), (-1, -1), colors.HexColor("#f8fafb")),
    ]))
    story.append(addr_tbl)
    story.append(Spacer(1, 6 * mm))

    # ── Line items
    head = ["Description", "Qty", "Unit Price", "Disc %", "Amount"]
    rows = [head]
    for it in data["items"]:
        if not it["description"] and it["qty"] == 0 and it["price"] == 0:
            continue
        rows.append([
            Paragraph(html.escape(it["description"]), body),
            f"{it['qty']:g}",
            f"{sym} {it['price']:,.2f}",
            f"{it['discount']:g}%",
            f"{sym} {it['amount']:,.2f}", 
        ])
    if len(rows) == 1:
        rows.append(["—", "", "", "", ""])

    items_tbl = Table(rows,
                      colWidths=[80 * mm, 15 * mm, 30 * mm, 20 * mm, 35 * mm],
                      repeatRows=1)
    items_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  colors.HexColor("#2c3e50")),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  colors.white),
        ("FONT",         (0, 0), (-1, 0),  "Helvetica-Bold", 9),
        ("FONT",         (0, 1), (-1, -1), "Helvetica", 9),
        ("ALIGN",        (1, 0), (-1, -1), "RIGHT"), 
        ("ALIGN",        (0, 0), (0, -1),  "LEFT"), 
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"), 
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
            [colors.white, colors.HexColor("#f4f6f7")]),
        ("BOX",          (0, 0), (-1, -1), 0.5,  colors.HexColor("#bdc3c7")),
        ("INNERGRID",    (0, 0), (-1, -1), 0.25, colors.HexColor("#bdc3c7")),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
    ]))
    story.append(items_tbl)
    story.append(Spacer(1, 6 * mm))

    # ── Totals
    tot_rows = [["Subtotal:", f"{sym} {data['subtotal']:,.2f}"]]
    if data["discount_pct"]:
        tot_rows.append([
            f"Discount ({data['discount_pct']:g}%):",
            f"-{sym} {data['discount_amount']:,.2f}",
        ])
    if data["tax_pct"]:
        tot_rows.append([
            f"Tax ({data['tax_pct']:g}%):",
            f"{sym} {data['tax_amount']:,.2f}",
        ])
    tot_rows.append(["TOTAL:", f"{sym} {data['total']:,.2f}"])

    tot_tbl = Table(tot_rows, colWidths=[45 * mm, 45 * mm], hAlign="RIGHT")
    tot_tbl.setStyle(TableStyle([
        ("FONT",         (0, 0),  (-1, -2), "Helvetica", 10),
        ("FONT",         (0, -1), (-1, -1), "Helvetica-Bold", 12),
        ("TEXTCOLOR",    (0, -1), (-1, -1), colors.HexColor("#1a7a4a")),
        ("ALIGN",        (1, 0),  (1, -1),  "RIGHT"),
        ("ALIGN",        (0, 0),  (0, -1),  "RIGHT"),
        ("LINEABOVE",    (0, -1), (-1, -1), 1.2, colors.HexColor("#2c3e50")),
        ("TOPPADDING",   (0, -1), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0),  (-1, -1), 4),
    ]))
    story.append(tot_tbl)
    story.append(Spacer(1, 8 * mm))

    # ── Bank info
    bank = data["bank"]
    bank_lines = []
    for k, label in [
        ("bank_name",     "Bank / Account Name"),
        ("account_no",    "Account Number"),
        ("routing_swift", "Routing / SWIFT"),
        ("iban",          "IBAN"),
    ]:
        v = bank.get(k, "")
        if v:
            bank_lines.append(f"<b>{label}:</b> {html.escape(v)}")
    if bank_lines:
        story.append(Paragraph("PAYMENT / BANK INFO", h_section))
        story.append(Paragraph("<br/>".join(bank_lines), body))
        story.append(Spacer(1, 4 * mm))

    # ── Notes & terms
    if data["notes"]:
        story.append(Paragraph("NOTES", h_section))
        story.append(Paragraph(html.escape(data["notes"]).replace("\n", "<br/>"), body))
        story.append(Spacer(1, 3 * mm))
    if data["terms"]:
        story.append(Paragraph("TERMS &amp; CONDITIONS", h_section))
        story.append(Paragraph(html.escape(data["terms"]).replace("\n", "<br/>"), body))

    # ── Prepared by (signer)
    signer = data.get("signer")
    if signer:
        story.append(Spacer(1, 8 * mm))
        signer_style = ParagraphStyle(
            "signer", parent=body, fontSize=9, leading=12,
            textColor=colors.HexColor("#7f8c8d"),
        )
        story.append(Paragraph(
            f"<b>Prepared by:</b> {html.escape(signer.get('name', ''))} "
            f"&nbsp;·&nbsp; {html.escape(signer.get('position', ''))} "
            f"&nbsp;·&nbsp; {html.escape(signer.get('email', ''))}",
            signer_style,
        ))

    doc.build(story)


def render_html(data):
    sym = data["currency_symbol"]
    e = lambda s: html.escape(str(s) if s is not None else "")

    # Line item rows
    item_rows = []
    for it in data["items"]:
        if not it["description"] and it["qty"] == 0 and it["price"] == 0:
            continue
        item_rows.append(
            f"<tr>"
            f"<td>{e(it['description'])}</td>"
            f"<td class='num'>{it['qty']:g}</td>"
            f"<td class='num'>{sym} {it['price']:,.2f}</td>"
            f"<td class='num'>{it['discount']:g}%</td>"
            f"<td class='num'>{sym} {it['amount']:,.2f}</td>"
            f"</tr>"
        )
    items_html = "\n".join(item_rows) or (
        "<tr><td colspan='5' style='text-align:center;color:#888;padding:18px;'>"
        "No line items</td></tr>"
    )

    def addr_block(d, keys):
        return "<br>".join(e(d.get(k, "")) for k in keys if d.get(k, ""))

    from_html = addr_block(
        data["from"],
        ["company", "address", "citystatezip", "email", "phone", "website"],
    ) or "<em style='color:#aaa;'>—</em>"
    to_html = addr_block(
        data["to"],
        ["client", "company", "address", "citystatezip", "email", "phone"],
    ) or "<em style='color:#aaa;'>—</em>"

    # Bank info
    bank_rows = ""
    for k, label in [
        ("bank_name",     "Bank / Account Name"),
        ("account_no",    "Account Number"),
        ("routing_swift", "Routing / SWIFT"),
        ("iban",          "IBAN"),
    ]:
        v = data["bank"].get(k, "")
        if v:
            bank_rows += f"<tr><th>{label}</th><td>{e(v)}</td></tr>"
    bank_section = (
        f"<h3>Payment / Bank Info</h3><table class='kv'>{bank_rows}</table>"
        if bank_rows else ""
    )

    notes_section = (
        f"<div class='block'><h3>Notes</h3><p>"
        f"{e(data['notes']).replace(chr(10), '<br>')}</p></div>"
        if data["notes"] else ""
    )
    terms_section = (
        f"<div class='block'><h3>Terms &amp; Conditions</h3><p>"
        f"{e(data['terms']).replace(chr(10), '<br>')}</p></div>"
        if data["terms"] else ""
    )

    signer = data.get("signer")
    signer_section = (
        f"<div class='signer'><b>Prepared by:</b> {e(signer.get('name', ''))} "
        f"&middot; {e(signer.get('position', ''))} "
        f"&middot; {e(signer.get('email', ''))}</div>"
        if signer else ""
    )

    discount_row = (
        f"<tr><td>Discount ({data['discount_pct']:g}%):</td>"
        f"<td class='num'>-{sym} {data['discount_amount']:,.2f}</td></tr>"
        if data["discount_pct"] else ""
    )
    tax_row = (
        f"<tr><td>Tax ({data['tax_pct']:g}%):</td>"
        f"<td class='num'>{sym} {data['tax_amount']:,.2f}</td></tr>"
        if data["tax_pct"] else ""
    )

    # Meta block
    details = data["details"]
    meta_rows = ""
    for key, label in [
        ("invoice_no",     "Invoice #"),
        ("issue_date",     "Issue Date"),
        ("due_date",       "Due Date"),
        ("po_number",      "PO #"),
        ("payment_terms",  "Payment Terms"),
        ("payment_method", "Payment Method"),
    ]:
        v = details.get(key, "")
        if v:
            meta_rows += f"<tr><th>{label}:</th><td>{e(v)}</td></tr>"

    title_no = e(details.get("invoice_no", ""))

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Invoice {title_no}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #333;
         margin: 0; padding: 30px; background: #f0f4f8; }}
  .sheet {{ max-width: 880px; margin: 0 auto; background: white;
            padding: 40px 48px; box-shadow: 0 4px 18px rgba(0,0,0,.08);
            border-radius: 6px; }}
  h1 {{ color: #2c3e50; margin: 0; font-size: 34px; letter-spacing: 3px; }}
  h3 {{ color: #2c3e50; margin: 18px 0 8px; font-size: 12px;
        letter-spacing: 1px; text-transform: uppercase;
        border-bottom: 2px solid #2c3e50; padding-bottom: 4px; }}
  .top {{ display: flex; justify-content: space-between;
          align-items: flex-start; margin-bottom: 20px; }}
  table.meta {{ border-collapse: collapse; }}
  table.meta th {{ text-align: right; color: #2c3e50;
                   padding: 2px 10px 2px 0; font-weight: 600;
                   font-size: 12px; }}
  table.meta td {{ text-align: left; padding: 2px 0; font-size: 12px; }}
  .parties {{ display: flex; gap: 16px; margin: 16px 0 24px; }}
  .party {{ flex: 1; background: #f8fafb; border: 1px solid #dfe6ea;
            padding: 14px 16px; border-radius: 4px; font-size: 13px;
            line-height: 1.5; }}
  .party strong {{ color: #2c3e50; font-size: 11px; text-transform: uppercase;
                   letter-spacing: 1px; display: block; margin-bottom: 6px; }}
  table.items {{ width: 100%; border-collapse: collapse; margin-bottom: 18px; }}
  table.items th {{ background: #2c3e50; color: white; padding: 10px 8px;
                    text-align: left; font-size: 12px; }}
  table.items th.num, table.items td.num {{ text-align: right;
                                            font-variant-numeric: tabular-nums; }}
  table.items td {{ padding: 8px; border-bottom: 1px solid #ecf0f1;
                    font-size: 13px; }}
  table.items tbody tr:nth-child(even) td {{ background: #f8fafb; }}
  .totals-wrap {{ display: flex; justify-content: flex-end; margin-bottom: 24px; }}
  table.totals {{ min-width: 280px; border-collapse: collapse; }}
  table.totals td {{ padding: 6px 12px; font-size: 13px; }}
  table.totals td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  table.totals tr.total td {{ font-size: 16px; font-weight: bold;
                               color: #1a7a4a; border-top: 2px solid #2c3e50;
                               padding-top: 10px; }}
  table.kv {{ border-collapse: collapse; }}
  table.kv th {{ text-align: left; padding: 4px 16px 4px 0; color: #2c3e50;
                 font-weight: 600; font-size: 13px; }}
  table.kv td {{ padding: 4px 0; font-size: 13px; }}
  .block p {{ font-size: 13px; line-height: 1.5; white-space: pre-wrap;
              margin: 4px 0; }}
  .signer {{ margin-top: 28px; padding-top: 12px;
             border-top: 1px solid #ecf0f1; color: #7f8c8d;
             font-size: 12px; }}
  .signer b {{ color: #2c3e50; }}
  @media print {{
    body {{ background: white; padding: 0; }}
    .sheet {{ box-shadow: none; border-radius: 0; padding: 20px; max-width: none; }}
  }}
</style>
</head>
<body>
<div class="sheet">
  <div class="top">
    <h1>INVOICE</h1>
    <table class="meta">{meta_rows}</table>
  </div>

  <div class="parties">
    <div class="party"><strong>From</strong>{from_html}</div>
    <div class="party"><strong>Bill To</strong>{to_html}</div>
  </div>

  <table class="items">
    <thead>
      <tr>
        <th>Description</th>
        <th class="num">Qty</th>
        <th class="num">Unit Price</th>
        <th class="num">Disc %</th>
        <th class="num">Amount</th>
      </tr>
    </thead>
    <tbody>
      {items_html}
    </tbody>
  </table>

  <div class="totals-wrap">
    <table class="totals">
      <tr><td>Subtotal:</td><td class="num">{sym} {data['subtotal']:,.2f}</td></tr>
      {discount_row}
      {tax_row}
      <tr class="total"><td>TOTAL:</td>
          <td class="num">{sym} {data['total']:,.2f}</td></tr>
    </table>
  </div>

  {bank_section}
  {notes_section}
  {terms_section}
  {signer_section}
</div>
</body>
</html>"""
