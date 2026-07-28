import re
from difflib import SequenceMatcher

from app.services.llm_service import call_llm
from app.utils.logging_utils import safe_log

MAX_SUGGESTIONS = 10
FEEDBACK_MATCH_THRESHOLD = 0.75

FEEDBACK_SYSTEM_PROMPT = (
    "You are an assistant that turns reviewer feedback into specific, actionable "
    "correction suggestions for an academic draft. Base every suggestion ONLY on "
    "the provided feedback text. Never invent feedback that wasn't given."
)


def _build_feedback_prompt(draft_content: str, feedback_text: str) -> str:
    return (
        "Below is a draft document and reviewer feedback about it. Generate a list "
        "of specific, actionable correction suggestions for the draft, based ONLY "
        "on the reviewer feedback below — do not suggest anything the feedback "
        "doesn't support.\n\n"
        "Respond with one suggestion per line, in exactly this format:\n"
        "SUGGESTION: <specific, actionable correction> (Feedback: <short exact quote "
        "from the reviewer feedback that justifies this suggestion>)\n\n"
        "--- DRAFT CONTENT ---\n"
        f"{draft_content}\n\n"
        "--- REVIEWER FEEDBACK ---\n"
        f"{feedback_text}"
    )


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _partial_ratio(snippet: str, feedback_text: str) -> float:
    """Fuzzy substring match: scores how well `snippet` matches some contiguous
    window of `feedback_text`, rather than comparing the two strings as a whole
    (a short quote inside a much longer feedback text would otherwise always
    score low under a plain whole-string ratio, even for an exact substring).
    Lets a faithful paraphrase of a real feedback point pass verification, while
    a fabricated citation with no real counterpart in the feedback still scores
    low."""
    if not snippet or not feedback_text:
        return 0.0
    matcher = SequenceMatcher(None, feedback_text, snippet)
    best_ratio = 0.0
    for block in matcher.get_matching_blocks():
        start = max(block.a - block.b, 0)
        window = feedback_text[start:start + len(snippet)]
        best_ratio = max(best_ratio, SequenceMatcher(None, window, snippet).ratio())
    return best_ratio


def generate_review_suggestions(draft_content: str, feedback_text: str) -> tuple[list[str], int]:
    """Returns (verified_suggestions, discarded_count). Each suggestion the LLM
    proposes must quote a snippet of the actual feedback text as justification;
    a suggestion whose quoted snippet doesn't fuzzy-match (>= FEEDBACK_MATCH_THRESHOLD
    partial ratio) any window of the real feedback text is discarded rather than
    shown to the user — same anti-hallucination principle used throughout the rest
    of the app (verify the citation against the real source text), but tolerant of
    the LLM paraphrasing its citation instead of quoting verbatim."""
    prompt = _build_feedback_prompt(draft_content, feedback_text)
    response = call_llm(prompt, system_prompt=FEEDBACK_SYSTEM_PROMPT)

    normalized_feedback = _normalize(feedback_text)
    matches = re.findall(r"SUGGESTION:\s*(.*?)\s*\(Feedback:\s*([^)]+)\)", response)

    verified = []
    discarded = 0
    for suggestion_text, quoted_snippet in matches[:MAX_SUGGESTIONS]:
        if _partial_ratio(_normalize(quoted_snippet), normalized_feedback) >= FEEDBACK_MATCH_THRESHOLD:
            verified.append(suggestion_text.strip())
        else:
            discarded += 1
            safe_log(f"[feedback_service] Discarded ungrounded suggestion: {suggestion_text!r}")

    return verified, discarded
