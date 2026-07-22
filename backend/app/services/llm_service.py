import time

import groq

from app.config.settings import GROQ_API_KEY, GROQ_MODEL

MAX_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 2

_client = groq.Groq(api_key=GROQ_API_KEY)


class LlmError(Exception):
    pass


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
        except (groq.APIError, groq.APITimeoutError, groq.RateLimitError) as exc:
            last_error = exc
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_DELAY_SECONDS * attempt)

    raise LlmError(f"LLM call failed after {MAX_ATTEMPTS} attempts: {last_error}") from last_error
