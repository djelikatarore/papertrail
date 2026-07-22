import fitz

from app.services.ocr_service import OcrUnavailableError, ocr_page

HEADER_FOOTER_MARGIN_RATIO = 0.07
COLUMN_TOLERANCE_RATIO = 0.02
SIDEBAR_MAX_WIDTH_RATIO = 0.05
SIDEBAR_MIN_HEIGHT_RATIO = 0.25


class PdfExtractionError(Exception):
    pass


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

    raw_text = "\n\n".join(t for t in page_texts if t)

    if not raw_text.strip():
        if ocr_unavailable:
            raise PdfExtractionError(
                "No extractable text found and OCR is unavailable (Tesseract is not installed on this machine)"
            )
        raise PdfExtractionError(
            "No extractable text found (the PDF may be a scanned image without a text layer)"
        )

    return raw_text, page_count
