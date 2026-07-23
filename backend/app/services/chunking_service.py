import re

SECTION_NAMES = [
    "abstract",
    "introduction",
    "related work",
    "background",
    "methodology",
    "methods",
    "method",
    "materials and methods",
    "experiments",
    "experiment",
    "experimental setup",
    "results",
    "discussion",
    "conclusion",
    "conclusions",
    "limitations",
    "acknowledgments",
    "acknowledgements",
    "references",
]

# Matches a section title on its own line, optionally preceded by a number
# (e.g. "1 Introduction", "3.2 Methodology"), case-insensitive.
SECTION_PATTERN = re.compile(
    r"^[ \t]*(?:\d+\.?\d*\.?[ \t]+)?(" + "|".join(SECTION_NAMES) + r")[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)

FALLBACK_CHUNK_WORD_TARGET = 450  # ~600 tokens, approximated via word count


def chunk_text(raw_text: str) -> list[tuple[str, str]]:
    """Splits raw_text into (section_reference, chunk_text) pairs.

    Tries to detect real section headers (Abstract/Introduction/Method/...) via
    regex first. If none are found, falls back to paragraph-based chunks of
    roughly 600 tokens each, labeled "Chunk 1", "Chunk 2", etc.
    """
    matches = list(SECTION_PATTERN.finditer(raw_text))

    if matches:
        chunks = []
        for i, match in enumerate(matches):
            section_name = match.group(1).title()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
            body = raw_text[start:end].strip()
            if body:
                chunks.append((section_name, body))
        if chunks:
            return chunks

    paragraphs = [p.strip() for p in raw_text.split("\n") if p.strip()]
    chunks = []
    current_words: list[str] = []
    chunk_index = 1
    for paragraph in paragraphs:
        current_words.extend(paragraph.split())
        if len(current_words) >= FALLBACK_CHUNK_WORD_TARGET:
            chunks.append((f"Chunk {chunk_index}", " ".join(current_words)))
            chunk_index += 1
            current_words = []
    if current_words:
        chunks.append((f"Chunk {chunk_index}", " ".join(current_words)))

    return chunks
