"""Generate the sample intake form used for demos and tests.

An original, fictional 5-page physical therapy intake for a new patient after an
accident, with real fillable boxes (text, checkboxes, radio groups and a
signature line), laid out the way clinic forms usually are: labels above text
boxes, option labels to the right of checkboxes, and consent paragraphs at the end.

    python scripts/make_sample_form.py  ->  samples/pt-intake/original.pdf

Drawn with reportlab, whose AcroForm support writes standard radio groups (one
field, one export value per button), like the forms clinics actually send.
Coordinates below are measured from the top of the page, as on paper.
"""
from pathlib import Path

from reportlab.lib.colors import black, white, Color
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

OUT = Path(__file__).resolve().parent.parent / "samples" / "pt-intake" / "original.pdf"

W, H = 612, 792          # US Letter
LEFT, RIGHT = 54, 558
BOX_H = 18


GREY = Color(0.96, 0.96, 0.96)


def text_width(text, size, bold=False):
    return stringWidth(text, "Helvetica-Bold" if bold else "Helvetica", size)


class Form:
    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.c = Canvas(str(path), pagesize=(W, H))
        self.c.setTitle("Riverbend Physical Therapy - New Patient Intake (sample)")
        self.form = self.c.acroForm
        self.y = 0
        self.page_no = 0

    # reportlab measures from the bottom; everything here is from the top.
    def _text(self, x, y, text, size=9, bold=False):
        self.c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        self.c.drawString(x, H - y, text)

    def _line(self, x1, y1, x2, y2, width=0.5):
        self.c.setLineWidth(width)
        self.c.line(x1, H - y1, x2, H - y2)

    # -- page furniture -----------------------------------------------------

    def new_page(self, title):
        if self.page_no:
            self.c.showPage()
        self.page_no += 1
        self._text(LEFT, 40, "RIVERBEND PHYSICAL THERAPY", 9, bold=True)
        self._text(LEFT, 52, "New Patient Intake: Accident / Injury", 9)
        self._text(RIGHT - 150, 40, "SAMPLE FORM, FICTIONAL CLINIC", 8, bold=True)
        self._text(RIGHT - 40, 52, f"Page {self.page_no} of 5", 8)
        self._line(LEFT, 60, RIGHT, 60, 0.6)
        self._text(LEFT, 90, title, 15, bold=True)
        self.y = 112

    def section(self, text):
        self.y += 8
        self._text(LEFT, self.y, text.upper(), 10.5, bold=True)
        self._line(LEFT, self.y + 4, RIGHT, self.y + 4, 0.4)
        self.y += 20

    def note(self, text, size=8.5):
        """A wrapped paragraph."""
        words, line, lines = text.split(), "", []
        for w in words:
            trial = f"{line} {w}".strip()
            if text_width(trial, size) > RIGHT - LEFT:
                lines.append(line)
                line = w
            else:
                line = trial
        lines.append(line)
        for ln in lines:
            self._text(LEFT, self.y + size, ln, size)
            self.y += size * 1.35
        self.y += 10

    # -- fields -------------------------------------------------------------

    def text_row(self, *cols, multiline_lines=1):
        """A row of labelled text boxes. cols = (label, name, width_fraction)."""
        x = LEFT
        total = RIGHT - LEFT
        gap = 10
        n = len(cols)
        box_h = BOX_H if multiline_lines == 1 else 13 * multiline_lines + 6
        for label, name, frac in cols:
            width = total * frac - (gap * (n - 1) / n)
            self._text(x, self.y, label, 8.5)
            top = self.y + 4
            self.form.textfield(
                name=name, tooltip=label, x=x, y=H - top - box_h, width=width, height=box_h,
                borderWidth=0.6, borderColor=black, fillColor=GREY, textColor=black,
                forceBorder=True, fontName="Helvetica", fontSize=9,
                fieldFlags="multiline" if multiline_lines > 1 else "")
            x += width + gap
        self.y += box_h + 22

    def radio_row(self, prompt, name, options, inline_prompt=True):
        """A prompt followed by radio buttons, each with its label to the right."""
        x = LEFT
        self._text(x, self.y + 9, prompt, 9)
        if inline_prompt:
            x += text_width(prompt, 9) + 14
        else:
            self.y += 18
        for label, value in options:
            if x + 30 + text_width(label, 9) > RIGHT:
                self.y += 18
                x = LEFT + 14
            self.form.radio(
                name=name, tooltip=prompt, value=value, selected=False, x=x, y=H - self.y - 11,
                size=11, buttonStyle="circle", shape="circle", borderWidth=0.6, borderColor=black, fillColor=white,
                textColor=black, forceBorder=True)
            self._text(x + 15, self.y + 9, label, 9)
            x += 15 + text_width(label, 9) + 16
        self.y += 32

    def checkbox_grid(self, prompt, items, columns=3):
        """A prompt line, then checkboxes in columns, labels to the right."""
        self._text(LEFT, self.y + 9, prompt, 9)
        self.y += 20
        col_w = (RIGHT - LEFT) / columns
        for i, (label, name) in enumerate(items):
            col, row = i % columns, i // columns
            x = LEFT + 14 + col * col_w
            y = self.y + row * 18
            self.form.checkbox(
                name=name, tooltip=label, x=x, y=H - y - 11, size=11, buttonStyle="check", shape="square",
                borderWidth=0.6, borderColor=black, fillColor=white, textColor=black, forceBorder=True)
            self._text(x + 15, y + 9, label, 9)
        rows = (len(items) + columns - 1) // columns
        self.y += rows * 18 + 12

    def save(self):
        self.c.save()


