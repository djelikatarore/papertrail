import asyncio
import base64
import re

import groq

from app.config.settings import GROQ_API_KEY, GROQ_API_KEY_2, GROQ_MODEL, GROQ_VISION_MODEL
from app.utils.logging_utils import safe_log

RETRY_DELAY_SECONDS = 2
# Text calls (summary/keywords/paper-type) used to get only 2 attempts with a
# short fixed delay (2s, then 4s) — nowhere near Groq's actual reported wait on
# a 429 (often 20-30s+), so a rate-limited call was essentially guaranteed to
# fail both attempts and be given up on permanently (confirmed in practice:
# papers uploaded close together, or sharing quota with other concurrent Groq
# activity, silently ended up with empty summary/keywords/paper-type). Now
# uses the same retry-after-aware strategy as vision calls below. 5 attempts
# (vs. vision's 20) since a text call only needs to clear one shared TPM
# window, not survive dozens of sequential per-image calls.
TEXT_MAX_ATTEMPTS = 5
# Vision calls hit a much tighter per-minute token budget than text calls (each
# image costs ~3000+ tokens vs. a few hundred for text), and a paper can have
# dozens of figures queued back-to-back — confirmed in practice: a 75-page paper
# with 83 figures blew through Groq's 8000 TPM limit almost immediately, and the
# short fixed retry delay above (RETRY_DELAY_SECONDS) wasn't remotely long enough
# to wait out the ~20-25s Groq actually reports before the quota window resets,
# so most images failed outright after 2 quick, doomed attempts. Vision calls
# get a much larger attempt budget and wait the real duration Groq reports
# instead of a short guess, so a rate-limited image eventually succeeds rather
# than being given up on.
VISION_MAX_ATTEMPTS = 20
DEFAULT_RETRY_SECONDS = 25.0
# Groq's reported Retry-After can be pathologically large under real quota
# exhaustion — confirmed in practice: "waiting 1409.0s before retry" on a
# single image, which at VISION_MAX_ATTEMPTS could stall one call for hours.
# Clamping the wait keeps a rate-limited image bounded (it just gives up
# sooner and surfaces as a processing_warning instead of stalling the whole
# paper) while still honoring Groq's real reported wait for the common case
# (well under a minute).
MAX_RETRY_WAIT_SECONDS = 60.0
# Without this, a slow/degraded Groq API response can hang a call indefinitely —
# confirmed in practice: an upload with just 2 figures froze the entire FastAPI
# event loop for 10+ minutes on a single stuck call, since upload_paper called
# call_llm/call_vision_llm synchronously. A timeout turns that into a clean,
# bounded APITimeoutError (retried like any other error below, then surfaced as
# a normal LlmError) instead of an indefinite freeze.
REQUEST_TIMEOUT_SECONDS = 45
# Without an explicit cap, the API's own default max output length silently
# truncated long responses mid-sentence — confirmed in practice: the longer
# summary format (summary_service.py, 8-14 sentences per block) got cut off
# partway through the second of four blocks, well before Key Results or
# Limitations, with no error raised (just a shorter-than-intended response
# that then failed to parse). 3000 comfortably covers four ~14-sentence
# blocks plus citation tags and formatting (a real successful run measured
# ~1750 tokens of actual output) while staying under Groq's 8000 TPM
# *per-request* ceiling once combined with a near-MAX_PROMPT_CHARS input —
# 4096 was tried first and pushed a large prompt over that combined limit
# (a 413, not a rate limit: "Requested 8306, Limit 8000"). Short responses
# (keywords, paper-type, vision descriptions) are entirely unaffected since
# this is only an upper bound, not a target length.
MAX_COMPLETION_TOKENS = 3000

# Async client: these calls now run as real asyncio I/O instead of blocking the
# worker thread, so a slow Groq response only suspends the one request awaiting
# it — the event loop stays free to serve /health and every other request in
# the meantime (a plain sync client + timeout only bounds the damage; it doesn't
# stop a single slow call from freezing the whole server).
_client = groq.AsyncGroq(api_key=GROQ_API_KEY, timeout=REQUEST_TIMEOUT_SECONDS)
# Optional second Groq account, its own separate quota — see GROQ_API_KEY_2 in
# settings.py. None when not configured, in which case _call_groq behaves
# exactly as before (single key, waits out its own rate limit).
_client_2 = groq.AsyncGroq(api_key=GROQ_API_KEY_2, timeout=REQUEST_TIMEOUT_SECONDS) if GROQ_API_KEY_2 else None


