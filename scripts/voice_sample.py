"""Record the sample form's Nepali read-aloud with Gemini (needs GEMINI_API_KEY in .env).

    python scripts/voice_sample.py   ->  samples/pt-intake/voice/*.mp3

Skips anything already recorded, so it can be run again after the daily quota resets.
Calls are spaced out to stay under the free tier's per-minute limit.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import gemini, settings, store, voice  # noqa: E402

if __name__ == "__main__":
    if not settings.GEMINI_API_KEY:
        sys.exit("Put GEMINI_API_KEY in .env first.")
    form = store.load(store.SAMPLE_ID)
    keys = ["intro", "intro-story", "story"]
    keys += [q["id"] for q in form["questions"] if q["kind"] not in ("signature", "auto_date", "auto_name", "skip")]
    keys += [f"consent-{c['id']}" for c in form["consent"]]
    made = failed = 0
    for key in keys:
        text = voice.text_for(form, key)
        if voice.cached(store.SAMPLE_ID, key, text):
            continue
        try:
            path = voice.recording(store.SAMPLE_ID, key, text)
            made += 1
            print(f"{key}: {path.name}", flush=True)
        except gemini.AIError as exc:
            failed += 1
            print(f"{key}: failed ({str(exc)[:80]})", flush=True)
        time.sleep(13)
    print(f"made {made}, failed {failed}, {len(keys)} in all")
