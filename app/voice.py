"""Voice: each question read aloud in real Nepali (Gemini text-to-speech), made once and kept.

Devices rarely have a Nepali voice (Linux Chrome only has Hindi), so the patient page plays
these recordings and falls back to the device's voice only when there's no recording and no AI.
A recording is named after a hash of its text, so when the clinic rewords a question the next
patient gets a fresh one. The sample form's recordings are committed, so it needs no AI.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import wave
from io import BytesIO
from pathlib import Path

from . import gemini, settings, store

STYLE = ("Read the following aloud in natural, warm, clear Nepali, at a calm pace, like a kind clinic helper talking "
         "to an older person. Read only the text, nothing else:")

# The screens' own lines, read from the same file the page uses, so the two can't drift apart.
_UI_LINES = {"intro": ("introTitle", "introBody"), "intro-story": ("introTitle", "introBodyStory"),
             "story": ("storyTitle", "storyBody")}


def _ui_text(key: str) -> str | None:
    parts = _UI_LINES.get(key)
    if not parts:
        return None
    source = (settings.WEB_DIR / "js" / "nepali.js").read_text(encoding="utf-8")
    ne = source[source.index("ne: {"):source.index("en: {")]
    found = [re.search(rf'\b{p}: "([^"]*)"', ne) for p in parts]
    return "। ".join(m.group(1) for m in found if m) or None


def text_for(form: dict, key: str) -> str | None:
    """The Nepali text a key stands for: a question id, consent-<id>, or one of the screens' lines."""
    q = next((q for q in form["questions"] if q["id"] == key), None)
    if q:
        return q["ne"]
    if key.startswith("consent-"):
        c = next((c for c in form.get("consent", []) if c["id"] == key[len("consent-"):]), None)
        return c and f"{c['title_ne']}। {c['ne']}"
    return _ui_text(key)


def _path(form_id: str, key: str, text: str) -> Path:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
    safe = re.sub(r"[^a-z0-9_-]", "_", key.lower())[:60]
    return store._folder(form_id) / "voice" / f"{safe}-{digest}"


def cached(form_id: str, key: str, text: str) -> Path | None:
    base = _path(form_id, key, text)
    return next((p for p in (base.with_suffix(".mp3"), base.with_suffix(".wav")) if p.exists()), None)


def has_any(form_id: str) -> bool:
    folder = store._folder(form_id) / "voice"
    return folder.is_dir() and any(folder.iterdir())


def _encode(pcm: bytes) -> tuple[bytes, str]:
    """24 kHz 16-bit mono PCM -> MP3 if ffmpeg is installed (about 10x smaller), else WAV."""
    if shutil.which("ffmpeg"):
        out = subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", "pipe:0",
             "-codec:a", "libmp3lame", "-b:a", "48k", "-f", "mp3", "pipe:1"],
            input=pcm, capture_output=True, check=True)
        return out.stdout, ".mp3"
    buf = BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)
    return buf.getvalue(), ".wav"


def recording(form_id: str, key: str, text: str) -> Path:
    """The recording for this text, made with Gemini the first time. Raises gemini.AIError / AINotConfigured."""
    found = cached(form_id, key, text)
    if found:
        return found
    data, suffix = _encode(gemini.speech_pcm(text, style=STYLE))
    path = _path(form_id, key, text).with_suffix(suffix)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path
