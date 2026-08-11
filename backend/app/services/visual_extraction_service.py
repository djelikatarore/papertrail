import hashlib
import io

import fitz
from PIL import Image

# Images smaller than this (in either dimension) are almost always icons,
# bullet glyphs, or decorative rules rather than real figures — filtering
# them out before they ever become a VisualElement row keeps them from
# wasting one of the capped Vision API calls (see paper_router.py's
# VISION_CALL_CAP) and from cluttering the figure gallery.
MIN_IMAGE_DIMENSION_PX = 50


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


def extract_visual_elements(file_path: str) -> list[tuple[int, bytes, str]]:
    """Returns a list of (page_number, image_bytes, file_extension) for every
    embedded raster image found in the PDF that's at least
    MIN_IMAGE_DIMENSION_PX in both dimensions. Vector-drawn charts/plots that
    are not embedded as images are not detected by this basic extraction.
    Width/height come straight from get_images()'s own tuple, so tiny
    icons/bullets/decorative rules are skipped before the (more expensive)
    extract_image()/SMask-compositing step ever runs on them."""
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

                if smask_xref:
                    mask_image = doc.extract_image(smask_xref)
                    composited = _composite_smask(base_image, mask_image)
                    if composited is not None:
                        results.append((page_index + 1, composited, "png"))
                        continue

                results.append((page_index + 1, base_image["image"], base_image["ext"]))
        return results
    finally:
        doc.close()


def filter_duplicate_images(images: list[tuple[int, bytes, str]]) -> list[tuple[int, bytes, str]]:
    """Drops exact byte-for-byte duplicate images within the same paper —
    catches a repeated header/footer logo or watermark appearing on every
    page. Deliberately exact-hash only (no perceptual/fuzzy hashing): a false
    positive here would silently drop a genuinely repeated real figure, which
    is worse than leaving an occasional duplicate logo in."""
    seen_hashes: set[str] = set()
    deduped = []
    for page_number, image_bytes, ext in images:
        digest = hashlib.md5(image_bytes).hexdigest()
        if digest in seen_hashes:
            continue
        seen_hashes.add(digest)
        deduped.append((page_number, image_bytes, ext))
    return deduped
