import fitz


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
                base_image = doc.extract_image(xref)
                results.append((page_index + 1, base_image["image"], base_image["ext"]))
        return results
    finally:
        doc.close()
