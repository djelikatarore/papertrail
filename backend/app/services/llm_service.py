import base64
import re
import time

import groq

from app.config.settings import GROQ_API_KEY, GROQ_MODEL, GROQ_VISION_MODEL

MAX_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 2

_RETRYABLE_ERRORS = (groq.APIError, groq.APITimeoutError, groq.RateLimitError)

_client = groq.Groq(api_key=GROQ_API_KEY)


class LlmError(Exception):
    pass


def _strip_thinking_block(text: str) -> str:
    """qwen3.6-27b (thinking mode) prefixes its answer with a <think>...</think>
    reasoning block; strip it so only the actual answer is kept."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def call_llm(prompt: str, system_prompt: str | None = None) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = _client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
            )
            return response.choices[0].message.content
        except _RETRYABLE_ERRORS as exc:
            last_error = exc
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_DELAY_SECONDS * attempt)

    raise LlmError(f"LLM call failed after {MAX_ATTEMPTS} attempts: {last_error}") from last_error


def call_vision_llm(prompt: str, image_path: str, system_prompt: str | None = None) -> str:
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
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = _client.chat.completions.create(
                model=GROQ_VISION_MODEL,
                messages=messages,
            )
            return _strip_thinking_block(response.choices[0].message.content)
        except _RETRYABLE_ERRORS as exc:
            last_error = exc
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_DELAY_SECONDS * attempt)

    raise LlmError(f"Vision LLM call failed after {MAX_ATTEMPTS} attempts: {last_error}") from last_error
