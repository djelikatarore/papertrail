from fpdf import FPDF

from app.config.settings import DRAFT_PDF_FOOTER_TEXT

# fpdf2's core Helvetica font only supports the WinAnsi (~cp1252) character set.
# LLM-generated text sometimes includes typographic characters outside that range
# (e.g. a narrow no-break space or non-breaking hyphen, both observed from Groq's
# output elsewhere in this project) which would otherwise crash PDF generation.
_UNICODE_REPLACEMENTS = {
    "‐": "-",  # hyphen
    "‑": "-",  # non-breaking hyphen
    " ": " ",  # narrow no-break space
    " ": " ",  # non-breaking space
}


def _sanitize_for_pdf(text: str) -> str:
    for unicode_char, replacement in _UNICODE_REPLACEMENTS.items():
        text = text.replace(unicode_char, replacement)
    return text.encode("latin-1", errors="replace").decode("latin-1")


class _DraftPdf(FPDF):
    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, DRAFT_PDF_FOOTER_TEXT, align="C")


def generate_pdf_from_text(title: str, content: str, output_path: str) -> None:
    """Renders a draft's plain-text content into a basic single-column PDF, with
    a discreet footer on every page marking it as generated (not a real uploaded
    paper) — relevant for future citation-graph/comparison logic that may want to
    exclude or flag these differently from genuine papers."""
    pdf = _DraftPdf()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 10, _sanitize_for_pdf(title))
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 7, _sanitize_for_pdf(content or ""))

    pdf.output(output_path)
