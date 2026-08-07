import io

import fitz
from PIL import Image


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
    embedded raster image found in the PDF. Vector-drawn charts/plots that are
    not embedded as images are not detected by this basic extraction."""
    doc = fitz.open(file_path)
    try:
        results = []
        for page_index in range(doc.page_count):
            page = doc[page_index]
            for image_info in page.get_images(full=True):
                xref = image_info[0]
                smask_xref = image_info[1]
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
