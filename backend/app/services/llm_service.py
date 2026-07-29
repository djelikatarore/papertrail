import asyncio
import base64
import re

import groq

from app.config.settings import GROQ_API_KEY, GROQ_MODEL, GROQ_VISION_MODEL
from app.utils.logging_utils import safe_log

MAX_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 2
# Vision calls hit a much tighter per-minute token budget than text calls (each
# image costs ~3000+ tokens vs. a few hundred for text), and a paper can have
# dozens of figures queued back-to-back — confirmed in practice: a 75-page paper
# with 83 figures blew through Groq's 8000 TPM limit almost immediately, and the
# short fixed retry delay below (RETRY_DELAY_SECONDS) wasn't remotely long enough
# to wait out the ~20-25s Groq actually reports before the quota window resets,
# so most images failed outright after 2 quick, doomed attempts. Vision calls
# get a much larger attempt budget and wait the real duration Groq reports
# instead of a short guess, so a rate-limited image eventually succeeds rather
# than being given up on.
VISION_MAX_ATTEMPTS = 20
VISION_DEFAULT_RETRY_SECONDS = 25.0
# Without this, a slow/degraded Groq API response can hang a call indefinitely —
# confirmed in practice: an upload with just 2 figures froze the entire FastAPI
# event loop for 10+ minutes on a single stuck call, since upload_paper called
# call_llm/call_vision_llm synchronously. A timeout turns that into a clean,
# bounded APITimeoutError (already retried once via _RETRYABLE_ERRORS below,
# then surfaced as a normal LlmError) instead of an indefinite freeze.
REQUEST_TIMEOUT_SECONDS = 45

_RETRYABLE_ERRORS = (groq.APIError, groq.APITimeoutError, groq.RateLimitError)

# Async client: these calls now run as real asyncio I/O instead of blocking the
# worker thread, so a slow Groq response only suspends the one request awaiting
# it — the event loop stays free to serve /health and every other request in
# the meantime (a plain sync client + timeout only bounds the damage; it doesn't
# stop a single slow call from freezing the whole server).
_client = groq.AsyncGroq(api_key=GROQ_API_KEY, timeout=REQUEST_TIMEOUT_SECONDS)


class LlmError(Exception):
    pass


def _strip_thinking_block(text: str) -> str:
    """qwen3.6-27b (thinking mode) prefixes its answer with a <think>...</think>
    reasoning block; strip it so only the actual answer is kept."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _extract_retry_after_seconds(exc: Exception) -> float:
    """Groq's 429 body reports the actual wait time needed (e.g. "Please try
    again in 21.8s") — try the retry-after response header first (the more
    structured source), then fall back to parsing that sentence out of the
    error message, then a conservative default if neither is present."""
    response = getattr(exc, "response", None)
    if response is not None:
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                pass

    match = re.search(r"try again in ([\d.]+)s", str(exc))
    if match:
        return float(match.group(1))

    return VISION_DEFAULT_RETRY_SECONDS


async def call_llm(prompt: str, system_prompt: str | None = None) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = await _client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
            )
            return response.choices[0].message.content
        except _RETRYABLE_ERRORS as exc:
            last_error = exc
            if attempt < MAX_ATTEMPTS:
                await asyncio.sleep(RETRY_DELAY_SECONDS * attempt)

    raise LlmError(f"LLM call failed after {MAX_ATTEMPTS} attempts: {last_error}") from last_error


async def call_vision_llm(prompt: str, image_path: str, system_prompt: str | None = None) -> str:
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    ext = image_path.rsplit(".", 1)[-1].lower()
    mime = "image/png" if ext == "png" else "image/jpeg"

    user_content = [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
    ]

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_content})

    last_error: Exception | None = None
    for attempt in range(1, VISION_MAX_ATTEMPTS + 1):
        try:
            response = await _client.chat.completions.create(
                model=GROQ_VISION_MODEL,
                messages=messages,
            )
            return _strip_thinking_block(response.choices[0].message.content)
        except groq.RateLimitError as exc:
            last_error = exc
            if attempt < VISION_MAX_ATTEMPTS:
                wait_seconds = _extract_retry_after_seconds(exc)
                safe_log(
                    f"[llm_service] Vision call rate-limited (attempt {attempt}/{VISION_MAX_ATTEMPTS}), "
                    f"waiting {wait_seconds:.1f}s before retry"
                )
                await asyncio.sleep(wait_seconds)
        except (groq.APIError, groq.APITimeoutError) as exc:
            last_error = exc
            if attempt < VISION_MAX_ATTEMPTS:
                await asyncio.sleep(RETRY_DELAY_SECONDS * attempt)

    raise LlmError(f"Vision LLM call failed after {VISION_MAX_ATTEMPTS} attempts: {last_error}") from last_error