def _circle(r, cx, cy, op):
    k = 0.5523 * r
    return (f"{cx + r:.3f} {cy:.3f} m {cx + r:.3f} {cy + k:.3f} {cx + k:.3f} {cy + r:.3f} {cx:.3f} {cy + r:.3f} c "
            f"{cx - k:.3f} {cy + r:.3f} {cx - r:.3f} {cy + k:.3f} {cx - r:.3f} {cy:.3f} c "
            f"{cx - r:.3f} {cy - k:.3f} {cx - k:.3f} {cy - r:.3f} {cx:.3f} {cy - r:.3f} c "
            f"{cx + k:.3f} {cy - r:.3f} {cx + r:.3f} {cy - k:.3f} {cx + r:.3f} {cy:.3f} c {op}\n")


def fix_radio_appearances(path):
    """reportlab draws radio circles at about half size in the box corner; redraw them centred."""
    import pymupdf

    doc = pymupdf.open(path)
    for page in doc:
        for w in page.widgets():
            if w.field_type != pymupdf.PDF_WIDGET_TYPE_RADIOBUTTON:
                continue
            size = w.rect.width
            c, r = size / 2, size / 2 - 0.6
            ring = "q 1 1 1 rg 0 0 0 RG 0.6 w " + _circle(r, c, c, "B") + "Q\n"
            dot = "q 0 0 0 rg " + _circle(r * 0.45, c, c, "f") + "Q\n"
            for state in ("N", "D"):
                for key, extra in (("Off", ""), (w.on_state(), dot)):
                    ref = doc.xref_get_key(w.xref, f"AP/{state}/{key}")
                    if ref[0] == "xref":
                        doc.update_stream(int(ref[1].split()[0]), (ring + extra).encode())
    doc.saveIncr()


YES_NO = [("Yes", "Yes"), ("No", "No")]
SCALE = [(str(i), str(i)) for i in range(11)]


