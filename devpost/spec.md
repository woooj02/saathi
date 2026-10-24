---
doc: spec
status: approved
---

# Saathi — Technical Spec

## How This Works, In Plain Language
Saathi is one small Python web server on your laptop. It serves two sets of pages, one for the clinic and one for
the patient.

- **The clinic uploads its PDF.** The server opens the PDF with a library called PyMuPDF and lists every fillable
  box: what kind of box it is, where it is on the page, and the printed words next to it. That part needs no AI.
  The server sends that list to **Gemini** (Google's AI, free tier) once, and Gemini writes a plain English and a
  plain Nepali question for each box. Gemini also writes a Nepali explanation of each consent paragraph. The result
  is saved as one file next to the PDF. The clinic checks and edits the wording, then publishes.
- **The patient opens the link on their phone.** The page asks each question in Nepali and reads it aloud with the
  device's own voice. The patient speaks, the page records a short clip, and **Gemini listens to it** and writes
  both the Nepali it heard and the English for the form, in one call. (Chrome's built-in recognition was the first
  plan, but it returned nothing for Nepali on the learner's machine; see `Decisions and Open Issues`.) Yes/no,
  choice, scale and date questions need no AI. Only spoken or Nepali-typed answers go to Gemini. For dates, Gemini only works out what date was said; plain code then
  converts Nepali-calendar dates to English dates, so the conversion is exact. The answers wait on the phone (a sticky
  note the browser keeps for this site) until the patient sends.
- **When the patient sends,** the server writes the English answers and the typed signature into the clinic's
  original PDF and emails it to the clinic from Keepsrunning's Zoho account. The patient gets the same PDF as a
  download. The server doesn't keep the answers afterwards.

Why this shape: one server, one AI service, no database and no logins. Every part that doesn't need AI is plain
code, and the AI is called only where it really helps: understanding a form, and understanding free speech.

## The Core Journey Through the System
PRD ref: `prd.md > The Core Journey`.

1. The clinic fills in its name and email and picks its PDF on `/clinic`. The browser sends them to
   `POST /api/forms`. → `Form Reader` lists the boxes and nearby text. → `Form Converter` asks Gemini for the
   questions. → `Form Store` saves `data/forms/<id>/form.json` and `original.pdf`. → The clinic sees the
   question review list.
2. The clinic edits wording, which calls `PATCH /api/forms/<id>`, then presses Publish, which calls
   `POST /api/forms/<id>/publish`. → The clinic sees the patient link `/f/<id>` and a copy button.
3. The patient opens `/f/<id>`. The browser loads the published form with `GET /api/forms/<id>`. → Welcome, then
   the language choice, then the intro.
4. On each question, `Voice` reads the Nepali text aloud. The patient taps the mic, and `Voice` records until they
   pause.
   - For **text and name** answers, the browser sends the clip to `POST /api/forms/<id>/interpret-audio` (typed
     Nepali goes to `POST /api/forms/<id>/interpret`). → `Answer Interpreter`
     (Gemini) returns Nepali and English. → The "both sides" card appears.
   - For **dates**, the same call returns the date that was said. → `Nepali Dates` converts it to an English date.
     → The "both sides" card appears.
   - **Yes/no, choice and scale** answers are mapped in the browser directly, with no server call.
   - The answer is saved to the phone's local storage.
5. The patient reviews, ticks the consent box and types their name. The browser sends all answers to
   `POST /api/forms/<id>/submit`. → `PDF Filler` writes them into `original.pdf`. → `Mailer` emails it, or saves it
   to `data/outbox/` in file mode. → The response returns the filled PDF. → The Sent screen offers it as a download,
   and local storage is cleared.

## Stack
Agreed with the learner: Python and FastAPI as in Memory Lane, PyMuPDF, and plain HTML/CSS/JS with no build step.
Gemini's free tier instead of Together; "use 0 credit from Together". Zoho for email.

- **Python 3.12, FastAPI, Uvicorn.** The learner already used them in Memory Lane.
  https://fastapi.tiangolo.com/
- **PyMuPDF (`pymupdf`)** reads fillable boxes ("widgets"), their types, positions and nearby words, and writes
  values and the signature back. https://pymupdf.readthedocs.io/en/latest/widget.html
- **Google Gen AI SDK (`google-genai`)** for Gemini, with structured JSON output.
  https://ai.google.dev/gemini-api/docs/structured-output
  - Model: `GEMINI_MODEL`, default `gemini-3.6-flash` (2.5 Flash is closed to new keys; 3.7 and 3.8 Flash timed out on 2026-10-24).
  - **Unverified:** the current model names and free-tier limits. Google's own pages disagree, so check the live
    limits in AI Studio in build step 1. https://ai.google.dev/gemini-api/docs/rate-limits
- **`nepali-datetime`** converts Bikram Sambat (Nepali calendar) dates to Gregorian dates.
  https://pypi.org/project/nepali-datetime/
- **Browser audio.** `MediaRecorder` records the answer (WebM/Opus in Chrome), and `speechSynthesis` reads aloud.
  https://developer.mozilla.org/docs/Web/API/MediaRecorder ·
  https://developer.mozilla.org/docs/Web/API/Web_Speech_API (`SpeechRecognition` is now only used by `/lab`).
- **Python's built-in `smtplib`** for Zoho SMTP. https://www.zoho.com/mail/help/zoho-smtp.html
- **Fonts:** Inter for Latin text, Noto Sans Devanagari for Nepali, and a handwriting-style font (Dancing Script, open
  licence) for the signature. All are bundled locally in `web/fonts/` so the app works offline.

## Where It Runs and How Someone Tries It
- **Runs locally:** `./run.sh` installs requirements into `.venv` if needed and starts Uvicorn on
  http://localhost:8010.
  - `/clinic` is the clinic side.
  - `/f/<id>` is the patient side.
  - `/f/sample` is the pre-converted sample form.
- **Needs Python 3.12 and a modern browser.** Recording needs a secure origin; `localhost` counts.
- **Keys, in `.env`, which the learner fills in.** They are never pasted in chat. `.env.example` lists them:
  - `GEMINI_API_KEY`, and optionally `GEMINI_MODEL`.
  - `MAIL_MODE=file|send`. The default is `file`.
  - `SMTP_HOST` (default `smtppro.zoho.com`), `SMTP_PORT=465`, `SMTP_USER`, `SMTP_PASSWORD` (a Zoho app password),
    `MAIL_FROM`.
  - `MIN_SEND_GAP_SECONDS=300`.
- **Recording:** Chrome on the laptop. Use DevTools device mode at phone size for the patient side, and a normal
  window for the clinic side and the inbox.
- **Deployment:** optional, decided in `6-ship`. Submission needs the video and the public GitHub repo regardless.

## Look and Feel
Carried from `prd.md > Look and Feel` and `scope.md > Inspiration & Identity`.
- **Colour:** pure black `#000` on white `#fff`, with greys only for secondary text and borders. One accent for
  "skipped" states only: a thin black dashed outline rather than a colour, to stay monochrome.
- **Type:** Inter for English and Noto Sans Devanagari for Nepali.
  - Patient side: questions at 28–32px, body at 20px or more, line height 1.5.
  - Clinic side: a normal 16px.
- **Layout:** the patient side is phone first, with one question per screen and full-width buttons at least 64px
  tall. The clinic side is a calm single column, with a maximum width of about 880px.
- **Feel:** lots of white space, square corners or a 12px radius, no shadows, no gradients and no emoji. Motion is a
  subtle fade or slide between questions.
- **Numbers:** Nepali numerals (०–९) on the patient side, using `toNepaliDigits()`.
- **Tone:** short, warm Nepali, addressing the patient as तपाईं. The clinic side uses plain English.

## Components

### Form Reader
`app/pdf_reader.py`. Opens the PDF with PyMuPDF and returns a list of fields.
- Each field has its name, type (text, checkbox, radio group, choice list or signature), page, rectangle, current
  options, and a **label**. The label comes from words on the same line to the left of the box, or just above it.
- It also returns **section headings** (larger or bold lines) and **long paragraphs** (consent text).
- A PDF with no widgets raises `NotFillable`.
PRD ref: `prd.md > Clinic Setup and Conversion`, `prd.md > States and Boundaries` ("Not a fillable PDF").

### Form Converter
`app/converter.py`. Sends Gemini the reader's output once and asks for JSON matching a schema. Each question gets:
- an id, the field name(s) it covers, and its kind: text, name, date, yes/no, choice, scale, signature or skip-auto
- English and Nepali wording, options with English and Nepali labels, and its section in English and Nepali
- `consent` blocks, with their English text and a plain Nepali explanation

Radio groups become one choice question. A run of checkboxes under one label becomes one multi-choice question.
Auto-filled boxes such as "Today's date" are marked skip-auto. The code checks that every field is covered exactly
once and retries once if the JSON is invalid.
PRD ref: `prd.md > Clinic Setup and Conversion`.

### Form Store
`app/store.py`. Works with folders under `data/forms/<id>/`, each holding `original.pdf` and `form.json`.
- `form.json` holds the clinic name and email, the status (draft or published), the questions and the consent
  blocks.
- `samples/pt-intake/` holds the sample form and its saved conversion, served as id `sample`. Testing and recording
  the patient flow therefore cost no AI calls.
PRD ref: `prd.md > Clinic Setup and Conversion`.

### Answer Interpreter
`app/answers.py`. Handles `POST /api/forms/<id>/interpret` with `{question_id, transcript_ne}`.
- Asks Gemini, with the question in both languages as context, for:
  - `{ok, ne_clean, en}` for text answers
  - `{ok, ne_clean, en_latin}` for names, spelled in English letters
  - `{ok, calendar: "BS"|"AD", year, month, day}` for dates
- `ok: false` means Saathi didn't understand. The PRD's "say it again" path follows.
- Dates go through `Nepali Dates`. The English is never shown before the patient confirms the both-sides card.
PRD ref: `prd.md > Answering a Question`, `prd.md > Not Sure or Misunderstood`.

### Story
`app/story.py`. Handles `POST /api/forms/<id>/story` with one recording (multipart `audio`).
- One Gemini call (with thinking) gets the recording and every question that can be answered by voice, with each
  question's answer type and, for taps, its option values. The JSON schema is built from the form, so the reply can
  only name real questions and real option values.
- Every answer is then checked like a single answer: typed kinds through `Answer Interpreter`'s checks, dates through
  `Nepali Dates`, taps against the PDF's option values. Anything that doesn't hold up is dropped.
- Returns `{said, answers: {question_id: {value, said, en, parts?, story: true}}}`.
PRD ref: `prd.md > Telling the Story Once`.

### Read-Aloud Recordings
`app/voice.py`. Handles `GET /api/forms/<id>/voice/<key>` (a question id, `consent-<id>`, or a screen's line).
- The first request records the Nepali text with Gemini text-to-speech (`GEMINI_TTS_MODELS`, voice "Kore"), encodes it
  to MP3 with ffmpeg (WAV without it) and keeps it next to the form, named by a hash of the text. Reworded text gets a
  new recording.
- 404 means "use the device's voice". The sample form's recordings are committed (`scripts/voice_sample.py`).
PRD ref: `prd.md > Answering a Question`.

### Nepali Dates
`app/nepali_dates.py`. Converts a BS date to AD with `nepali-datetime`, and formats it the way the form expects
(MM/DD/YYYY by default). Unit-tested with known pairs.
PRD ref: `prd.md > Answering a Question` (Nepali-calendar dates).

### PDF Filler
`app/filler.py`. Writes the answers into a copy of `original.pdf`:
- text values, checkbox on-states and radio selections
- "Patient will provide at visit" for skipped answers
- today's date into date boxes marked skip-auto
- the typed full name drawn in the signature font inside the signature box, with the date beside it

It returns the PDF bytes.
PRD ref: `prd.md > Consent and Signature`, `prd.md > Sending the Form`.

### Mailer
`app/mailer.py`. Builds an email to the clinic: the subject is "Intake form: <patient name>", the body lists any
skipped fields, and the filled PDF is attached.
- `MAIL_MODE=file` (the default) writes an `.eml` file to `data/outbox/`.
- `MAIL_MODE=send` sends through Zoho SMTP over SSL. It refuses to send again within `MIN_SEND_GAP_SECONDS` of the
  last send, as the learner asked for sends "5-10 minutes apart". The patient's PDF download still works in that
  case.
PRD ref: `prd.md > Sending the Form`.

### Web Server
`app/main.py`. FastAPI routes:
- `GET /clinic`, `GET /f/{id}` and `GET /` serve the pages. `/` sends people to `/clinic`.
- `POST /api/forms` takes a multipart upload (`clinic_name`, `clinic_email`, `pdf`) and returns the form JSON.
- `GET /api/forms/{id}` returns the form JSON. For patients, only published forms are returned; otherwise it returns
  404.
- `PATCH /api/forms/{id}` saves edits to question wording.
- `POST /api/forms/{id}/publish` returns `{link}`.
- `POST /api/forms/{id}/interpret` (see `Answer Interpreter`).
- `POST /api/forms/{id}/submit` takes `{answers: {question_id: value|"__skip__"}, signer_name}` and returns
  `application/pdf`, with an `X-Mail-Status` header of `sent`, `saved` or `deferred`.

### Clinic Pages
`web/clinic.html` and `web/js/clinic.js`. There are three states on one page: setup, then reviewing, then the link.
- Setup has a converting progress state.
- The review list is grouped by section. Each row shows the English label, an editable English question, an editable
  Nepali question and the answer type.
- Errors are shown inline: not a PDF, not fillable, or conversion failed with a retry button.
PRD ref: `prd.md > Clinic Setup and Conversion`, `prd.md > Screens and Layout`.

### Patient Pages
`web/fill.html` and `web/js/fill.js`. A single page that moves between screens: welcome, language, intro, questions,
review, consent and sign, then sent.
- Progress shows as प्रश्न ३ / ४२.
- Answer controls depend on the question kind.
- The both-sides card, the skip button ("थाहा छैन / पछि दिन्छु") and Back.
- Answers are saved to `localStorage["saathi:<id>"]` after every confirm.
- The review list and the consent cards.
- A live signature preview in the signature font.
- The Sent screen with a download button.
PRD ref: `prd.md > Answering a Question`, `prd.md > Review`, `prd.md > Consent and Signature`,
`prd.md > Not Sure or Misunderstood`.

### Voice
`web/js/voice.js`.
- `recordAnswer({onLevel})` records one answer with `MediaRecorder`. A level bar shows the mic hears the patient.
  It stops by itself 1.8 s after they stop talking (or when the mic is tapped again), and rejects with `no-speech`
  if nothing louder than the room was heard within 8 s, or `not-allowed` / `audio-capture`.
- `listen()` wraps `SpeechRecognition` (ne-NP). Only the `/lab` test page uses it now.
- `speak(text)` picks a `ne-NP` voice, then a `hi-*` voice as a fallback, since it reads Devanagari. If there is
  none, the speaker button is hidden.
- If recording is unsupported or AI is off, the mic button is hidden and the type option becomes primary.
PRD ref: `prd.md > Answering a Question`, `prd.md > States and Boundaries` ("Microphone blocked").

### Sample Form
`scripts/make_sample_form.py` uses PyMuPDF to generate `samples/pt-intake/original.pdf`. It's a realistic,
original, 5-page fillable "Physical Therapy — New Patient / Accident Intake" form, with:
- patient info and an emergency contact
- accident details: date, how it happened, and work or auto
- insurance, including claim numbers
- pain: location checkboxes and a 0–10 radio scale
- medical history, medications and allergies
- consent and HIPAA acknowledgement paragraphs, and a signature box

It's labelled as a sample, with made-up answers in demos. Its conversion is saved once into
`samples/pt-intake/form.json`.
PRD ref: `prd.md > Product Decisions` (sample form assumption).

## Data Model
- **`form.json`, saved per form on the laptop:**
  `{id, clinic_name, clinic_email, status, created_at, questions: [{id, fields: [..], kind, en, ne, section_en, section_ne, options: [{value, en, ne}], required}], consent: [{id, en, ne}]}`.
  - Created by the upload and updated by clinic edits and publish.
  - It stays until deleted, and survives restarts.
- **Patient answers, in the phone's local storage:**
  `{lang, index, answers: {question_id: {value, ne, en}}, skipped: [..], signer_name}`.
  - Updated after every confirm, and survives a reload.
  - Cleared after a successful submit.
- **The filled PDF:** built in memory on submit, then emailed or written to `data/outbox/` and returned to the phone.
  It isn't stored otherwise. `data/` is gitignored.

## File Structure
```
build-with-ai/
├── app/
│   ├── main.py            # FastAPI routes and static pages
│   ├── settings.py        # reads .env (Gemini, mail mode, Zoho)
│   ├── pdf_reader.py      # Form Reader: widgets, labels, sections, paragraphs
│   ├── converter.py       # Form Converter: one Gemini call → questions JSON
│   ├── gemini.py          # small wrapper: structured JSON call, one retry
│   ├── answers.py         # Answer Interpreter: spoken Nepali → English
│   ├── nepali_dates.py    # BS → AD and date formatting
│   ├── filler.py          # PDF Filler: values + signature into the PDF
│   ├── mailer.py          # Mailer: file mode or Zoho SMTP with send gap
│   └── store.py           # Form Store: data/forms/<id>/, plus samples/
├── web/
│   ├── clinic.html
│   ├── fill.html
│   ├── css/saathi.css     # black and white system from Look and Feel
│   ├── js/clinic.js
│   ├── js/fill.js
│   ├── js/voice.js        # speech recognition + read-aloud
│   ├── js/nepali.js       # Nepali digits, UI strings
│   ├── lab.html           # build step 1 speech test page (dev only)
│   └── fonts/             # Inter, Noto Sans Devanagari, Dancing Script
├── samples/pt-intake/     # sample form PDF + saved conversion (form.json)
├── scripts/make_sample_form.py
├── tests/                 # pdf_reader, filler, nepali_dates, mailer gap
├── data/                  # runtime: forms/, outbox/ (gitignored)
├── devpost/               # Devpost learning workspace
├── .env.example
├── requirements.txt
├── run.sh
├── LICENSE                # MIT
└── README.md
```

## External Services and Dependencies

### Gemini API (free tier)
- **Calls:** `client.models.generate_content(model, contents, config={response_mime_type: "application/json",
  response_schema: ...})`, through `google-genai`. https://ai.google.dev/gemini-api/docs/structured-output
- **Two uses:**
  - One conversion call per uploaded form. The input is the reader's field list plus page text; the output is the
    questions JSON.
  - One call per spoken text, name or date answer.
- **Key:** `GEMINI_API_KEY`, from Google AI Studio. The learner creates it and puts it in `.env`.
- **Limits:** free-tier requests per minute and per day, which vary by model. Check the live limits in AI Studio.
  https://ai.google.dev/gemini-api/docs/rate-limits
- **Privacy:** free-tier prompts may be used by Google to improve its products, so the app is only ever run with
  sample data. https://ai.google.dev/gemini-api/terms
- **Cost:** $0.

### Zoho Mail SMTP
- **Connection:** `smtplib.SMTP_SSL(SMTP_HOST, 465)`, then `login(SMTP_USER, SMTP_PASSWORD)` and `send_message`.
  - The host is `smtppro.zoho.com` for domain accounts, and `smtp.zoho.com` for personal ones.
  - An app-specific password is needed if 2FA is on. https://www.zoho.com/mail/help/zoho-smtp.html
- **Sender:** `MAIL_FROM` on keepsrunning.com.
- **Limits:** the learner asked for few sends, 5–10 minutes apart. The app enforces at least 300 seconds between
  sends.
- **Cost:** $0, using the existing account.

### Browser audio
- **What it is:** `MediaRecorder` for recording answers, and the device voices for reading aloud.
  https://developer.mozilla.org/docs/Web/API/MediaRecorder
- **Requirements:** a secure origin.
- **Cost:** $0.

## Important Failure Modes
- **Nepali speech is misheard** → The both-sides card shows what was understood. The patient can say it again, type
  it, or skip it. Gemini's cleanup uses the question as context.
- **Gemini is slow, rate-limited or down:**
  - Clinic conversion shows a progress state and a retry button.
  - The patient's answer shows "say it again or type". A typed answer is still sent to the same call.
  - The sample form never needs conversion.
- **Zoho fails or a send is too soon** → The submit still returns the PDF for download, and the email is kept in
  `data/outbox/`. The Sent screen says, in Nepali, "Your form is ready. Please show this copy at the front desk",
  instead of an error.
- **The PDF has odd labels or field names** → Labels come from nearby printed words, not field names. The clinic
  review step lets the clinic fix any wording.

## What Was Simplified and Why
- **JSON files in folders instead of a database.** One form per clinic and no logins, so a database adds nothing. A
  real version would use Postgres with clinic accounts.
- **Clinic "sign-up" is a setup form without a password.** Agreed in scope. Real auth is deferred.
- **Gemini listens to the recording.** Chrome's free recognition was tried first and heard nothing in Nepali on the
  learner's machine, so the agreed fallback is in use: one Gemini call per spoken answer does both the hearing and
  the English. It also works in browsers without Chrome's recognition.
- **Read-aloud uses the device's voice.** Nepali voices vary by device, and Hindi voices read Devanagari as a
  fallback. A real version could pre-generate Nepali audio per question.
- **Sample form and saved conversion for demos.** The kernel stays real: any uploaded fillable PDF is converted live
  by Gemini. Only the sample is cached, to save free-tier calls and Zoho sends.

## Decisions and Open Issues

### Learner decisions
- Stack as in Memory Lane: FastAPI, PyMuPDF, plain HTML/JS.
- No Together credits. Gemini free tier for the AI, and only where it's really needed.
- Zoho on Keepsrunning for email, with a few real sends spaced 5–10 minutes apart; they're fine on weekends.
- Runs locally for building and recording. Deployment is decided in `6-ship`.

### Implementation details derived from those
- File mode is the default for mail, with a send gap of 300 seconds or more.
- A cached sample form.
- Dates: the AI extracts the date and code converts it.

### The useful unknown: how well Nepali speech is recognised
It's an open question from `prd.md > Open Questions`, and the main risk. **The agreed investigation is build step 1,
`web/lab.html`.** The learner speaks about 6 sample answers into Chrome's `ne-NP` recognition: a name, an address, a
Nepali date, a short accident story, a medication, and a yes/no. We judge the transcripts by eye and record the
result here.
- If several of them are unusable, switch `Voice` to recording audio and asking Gemini to transcribe it.
- The same page checks which Nepali or Hindi read-aloud voice exists on the recording machine.

- Sender address: `contact@keepsrunning.com`. The learner chose it.

### Still open
- The current Gemini model name and free-tier limits. Verified 2026-10-24: `gemini-3.6-flash`, 5 calls a minute
  per model on the free tier, with `gemini-3.5-flash` as the fallback.
- Nepali voice availability on Linux Chrome. Checked in build step 1.
- Build step 1 finding (automatic part): on the learner's Linux Chrome, `SpeechRecognition` exists and accepts
  `ne-NP`. There's no Nepali voice for reading aloud, only "Google हिन्दी" (hi-IN, online), which Saathi uses as the
  fallback.
- Build step 1 finding (learner's spoken test, 2026-10-24): Chrome's `ne-NP` recognition started and opened the mic
  without an error but returned no words for any of the 6 answers. So `Voice` now records the answer and Gemini
  listens to it. Checked with Nepali test clips (name, accident story, spoken phone digits): all three came back
  right in about 2 s.
