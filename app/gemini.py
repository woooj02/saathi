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


def generate_json(prompt: str, schema: dict, *, system: str | None = None, think: bool = False,
                  model: str | None = None, retries: int = 1) -> dict:
    from google.genai import types

    client = _get_client()
    config = types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json",
        response_json_schema=schema,
        temperature=0.2,
        thinking_config=None if think else types.ThinkingConfig(thinking_budget=0),
    )
    current = model or settings.GEMINI_MODEL
    last = None
    for attempt in range(retries + 1):
        try:
            started = time.monotonic()
            resp = client.models.generate_content(model=current, contents=prompt, config=config)
            data = _parse(resp.text)
            log.info("gemini ok in %.1fs", time.monotonic() - started)
            return data
        except (ValueError, json.JSONDecodeError) as exc:
            last = exc
            log.warning("gemini returned unusable JSON (attempt %d): %s", attempt + 1, exc)
        except Exception as exc:  # network, 429, 5xx: the SDK raises its own error types
            last = exc
            log.warning("gemini call failed (attempt %d): %s", attempt + 1, str(exc)[:200])
            if _busy(exc) and settings.GEMINI_FALLBACK_MODEL and current != settings.GEMINI_FALLBACK_MODEL:
                current = settings.GEMINI_FALLBACK_MODEL   # the free tier's per-minute limit is per model
                continue
            time.sleep(1.5 * (attempt + 1))
    raise AIError(str(last))