def build():
    f = Form(OUT)

    # Page 1 -------------------------------------------------------------
    f.new_page("Patient Information")
    f.note("Please complete every page before your first visit. If a question does not apply to you, leave it blank. "
           "Bring your photo ID and insurance card to your appointment.")
    f.section("About you")
    f.text_row(("Last name", "last_name", 0.4), ("First name", "first_name", 0.4), ("Middle initial", "middle_initial", 0.2))
    f.text_row(("Date of birth (MM/DD/YYYY)", "date_of_birth", 0.35), ("Phone number", "phone", 0.35), ("Preferred language", "preferred_language", 0.3))
    f.radio_row("Sex:", "sex", [("Male", "Male"), ("Female", "Female"), ("Prefer not to say", "Undisclosed")])
    f.text_row(("Street address", "address_street", 1.0))
    f.text_row(("City", "address_city", 0.5), ("State", "address_state", 0.2), ("ZIP code", "address_zip", 0.3))
    f.text_row(("Email address", "email", 0.6), ("Occupation", "occupation", 0.4))
    f.radio_row("Do you need an interpreter for your visits?", "needs_interpreter", YES_NO)
    f.section("Emergency contact")
    f.text_row(("Emergency contact name", "emergency_name", 0.45), ("Relationship to you", "emergency_relationship", 0.25), ("Phone number", "emergency_phone", 0.3))

    # Page 2 -------------------------------------------------------------
    f.new_page("Accident and Injury Details")
    f.section("The accident")
    f.text_row(("Date of injury (MM/DD/YYYY)", "injury_date", 0.4), ("Time of day (approximate)", "injury_time", 0.3), ("City where it happened", "injury_city", 0.3))
    f.radio_row("Type of accident:", "accident_type", [
        ("Motor vehicle", "MotorVehicle"), ("At work", "Work"), ("Slip or fall", "Fall"),
        ("Sports", "Sports"), ("Other", "Other")])
    f.text_row(("Describe in your own words how the injury happened", "injury_description", 1.0), multiline_lines=4)
    f.section("Care so far")
    f.radio_row("Did you go to an emergency room or urgent care?", "seen_er", YES_NO)
    f.radio_row("Have you seen another doctor for this injury?", "seen_other_doctor", YES_NO)
    f.text_row(("Referring doctor's name", "referring_doctor", 0.6), ("Doctor's phone", "referring_doctor_phone", 0.4))
    f.radio_row("Have you had an X-ray, MRI, or CT scan for this injury?", "had_imaging", YES_NO)
    f.section("Claims")
    f.radio_row("Is this injury related to your job (workers' compensation)?", "workers_comp", YES_NO)
    f.radio_row("Is an attorney representing you for this injury?", "has_attorney", YES_NO)
    f.text_row(("Attorney name and phone (if any)", "attorney_contact", 1.0))

    # Page 3 -------------------------------------------------------------
    f.new_page("Insurance")
    f.section("Health insurance")
    f.text_row(("Insurance company", "insurance_company", 0.5), ("Member ID", "insurance_member_id", 0.3), ("Group number", "insurance_group", 0.2))
    f.text_row(("Policy holder's full name", "policy_holder_name", 0.6), ("Policy holder's date of birth", "policy_holder_dob", 0.4))
    f.radio_row("Policy holder's relationship to patient:", "policy_holder_relationship", [
        ("Self", "Self"), ("Spouse", "Spouse"), ("Parent", "Parent"), ("Other", "Other")])
    f.section("Accident claim (if any)")
    f.text_row(("Auto insurance company", "auto_insurance_company", 0.5), ("Auto claim number", "auto_claim_number", 0.5))
    f.text_row(("Workers' compensation claim number", "wc_claim_number", 0.5), ("Employer name", "employer_name", 0.5))
    f.note("We will bill your insurance as a courtesy. You are responsible for any balance your insurance does not pay. "
           "Please tell the front desk right away if your insurance changes.")

    # Page 4 -------------------------------------------------------------
    f.new_page("Pain and Medical History")
    f.section("Your pain")
    f.checkbox_grid("Where is your pain? (check all that apply)", [
        ("Head", "pain_head"), ("Neck", "pain_neck"), ("Upper back", "pain_upper_back"),
        ("Lower back", "pain_lower_back"), ("Shoulder", "pain_shoulder"), ("Arm or elbow", "pain_arm"),
        ("Wrist or hand", "pain_hand"), ("Hip", "pain_hip"), ("Knee", "pain_knee"),
        ("Ankle or foot", "pain_foot")])
    f.radio_row("Rate your pain right now (0 = no pain, 10 = worst pain):", "pain_now", SCALE, inline_prompt=False)
    f.radio_row("Is your pain constant, or does it come and go?", "pain_pattern", [
        ("Constant", "Constant"), ("Comes and goes", "Intermittent")])
    f.text_row(("What makes your pain worse?", "pain_worse", 1.0))
    f.text_row(("What do you hope to be able to do again after therapy?", "therapy_goals", 1.0))
    f.section("Medical history")
    f.checkbox_grid("Do you have, or have you had, any of these? (check all that apply)", [
        ("High blood pressure", "hx_high_bp"), ("Diabetes", "hx_diabetes"), ("Heart disease", "hx_heart"),
        ("Asthma", "hx_asthma"), ("Arthritis", "hx_arthritis"), ("Osteoporosis", "hx_osteoporosis"),
        ("Cancer", "hx_cancer"), ("Pacemaker", "hx_pacemaker"), ("Currently pregnant", "hx_pregnant")])
    f.text_row(("Current medications (name and dose)", "medications", 1.0), multiline_lines=2)
    f.text_row(("Allergies (medicines, latex, foods)", "allergies", 0.6), ("Past surgeries", "past_surgeries", 0.4))

    # Page 5 -------------------------------------------------------------
    f.new_page("Consent and Signature")
    f.section("Consent to evaluation and treatment")
    f.note("I agree to an evaluation and physical therapy treatment by the licensed therapists of Riverbend Physical "
           "Therapy. Treatment may include exercise, manual therapy, heat, ice, and electrical stimulation. My "
           "therapist will explain the plan of care, and I may ask questions or stop treatment at any time. I "
           "understand that results are not guaranteed.", size=9)
    f.section("Privacy notice acknowledgement (HIPAA)")
    f.note("I acknowledge that I have been offered a copy of the clinic's Notice of Privacy Practices, which explains "
           "how my health information may be used and shared for treatment, payment, and health care operations, "
           "and my rights to access and correct my records.", size=9)
    f.section("Financial responsibility and cancellations")
    f.note("I authorize the clinic to bill my insurance and to receive payment directly. I am responsible for "
           "copays, deductibles, and any amount my insurance does not cover. I will give at least 24 hours' notice "
           "to cancel an appointment, or a $35 missed-visit fee may apply.", size=9)
    f.y += 6
    f.text_row(("Patient signature", "patient_signature", 0.65), ("Date", "signature_date", 0.35))
    f.text_row(("Printed name", "printed_name", 0.65), ("If signed by someone else, relationship", "signer_relationship", 0.35))

    f.save()
    fix_radio_appearances(OUT)
    return OUT


if __name__ == "__main__":
    print(build())
