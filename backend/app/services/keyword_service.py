from app.services.llm_service import call_llm
from app.services.summary_service import _prioritize_and_truncate

KEYWORD_SYSTEM_PROMPT = (
    "You are an assistant that extracts keywords from academic papers. "
    "Base your answer ONLY on the provided text."
)


def _build_prompt(selected_chunks: list[tuple[str, str]]) -> str:
    labeled_text = "\n\n".join(f"[Section: {name}]\n{text}" for name, text in selected_chunks)
    return (
        "Extract exactly 5 to 8 keywords or key phrases that best represent the topic "
        "and content of this paper. Respond with ONLY a comma-separated list, nothing else.\n\n"
        "--- PAPER TEXT (chunked by section) ---\n"
        f"{labeled_text}"
    )


async def extract_keywords(chunks: list[tuple[str, str]]) -> list[str]:
    selected_chunks = _prioritize_and_truncate(chunks)
    prompt = _build_prompt(selected_chunks)
    response = await call_llm(prompt, system_prompt=KEYWORD_SYSTEM_PROMPT)

    keywords = [kw.strip() for kw in response.split(",")]
    return [kw for kw in keywords if kw]
