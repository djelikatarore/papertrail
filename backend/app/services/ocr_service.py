import io
import os

import fitz
import pytesseract
from PIL import Image

from app.config.settings import OCR_DPI, TESSERACT_CMD

if os.path.exists(TESSERACT_CMD):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


class OcrUnavailableError(Exception):
    pass


def ocr_page(page: fitz.Page) -> str:
    zoom = OCR_DPI / 72
    pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    image = Image.open(io.BytesIO(pixmap.tobytes("png")))

    try:
        return pytesseract.image_to_string(image)
    except pytesseract.TesseractNotFoundError as exc:
        raise OcrUnavailableError(
            "Tesseract OCR is not installed or not found on this machine"
        ) from exc