class LlmError(Exception):
    pass


def _strip_thinking_block(text: str) -> str:
    """qwen3.6-27b (thinking mode) prefixes its answer with a <think>...</think>
    reasoning block; strip it so only the actual answer is kept. If the model
    never emits the closing </think> tag, the first pass matches nothing and
    the entire raw reasoning trace used to leak through as the "answer" —
    confirmed in practice on several image descriptions. The second pass
    strips an unclosed <think> to the end of the string as a fallback."""
    stripped = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    stripped = re.sub(r"<think>.*$", "", stripped, flags=re.DOTALL)
    return stripped.strip()


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
                return min(float(retry_after), MAX_RETRY_WAIT_SECONDS)
            except ValueError:
                pass

    match = re.search(r"try again in ([\d.]+)s", str(exc))
    if match:
        return min(float(match.group(1)), MAX_RETRY_WAIT_SECONDS)

    return DEFAULT_RETRY_SECONDS


async def _call_groq(
    model: str, messages: list, max_attempts: int, label: str, reasoning_effort: str | None = None
) -> str:
    """Shared retry loop for both text and vision Groq calls. A RateLimitError
    (429) waits the real duration Groq reports instead of a short fixed guess —
    a rate-limited call almost always succeeds on the next attempt once that
    real window has passed, whereas retrying immediately just fails again.
    Other retryable errors (timeout, generic API error) don't carry a reported
    wait time, so those keep the short escalating fixed delay.

    If a second Groq key is configured (_client_2), the very first rate limit
    hit switches to it immediately instead of waiting out the primary key's
    window — a second account has its own separate quota, so there's nothing
    to gain by waiting when it can serve the request right now. Only one
    switch ever happens per call: if the secondary key later gets rate-limited
    too, it falls back to the normal wait-and-retry behavior on whichever
    client is current, rather than bouncing back and forth between two
    exhausted keys.

    reasoning_effort is left unset (model default) unless the caller passes
    it — call_llm's GROQ_MODEL (openai/gpt-oss-120b) is a reasoning model
    that spends completion tokens on an internal, invisible reasoning pass
    before writing the actual answer. Confirmed in practice: with the longer
    summary format, the default reasoning depth consumed 2888 of a 3000
    max_completion_tokens budget, leaving ~100 tokens for the real answer and
    silently truncating it (finish_reason="length") after little more than
    the Contribution block. "low" cut that to ~30 reasoning tokens with no
    loss of a complete, well-formed response."""
    client = _client
    switched_client = False
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            kwargs = {"reasoning_effort": reasoning_effort} if reasoning_effort else {}
            response = await client.chat.completions.create(
                model=model, messages=messages, max_completion_tokens=MAX_COMPLETION_TOKENS, **kwargs
            )
            return response.choices[0].message.content
        except groq.RateLimitError as exc:
            last_error = exc
            if not switched_client and _client_2 is not None:
                safe_log(f"[llm_service] {label} call rate-limited on primary Groq key, switching to secondary key")
                client = _client_2
                switched_client = True
                continue
            if attempt < max_attempts:
                wait_seconds = _extract_retry_after_seconds(exc)
                safe_log(
                    f"[llm_service] {label} call rate-limited (attempt {attempt}/{max_attempts}), "
                    f"waiting {wait_seconds:.1f}s before retry"
                )
                await asyncio.sleep(wait_seconds)
        except (groq.APIError, groq.APITimeoutError) as exc:
            last_error = exc
            if attempt < max_attempts:
                await asyncio.sleep(RETRY_DELAY_SECONDS * attempt)

    raise LlmError(f"{label} call failed after {max_attempts} attempts: {last_error}") from last_error


async def call_llm(prompt: str, system_prompt: str | None = None) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    return await _call_groq(GROQ_MODEL, messages, TEXT_MAX_ATTEMPTS, "LLM", reasoning_effort="low")


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

    result = await _call_groq(GROQ_VISION_MODEL, messages, VISION_MAX_ATTEMPTS, "Vision")
    return _strip_thinking_block(result)
