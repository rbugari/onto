"""Build the presentation guide PDF from its versioned Markdown source."""
from __future__ import annotations

import argparse
from html import escape
from pathlib import Path

from markdown_it import MarkdownIt
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "12_DEMO_END_TO_END.md"
OUTPUT = ROOT / "deliverables" / "ONTO_Guion_Demo_Ventas_Distribuidas.pdf"


def build_pdf(source: Path, output: Path, header: str = "ONTO | Guion del presentador",
              footer: str = "Ventas distribuidas | Caso sintetico | 2026-10-08",
              title: str = "ONTO - Guion de demo: ventas distribuidas") -> None:
    fonts = Path("C:/Windows/Fonts")
    family, bold = "Helvetica", "Helvetica-Bold"
    if all((fonts / filename).exists() for filename in ("segoeui.ttf", "segoeuib.ttf", "segoeuii.ttf", "segoeuiz.ttf")):
        for name, filename in (("Guide", "segoeui.ttf"), ("Guide-Bold", "segoeuib.ttf"),
                               ("Guide-Italic", "segoeuii.ttf"), ("Guide-BoldItalic", "segoeuiz.ttf")):
            pdfmetrics.registerFont(TTFont(name, str(fonts / filename)))
        pdfmetrics.registerFontFamily("Guide", normal="Guide", bold="Guide-Bold", italic="Guide-Italic", boldItalic="Guide-BoldItalic")
        family, bold = "Guide", "Guide-Bold"
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="GuideBody", fontName=family, fontSize=10, leading=15,
                             spaceAfter=8, textColor=colors.HexColor("#20262b"), alignment=TA_LEFT))
    styles.add(ParagraphStyle(name="GuideQuote", parent=styles["GuideBody"], leftIndent=14,
                             rightIndent=8, borderPadding=8, backColor=colors.HexColor("#eef5f4"), spaceAfter=12))
    styles.add(ParagraphStyle(name="GuideCell", parent=styles["GuideBody"], fontSize=8.5, leading=12, spaceAfter=0))
    styles.add(ParagraphStyle(name="GuideCode", fontName="Courier", fontSize=8, leading=11,
                             spaceAfter=12, backColor=colors.HexColor("#f2f4f5"), borderPadding=8))
    for level, size in ((1, 24), (2, 19), (3, 13), (4, 11)):
        styles.add(ParagraphStyle(name=f"GuideHeading{level}", fontName=bold, fontSize=size,
                                 leading=size + 6, spaceBefore=12, spaceAfter=12, keepWithNext=True,
                                 textColor=colors.HexColor("#176b64")))
    parser = MarkdownIt("commonmark").enable("table")
    parser.renderer.rules["code_inline"] = lambda tokens, index, options, env: (
        f'<font name="Courier" size="8">{escape(tokens[index].content)}</font>'
    )
    tokens = parser.parse(source.read_text(encoding="utf-8"))
    story = []
    list_stack = []
    quote_depth = 0
    heading = 0
    table_rows = None
    table_row = []
    for token in tokens:
        if token.type == "heading_open":
            heading = min(int(token.tag[1:]), 4)
            if heading == 2 and story:
                story.append(PageBreak())
        elif token.type == "heading_close":
            heading = 0
        elif token.type in {"bullet_list_open", "ordered_list_open"}:
            list_stack.append({"ordered": token.type == "ordered_list_open", "number": int(token.attrGet("start") or 1), "prefix": ""})
        elif token.type in {"bullet_list_close", "ordered_list_close"}:
            list_stack.pop()
        elif token.type == "list_item_open":
            current = list_stack[-1]
            current["prefix"] = f'{current["number"]}. ' if current["ordered"] else "- "
            current["number"] += 1
        elif token.type == "blockquote_open":
            quote_depth += 1
        elif token.type == "blockquote_close":
            quote_depth -= 1
        elif token.type == "table_open":
            table_rows = []
        elif token.type == "tr_open":
            table_row = []
        elif token.type == "tr_close":
            table_rows.append(table_row)
        elif token.type == "table_close":
            table = Table(table_rows, colWidths=[(A4[0] - 88) / len(table_rows[0])] * len(table_rows[0]), repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6efee")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#ccd5d5")),
                ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]))
            story.extend([table, Spacer(1, 12)])
            table_rows = None
        elif token.type == "inline":
            content = parser.renderInline(token.content)
            if table_rows is not None:
                table_row.append(Paragraph(content, styles["GuideCell"]))
            else:
                prefix = list_stack[-1]["prefix"] if list_stack else ""
                if list_stack:
                    list_stack[-1]["prefix"] = ""
                style = styles[f"GuideHeading{heading}"] if heading else styles["GuideQuote" if quote_depth else "GuideBody"]
                story.append(Paragraph(escape(prefix) + content, style))
        elif token.type in {"fence", "code_block"}:
            story.append(Paragraph(escape(token.content).replace("\n", "<br/>"), styles["GuideCode"]))

    def page_decoration(canvas, document):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#176b64"))
        canvas.setFont(bold, 8)
        canvas.drawString(44, A4[1] - 29, header)
        canvas.setStrokeColor(colors.HexColor("#ccd5d5"))
        canvas.line(44, A4[1] - 36, A4[0] - 44, A4[1] - 36)
        canvas.setFont(family, 8)
        canvas.setFillColor(colors.HexColor("#59666a"))
        canvas.drawString(44, 24, footer)
        canvas.drawRightString(A4[0] - 44, 24, str(document.page))
        canvas.restoreState()

    output.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(str(output), pagesize=A4, leftMargin=44, rightMargin=44,
                                 topMargin=52, bottomMargin=44,
                                 title=title, author="ONTO")
    document.build(story, onFirstPage=page_decoration, onLaterPages=page_decoration)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generar un PDF desde Markdown (por defecto, el guion de la demo)")
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--header", default="ONTO | Guion del presentador")
    parser.add_argument("--footer", default="Ventas distribuidas | Caso sintetico | 2026-10-08")
    parser.add_argument("--title", default="ONTO - Guion de demo: ventas distribuidas")
    args = parser.parse_args()
    build_pdf(args.source, args.output, args.header, args.footer, args.title)
    print(args.output.resolve())


if __name__ == "__main__":
    main()