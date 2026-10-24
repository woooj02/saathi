"""Fill the sample form with made-up answers -> data/outbox/sample-filled.pdf (a quick look at the output)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import settings  # noqa: E402
from app.filler import fill_pdf  # noqa: E402

EXAMPLE = {
    "last_name": "Neupane", "first_name": "Kamala", "date_of_birth": "04/14/1965", "sex": "Female",
    "phone": "(303) 555-0142", "preferred_language": "Nepali", "needs_interpreter": "Yes",
    "address_street": "1450 Example Street, Apt 12", "address_city": "Aurora", "address_state": "CO",
    "address_zip": "80010", "emergency_name": "Ram Neupane", "emergency_relationship": "Son",
    "injury_date": "01/05/2026", "accident_type": "Fall", "seen_er": "No",
    "injury_description": "I slipped on ice in the parking lot at work and fell on my right side.",
    "pain_lower_back": True, "pain_hip": True, "pain_now": "7", "pain_pattern": "Constant",
    "medications": "Amlodipine 5 mg once a day", "insurance_member_id": "Patient will provide at visit",
    "signature_date": "10/24/2026", "printed_name": "Kamala Neupane",
}

if __name__ == "__main__":
    original = (settings.SAMPLES_DIR / "pt-intake" / "original.pdf").read_bytes()
    out = settings.OUTBOX_DIR / "sample-filled.pdf"
    out.write_bytes(fill_pdf(original, EXAMPLE, {"field": "patient_signature", "name": "Kamala Neupane"}))
    print(out)
