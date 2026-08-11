import fitz

from app.services.ocr_service import OcrUnavailableError, ocr_page

HEADER_FOOTER_MARGIN_RATIO = 0.07
COLUMN_TOLERANCE_RATIO = 0.02
SIDEBAR_MAX_WIDTH_RATIO = 0.05
SIDEBAR_MIN_HEIGHT_RATIO = 0.25
TITLE_MAX_CHARS = 300
TITLE_MIN_CHARS = 8
TITLE_MAX_LINES = 4


class PdfExtractionError(Exception):
    pass


def _strip_nul_bytes(text: str) -> str:
    """PyMuPDF's text extraction can emit literal NUL (0x00) characters —
    confirmed on real papers (StyleGAN, DDPM): pages containing math
    equations rendered with custom symbol fonts (braces, delimiters) produced
    a NUL wherever a glyph couldn't be mapped to Unicode. Postgres text
    columns can't store NUL at all ("A string literal cannot contain NUL
    (0x00) characters"), which crashed the whole background processing
    transaction — not just for raw_text, but for every row still pending in
    that same session, since the flush that discovers the bad byte rolls
    back everything not yet committed. Stripped here, at the single point
    all downstream text (raw_text, title, chunks, embeddings) is derived
    from, rather than re-guarding every individual DB write site."""
    return text.replace("\x00", "")


# Same root cause class as the NUL-byte issue above (a PDF font glyph that
# doesn't map cleanly to a single Unicode codepoint) but for typeset
# ligatures instead: many academic-paper PDFs render "ffi"/"fi"/"fl"/"ff"/
# "ffl" as one combined glyph, which PyMuPDF extracts as its own single
# Unicode ligature codepoint (U+FB00-FB06) rather than expanding it back to
# plain ASCII letters. Confirmed in practice: "coefficient" round-tripped as
# "coeﬃcient" in stored raw_text/chunks, which never byte-matches a
# citation like "(Source: Adaptive KL Penalty Coefficient)" that an LLM
# writes back in normal ASCII — wrongly rejecting an otherwise well-grounded
# summary claim. Expanded here at the same single point as _strip_nul_bytes,
# so every downstream consumer (chunking, embeddings, citation verification,
# search, display) sees normal ASCII rather than each needing its own
# workaround.
_LIGATURE_NORMALIZATIONS = str.maketrans({
    "ﬀ": "ff",
    "ﬁ": "fi",
    "ﬂ": "fl",
    "ﬃ": "ffi",
    "ﬄ": "ffl",
    "ﬅ": "st",
    "ﬆ": "st",
})


def _normalize_ligatures(text: str) -> str:
    return text.translate(_LIGATURE_NORMALIZATIONS)


def _is_rotated_sidebar(block, page_width: float, page_height: float) -> bool:
    x0, y0, x1, y1 = block[:4]
    width = x1 - x0
    height = y1 - y0
    return width < page_width * SIDEBAR_MAX_WIDTH_RATIO and height > page_height * SIDEBAR_MIN_HEIGHT_RATIO


def _sort_page_blocks(blocks: list, page_width: float, page_height: float) -> str:
    text_blocks = [
        b for b in blocks
        if b[6] == 0 and b[4].strip() and not _is_rotated_sidebar(b, page_width, page_height)
    ]

    header_band = page_height * HEADER_FOOTER_MARGIN_RATIO
    footer_band = page_height * (1 - HEADER_FOOTER_MARGIN_RATIO)

    headers = [b for b in text_blocks if b[1] < header_band]
    footers = [b for b in text_blocks if b[3] > footer_band]
    body = [b for b in text_blocks if b not in headers and b not in footers]

    midpoint = page_width / 2
    tolerance = page_width * COLUMN_TOLERANCE_RATIO

    # Group body blocks into segments separated by full-width ("spanning") blocks,
    # such as titles, abstracts, or section headers that cross the column midline.
    # Each segment is then read left-column-first, then right-column, which is the
    # correct order for a genuine 2-column layout while still working for single-column
    # content (everything lands in the "left" bucket and "right" stays empty).
    segments: list[list] = []
    current_segment: list = []
    for block in sorted(body, key=lambda b: b[1]):
        x0, x1 = block[0], block[2]
        spans_midline = x0 < midpoint - tolerance and x1 > midpoint + tolerance
        if spans_midline:
            if current_segment:
                segments.append(current_segment)
                current_segment = []
            segments.append([block])
        else:
            current_segment.append(block)
    if current_segment:
        segments.append(current_segment)

    ordered_blocks = []
    for segment in segments:
        left = sorted([b for b in segment if b[0] < midpoint], key=lambda b: b[1])
        right = sorted([b for b in segment if b[0] >= midpoint], key=lambda b: b[1])
        ordered_blocks.extend(left)
        ordered_blocks.extend(right)

    final_order = sorted(headers, key=lambda b: b[1]) + ordered_blocks + sorted(footers, key=lambda b: b[1])

    return "\n".join(b[4].strip() for b in final_order)


def _extract_title_from_first_page(page) -> str | None:
    """The paper's title is usually the largest-font text near the top of page 1.
    Rotated text (arXiv sidebar watermarks) is excluded via the line direction check."""
    top_half = page.rect.height / 2

    spans = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            direction = line.get("dir", (1.0, 0.0))
            if abs(direction[0]) < 0.9:
                continue
            for span in line["spans"]:
                text = span["text"].strip()
                if text and span["bbox"][1] < top_half:
                    spans.append((span["size"], span["bbox"][1], text))

    if not spans:
        return None

    max_size = max(s[0] for s in spans)
    title_spans = sorted((s for s in spans if s[0] >= max_size - 0.5), key=lambda s: s[1])[:TITLE_MAX_LINES]
    title = " ".join(text for _, _, text in title_spans)
    title = " ".join(_normalize_ligatures(_strip_nul_bytes(title)).split())

    return title[:TITLE_MAX_CHARS] if len(title) >= TITLE_MIN_CHARS else None


def extract_title(file_path: str, raw_text: str) -> str:
    try:
        doc = fitz.open(file_path)
        try:
            title = _extract_title_from_first_page(doc[0])
        finally:
            doc.close()
        if title:
            return title
    except Exception:
        pass

    for line in raw_text.splitlines():
        line = line.strip()
        if line:
            return line[:TITLE_MAX_CHARS]

    return "Untitled"


def extract_text(file_path: str) -> tuple[str, int]:
    try:
        doc = fitz.open(file_path)
    except Exception as exc:
        raise PdfExtractionError(f"Could not open PDF: {exc}") from exc

    ocr_unavailable = False

    try:
        page_count = doc.page_count
        page_texts = []
        for page in doc:
            text = _sort_page_blocks(page.get_text("blocks"), page.rect.width, page.rect.height)
            if not text.strip() and not ocr_unavailable:
                try:
                    text = ocr_page(page).strip()
                except OcrUnavailableError:
                    ocr_unavailable = True
                    text = ""
            page_texts.append(text)
    finally:
        doc.close()

    raw_text = _normalize_ligatures(_strip_nul_bytes("\n\n".join(t for t in page_texts if t)))

    if not raw_text.strip():
        if ocr_unavailable:
            raise PdfExtractionError(
                "No extractable text found and OCR is unavailable (Tesseract is not installed on this machine)"
            )
        raise PdfExtractionError(
            "No extractable text found (the PDF may be a scanned image without a text layer)"
        )

    return raw_text, page_count
