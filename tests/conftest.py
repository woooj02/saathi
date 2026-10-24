import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
# tests never touch the real data folder or send real email
os.environ["SAATHI_DATA_DIR"] = tempfile.mkdtemp(prefix="saathi-test-")
os.environ["MAIL_MODE"] = "file"
os.environ["GEMINI_API_KEY"] = ""

import pytest  # noqa: E402

SAMPLE_PDF = ROOT / "samples" / "pt-intake" / "original.pdf"


@pytest.fixture
def sample_pdf() -> bytes:
    return SAMPLE_PDF.read_bytes()
