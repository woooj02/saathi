import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
# tests never touch the real data folder or send real email
os.environ["SAATHI_DATA_DIR"] = tempfile.mkdtemp(prefix="saathi-test-")
os.environ["MAIL_MODE"] = "file"
os.environ["GEMINI_API_KEY"] = ""
# the sample PDF with the hand-written questions, so tests don't change when the sample is re-converted
_samples = Path(tempfile.mkdtemp(prefix="saathi-samples-"))
(_samples / "pt-intake").mkdir()
shutil.copy(ROOT / "samples" / "pt-intake" / "original.pdf", _samples / "pt-intake")
shutil.copy(ROOT / "tests" / "fixtures" / "sample-form.json", _samples / "pt-intake" / "form.json")
os.environ["SAATHI_SAMPLES_DIR"] = str(_samples)

import pytest  # noqa: E402

SAMPLE_PDF = ROOT / "samples" / "pt-intake" / "original.pdf"


@pytest.fixture
def sample_pdf() -> bytes:
    return SAMPLE_PDF.read_bytes()
