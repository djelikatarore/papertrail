import hashlib
import io
import re

import fitz
from PIL import Image

# Images smaller than this (in either dimension) are almost always icons,
# bullet glyphs, or decorative rules rather than real figures — filtering
# them out before they ever become a VisualElement row keeps them from
# wasting one of the capped Vision API calls (see paper_router.py's
# VISION_CALL_CAP) and from cluttering the figure gallery.
MIN_IMAGE_DIMENSION_PX = 50

# Matches a caption's leading label ("Figure 3", "Fig. 3a", "Table 2") without
# swallowing the rest of the caption text — that's all the UI needs to show a
# reference next to the image.
_CAPTION_LABEL_PATTERN = re.compile(r"^\s*(Figure|Fig\.?|Table)\s*(\d+[a-zA-Z]?)", re.IGNORECASE)


def _find_figure_reference(page: "fitz.Page", xref: int) -> str | None:
    """Best-effort caption lookup: finds the text block on the same page
    whose leading words look like a figure/table label ("Figure 3: ...") and
    is vertically closest to the image, preferring a caption below the image
    (the common case) over one above it. Not perfect — a page with several
    images close together can occasionally match the wrong caption — but
    good enough to label a figure in the gallery, which is all this is for."""
    rects = page.get_image_rects(xref)
    if not rects:
        return None
    image_rect = rects[0]

    best_label = None
    best_distance = None
    for block in page.get_text("blocks"):
        x0, y0, x1, y1, text = block[0], block[1], block[2], block[3], block[4]
        match = _CAPTION_LABEL_PATTERN.match(text)
        if not match:
            continue
        below = y0 >= image_rect.y1
        distance = (y0 - image_rect.y1) if below else (image_rect.y0 - y1) * 10
        distance = abs(distance)
        if best_distance is None or distance < best_distance:
            best_distance = distance
            kind = "Figure" if match.group(1).lower().startswith("fig") else "Table"
            best_label = f"{kind} {match.group(2)}"

    return best_label


def _composite_smask(base_image: dict, mask_image: dict) -> bytes | None:
    """Some images carry a soft mask (SMask) — extract_image() only returns
    the base image's raw RGB stream and ignores it. When the image's real
    visible content depends on that mask (anti-aliased glyph/highlight
    rendering, common in certain LaTeX-generated PDFs), the raw base stream
    alone is just a solid-colored rectangle instead of the actual figure —
    confirmed on real papers where every SMask'd image extracted as pure
    black. Composite the mask as an alpha channel and flatten onto white
    (matching how a PDF viewer would actually render it) instead. Returns
    None if the mask can't be applied (unexpected format), so the caller can
    fall back to the raw extraction rather than losing the image entirely."""
    try:
        rgb = Image.open(io.BytesIO(base_image["image"])).convert("RGB")
        alpha = Image.open(io.BytesIO(mask_image["image"])).convert("L")
        if alpha.size != rgb.size:
            alpha = alpha.resize(rgb.size)
        rgba = rgb.copy()
        rgba.putalpha(alpha)
        flattened = Image.new("RGB", rgba.size, (255, 255, 255))
        flattened.paste(rgba, mask=alpha)
        buffer = io.BytesIO()
        flattened.save(buffer, format="PNG")
        return buffer.getvalue()
    except Exception:
        return None


def extract_visual_elements(file_path: str) -> list[tuple[int, bytes, str, str | None]]:
    """Returns a list of (page_number, image_bytes, file_extension,
    figure_reference) for every embedded raster image found in the PDF that's
    at least MIN_IMAGE_DIMENSION_PX in both dimensions. Vector-drawn
    charts/plots that are not embedded as images are not detected by this
    basic extraction. Width/height come straight from get_images()'s own
    tuple, so tiny icons/bullets/decorative rules are skipped before the
    (more expensive) extract_image()/SMask-compositing step ever runs on
    them. figure_reference is a best-effort "Figure 3"/"Table 2" caption
    label (see _find_figure_reference) — None if no matching caption was
    found nearby."""
    doc = fitz.open(file_path)
    try:
        results = []
        for page_index in range(doc.page_count):
            page = doc[page_index]
            for image_info in page.get_images(full=True):
                xref, smask_xref, width, height = image_info[:4]
                if width < MIN_IMAGE_DIMENSION_PX or height < MIN_IMAGE_DIMENSION_PX:
                    continue

                base_image = doc.extract_image(xref)
                figure_reference = _find_figure_reference(page, xref)

                if smask_xref:
                    mask_image = doc.extract_image(smask_xref)
                    composited = _composite_smask(base_image, mask_image)
                    if composited is not None:
                        results.append((page_index + 1, composited, "png", figure_reference))
                        continue

                results.append((page_index + 1, base_image["image"], base_image["ext"], figure_reference))
        return results
    finally:
        doc.close()


def filter_duplicate_images(
    images: list[tuple[int, bytes, str, str | None]],
) -> list[tuple[int, bytes, str, str | None]]:
    """Drops exact byte-for-byte duplicate images within the same paper —
    catches a repeated header/footer logo or watermark appearing on every
    page. Deliberately exact-hash only (no perceptual/fuzzy hashing): a false
    positive here would silently drop a genuinely repeated real figure, which
    is worse than leaving an occasional duplicate logo in."""
    seen_hashes: set[str] = set()
    deduped = []
    for page_number, image_bytes, ext, figure_reference in images:
        digest = hashlib.md5(image_bytes).hexdigest()
        if digest in seen_hashes:
            continue
        seen_hashes.add(digest)
        deduped.append((page_number, image_bytes, ext, figure_reference))
    return deduped
