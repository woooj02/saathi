"""Convert the sample PDF with Gemini and save it as the sample's questions (needs GEMINI_API_KEY in .env).

    python scripts/convert_sample.py           ->  samples/pt-intake/form.json (source: gemini)
    python scripts/convert_sample.py --dry-run ->  print a summary, change nothing

The hand-written version stays in scripts/sample_questions.py for comparison.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import converter, settings  # noqa: E402
from app.pdf_reader import read_form  # noqa: E402

FOLDER = settings.SAMPLES_DIR / "pt-intake"

if __name__ == "__main__":
    if not settings.GEMINI_API_KEY:
        sys.exit("Put GEMINI_API_KEY in .env first.")
    read = read_form((FOLDER / "original.pdf").read_bytes())
    result = converter.convert(read)
    current = json.loads((FOLDER / "form.json").read_text())
    form = {**current, **{k: result[k] for k in ("form_title_en", "form_title_ne", "questions", "consent")},
            "source": "gemini", "needs_review": result["needs_review"]}
    asked = [q for q in result["questions"] if q["kind"] not in ("signature", "auto_date", "auto_name", "skip")]
    print(f"{len(result['questions'])} questions ({len(asked)} asked), {len(result['consent'])} consent sections, "
          f"{len(result['needs_review'])} boxes needing review")
    if "--dry-run" in sys.argv:
        print(json.dumps(result, ensure_ascii=False, indent=2)[:4000])
    else:
        (FOLDER / "form.json").write_text(json.dumps(form, ensure_ascii=False, indent=2))
        print(FOLDER / "form.json")
