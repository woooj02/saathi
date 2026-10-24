"""A small wrapper around Gemini: one structured-JSON call, retried once.

Everything AI in Saathi goes through generate_json(), so tests can replace it
with a fake and the app works (with typing and tapping) when no key is set.
"""
from __future__ import annotations

import json
import logging
import re
import time

from . import settings

log = logging.getLogger("saathi.gemini")


class AINotConfigured(Exception):
    """No GEMINI_API_KEY in .env."""


class AIError(Exception):
    """Gemini failed twice, or kept returning something that isn't the JSON we asked for."""


_client = None


def _get_client():
    global _client
    if not settings.GEMINI_API_KEY:
        raise AINotConfigured()
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def available() -> bool:
    return bool(settings.GEMINI_API_KEY)


def _parse(text: str) -> dict:
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)   # some models wrap JSON in a code fence
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("expected a JSON object")
    return data


def _busy(exc: Exception) -> bool:
    """Rate-limited or overloaded, as opposed to a bad request."""
    return any(code in str(exc) for code in ("429", "RESOURCE_EXHAUSTED", "503", "504", "UNAVAILABLE", "DEADLINE_EXCEEDED"))


# The free tier allows about 20 calls a day per model, so a model that says its daily quota is used up is
# skipped for a while and the next one in the chain is tried.
_spent: dict[str, float] = {}
SPENT_FOR = 3600


def _chain(model: str | None) -> list[str]:
    first = model or settings.GEMINI_MODEL
    names = [first] + [m for m in settings.GEMINI_FALLBACK_MODELS if m != first]
    now = time.monotonic()
    fresh = [m for m in names if _spent.get(m, 0) <= now]
    return fresh or names


def generate_json(prompt: str, schema: dict, *, system: str | None = None, think: bool = False,
                  model: str | None = None, retries: int = 1, audio: tuple[bytes, str] | None = None) -> dict:
    """audio: (bytes, mime type) of a recording Gemini should listen to along with the prompt.

    Each model in the chain gets one try; with a single model it gets 1 + retries tries.
    """
    from google.genai import types

    client = _get_client()
    config = types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json",
        response_json_schema=schema,
        temperature=0.2,
        thinking_config=None if think else types.ThinkingConfig(thinking_budget=0),
    )
    contents = [types.Part.from_bytes(data=audio[0], mime_type=audio[1]), prompt] if audio else prompt
    models = _chain(model)
    tries = models + [models[-1]] * max(0, retries + 1 - len(models))
    last = None
    for attempt, current in enumerate(tries, 1):
        try:
            started = time.monotonic()
            resp = client.models.generate_content(model=current, contents=contents, config=config)
            data = _parse(resp.text)
            log.info("gemini ok (%s) in %.1fs", current, time.monotonic() - started)
            return data
        except (ValueError, json.JSONDecodeError) as exc:
            last = exc
            log.warning("gemini returned unusable JSON (%s, attempt %d): %s", current, attempt, exc)
        except Exception as exc:  # network, 429, 5xx: the SDK raises its own error types
            last = exc
            log.warning("gemini call failed (%s, attempt %d): %s", current, attempt, str(exc)[:200])
            if "PerDay" in str(exc):
                _spent[current] = time.monotonic() + SPENT_FOR
            if not _busy(exc):
                time.sleep(1.0)
    raise AIError(str(last))
