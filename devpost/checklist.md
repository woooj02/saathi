---
doc: checklist
status: approved
---

# Build Checklist

Build mode: fast. The learner asked to "finish all the coding" and to be checked in with only at the planned hands-on
points.

## Slices

- [x] **1. The sample intake form goes in, and a filled English PDF comes out**
  Becomes usable: `./run.sh` starts the server. A 5-page fillable PT accident intake sample exists. One command reads
  every box with its printed label and fills the PDF with test answers, including a typed signature in the signature
  font, giving a PDF you can open.
  Why now: this is the kernel's output, "it fills the clinic's actual form". It's also the PDF risk: whether labels
  can be read from nearby text, and whether checkbox, radio and signature filling works. It's proven before any
  screen is built on it. Bootstrapping is included.
  PRD ref: `prd.md > Clinic Setup and Conversion`, `prd.md > Consent and Signature`, `prd.md > States and Boundaries`
  Spec ref: `spec.md > Form Reader`, `spec.md > PDF Filler`, `spec.md > Sample Form`, `spec.md > File Structure`,
  `spec.md > Where It Runs and How Someone Tries It`
  Build: Add `requirements.txt`, `run.sh`, `.env.example`, `app/settings.py`, and a minimal `app/main.py` with a
  health route. Add `scripts/make_sample_form.py` to generate `samples/pt-intake/original.pdf`. Add
  `app/pdf_reader.py`: widgets, labels, sections, consent paragraphs, and `NotFillable`. Add `app/filler.py`: text,
  checkbox, radio, skip text, auto date, and signature in the signature font. Bundle the fonts. Add tests.
  Verify (mechanical): `pytest` passes for the reader (every widget found; labels match the printed text for known
  fields; a flat PDF raises `NotFillable`) and for the filler (values read back from the output PDF; signature text
  present). Render the filled pages to PNG and inspect them by eye.
  Learner check: Open `data/outbox/sample-filled.pdf` and check that it looks like a real clinic form, filled in.
  Commit: `Read and fill the sample intake form`

- [x] **2. Nepali speech test page**
  Becomes usable: `/lab` lets you tap a mic, speak Nepali, and see Chrome's transcript. It lists the Nepali and Hindi
  voices available for reading aloud, with a "read this" test.
  Why now: Nepali speech recognition is the main unknown (`spec.md > Decisions and Open Issues`). Every speaking
  feature depends on it, so its quality is known before the patient flow uses it.
  PRD ref: `prd.md > Answering a Question`, `prd.md > Open Questions`
  Spec ref: `spec.md > Voice`, `spec.md > Decisions and Open Issues`
  Build: Add `web/js/voice.js` (`listen()`, `speak()`, voice selection, unsupported and blocked states), `web/lab.html`,
  and the base `web/css/saathi.css`.
  Verify (mechanical): Open `/lab` in Chrome. There are no console errors. The page reports whether
  `SpeechRecognition` is supported and lists the voices found. `speak()` runs without errors.
  Learner check: In Chrome on your laptop, open `/lab` and speak the 6 test answers: a name, an address, a Nepali date,
  a short accident story, a medication, and a yes/no. Say whether the transcripts are usable.
  Commit: `Add Nepali speech test page`

- [x] **3. A patient can fill the sample form in Nepali and download the English PDF**
  Becomes usable: `/f/sample` is the full patient journey on the sample form: welcome, language, intro, then one
  question per screen. There are हो/होइन buttons, choices, the ० to १० scale, typed text and a date picker that
  accepts Nepali or English calendar dates, plus skip, back, review, consent explained in Nepali, the typed signature
  with a live preview, and send. The English PDF downloads, and the clinic email is saved to `data/outbox/`. Answers
  survive a reload.
  Why now: this is the core loop the judges will watch. It runs without any AI key, on the saved sample conversion.
  PRD ref: `prd.md > The Core Journey` (steps 5–11), `prd.md > Answering a Question`,
  `prd.md > Not Sure or Misunderstood`, `prd.md > Review`, `prd.md > Consent and Signature`,
  `prd.md > Sending the Form`, `prd.md > Look and Feel`
  Spec ref: `spec.md > Patient Pages`, `spec.md > Form Store`, `spec.md > Nepali Dates`, `spec.md > Mailer`,
  `spec.md > Web Server`, `spec.md > Look and Feel`, `spec.md > Data Model`
  Build: Add `samples/pt-intake/form.json`, the sample conversion. Add `app/store.py`, `app/nepali_dates.py`, and the
  `GET /api/forms/{id}` and `POST /api/forms/{id}/submit` routes. Add `app/mailer.py` in file mode. Add
  `web/fill.html`, `web/js/fill.js` and `web/js/nepali.js`.
  Verify (mechanical): `pytest` for BS→AD dates using known pairs, for submit returning a PDF with the answers read
  back, and for an outbox `.eml` being written. Drive `/f/sample` end to end in Chrome at phone size: answer, skip,
  reload mid-way (answers kept), review, sign, send, and the PDF downloads. There are no console errors.
  Learner check: Open `/f/sample` in Chrome's phone view. Fill a few questions, skip one, sign and send. Open the
  downloaded PDF. Say how it looks and feels for your mom.
  Commit: `Add the patient journey on the sample form`

- [x] **4. Spoken answers become English on the both-sides card**
  Becomes usable: On text, name and date questions, the patient taps the mic and speaks Nepali. Gemini returns clean
  Nepali and English, or a date that code converts. The both-sides card shows both before the patient confirms. If
  speech isn't understood, they're asked to say it again or type. Without a Gemini key, the mic is hidden and typing
  still works.
  Why now: it's the "oh, that's cool" moment in `scope.md`. It builds on the voice result from slice 2 and the flow
  from slice 3.
  PRD ref: `prd.md > Answering a Question`, `prd.md > Not Sure or Misunderstood`
  Spec ref: `spec.md > Answer Interpreter`, `spec.md > Nepali Dates`, `spec.md > Voice`,
  `spec.md > Gemini API (free tier)`, `spec.md > Important Failure Modes`
  Build: Add `app/gemini.py`, a structured-JSON call with one retry. Add `app/answers.py` and
  `POST /api/forms/{id}/interpret`. Wire `listen()` and the interpreter into `fill.js`. Add the both-sides card states,
  typed answers going through the same call, and a no-key fallback.
  Verify (mechanical): `pytest` with a fake Gemini client covering a text answer, a name, a BS date converting to AD,
  `ok:false`, and no key returning 503 with the UI fallback. Once `GEMINI_API_KEY` is in `.env`, one live call per
  kind confirms the real response shape.
  Learner check: On a text question, speak an answer in Nepali and check that the English on the card is right.
  Commit: `Turn spoken Nepali answers into English`

- [x] **5. A clinic uploads its PDF and gets a patient link**
  Becomes usable: `/clinic`: enter the name and email, upload a fillable PDF, and Gemini converts it. Review and edit
  the English and Nepali wording, publish, then copy the patient link and preview it as a patient. Non-PDF,
  not-fillable and conversion-failed states each show a clear message.
  Why now: the clinic side depends on the question format that slices 3–4 proved. The sample patient flow already
  works without it.
  PRD ref: `prd.md > The Core Journey` (steps 1–4), `prd.md > Clinic Setup and Conversion`,
  `prd.md > States and Boundaries`
  Spec ref: `spec.md > Form Converter`, `spec.md > Form Store`, `spec.md > Clinic Pages`, `spec.md > Web Server`
  Build: Add `app/converter.py`, which checks the schema and that every field is covered exactly once. Add the
  `POST /api/forms`, `PATCH` and `publish` routes, and `web/clinic.html` and `web/js/clinic.js`.
  Verify (mechanical): `pytest` with a fake Gemini client: the conversion covers every field once, a flat PDF returns
  a not-fillable error, and invalid JSON is retried. Drive `/clinic` in Chrome: upload, edit wording, publish, and
  open the link. Once the key is in `.env`, convert the sample PDF live and save that output as
  `samples/pt-intake/form.json`, so the sample is real Gemini output.
  Learner check: Upload the sample PDF on `/clinic`, read the Nepali questions, and fix one wording. Publish, then open
  the patient link.
  Commit: `Add clinic upload, review and patient link`

- [x] **6. The filled form arrives in the clinic's inbox**
  Becomes usable: With `MAIL_MODE=send`, sending emails the filled PDF from `contact@keepsrunning.com` to the clinic,
  with skipped fields listed. A second send within 300 seconds is held in the outbox, and the patient's download still
  works.
  Why now: it finishes the journey. It's last because it needs the learner's Zoho app password, and real sends are
  precious.
  PRD ref: `prd.md > Sending the Form`, `prd.md > States and Boundaries` ("Sending fails")
  Spec ref: `spec.md > Mailer`, `spec.md > Zoho Mail SMTP`, `spec.md > Important Failure Modes`
  Build: Add send mode to `app/mailer.py`: SMTP over SSL, the send gap, and the outbox on failure. Show the Sent screen
  messages for each mail status. Write `README.md` and `LICENSE` (MIT).
  Verify (mechanical): `pytest` with a fake SMTP server, checking that the gap is enforced and that a failure keeps the
  outbox copy and still returns the PDF. Once Zoho credentials are in `.env`, one real send to the learner's inbox,
  with at least 5–10 minutes before any other send.
  Learner check: Send the sample form and check that the email and its PDF arrive in your inbox.
  Commit: `Email the filled form to the clinic`

## Hands-on Checkpoints

- [x] Early usable behavior explored — after slice 3 (patient journey on the sample form), plus the slice 2 speech
  test. Done 2026-10-24, after all slices: the learner's feedback was that middle name had no "I don't have one"
  answer, and the mic didn't hear Nepali. Both fixed (see Revisions); the learner retried the mic: "worked fine".
- [x] Final kick-the-tires exploration and feedback completed (run in Chrome with the learner supervising,
  2026-10-24; their requests A and B plus the fit fix are under Final Review)

## Final Review

- [x] Live Gemini checks once `GEMINI_API_KEY` is in `.env`: one interpret call per answer kind, and
  `scripts/convert_sample.py` to make the sample's questions real Gemini output (slices 4–5)
- [x] One real Zoho send once the app password is in `.env` (slice 6), at least 5–10 minutes from any other send
- [x] Learner's Nepali speech test on `/lab` (slice 2), and a check of the Nepali wording, by a native speaker
- [x] Fix (learner, final review): "I don't have one" and skip sit right under the answer, not below the fold on a
  small phone
- [x] Fix (learner, final review): the clinic review marks questions that are only a box label ("City") as "Needs
  your wording"
- [x] Fix (found in final review): a long answer in a narrow one-line box shrinks to fit ("Patient will provide at
  visit" was cut off in Group number)
- [x] Final review complete — feedback resolved and learner confirms ready to ship ("yep ready to ship", 2026-10-24)

## Code Tour and App Map

- [ ] Learning activity complete — guided route, focused alternative, prior practice connected, or brief recap
- [ ] Optional edit and transfer reflection addressed — offered/declined/already covered/not applicable as appropriate
- [x] `devpost/app-map.html` generated from finished code, checked, and shown, including a project-grounded practice
  to reuse

Activity and evidence: guided route offered (follow "tell the story once" through the code), tied to the spec's
useful unknown: the `/lab` test came back empty, so the planned fallback (Gemini listens) was used, and it became the
story. Waiting for the learner to walk the route.
Route and stops: `web/js/fill.js` story() → `app/story.py` extract()/_schema() → `app/story.py` _check() and
`fill.js` storyResult(). Map checked offline with headless Chrome; all anchors checked against the source.
Edit outcome: not started
Reflection: not started
Activity mode: not started

## Revisions
- The sample form is drawn with reportlab, not PyMuPDF. PyMuPDF can't create proper radio groups (its buttons get no
  export values), although it reads and fills them fine. reportlab draws its radio circles at about half size, so the
  generator redraws them centred.
- The default port is 8010, not 8000. Another of the learner's local apps already uses 8000.
- The signature box is removed and the typed name drawn in its place. Form boxes are painted on top of the page, so a
  signature drawn under the grey box was hidden.
- The sample's questions in `samples/pt-intake/form.json` are hand-written for now
  (`scripts/sample_questions.py`, `"source": "handwritten"`). There's no Gemini key yet. Slice 5 replaces them with
  Gemini's live conversion. They use the converter's exact output format, so nothing downstream changes.
- Added answer kinds that the spec only implied: `number`, `code` (IDs and claim numbers) and `email`, plus
  `auto_date`, `auto_name` and `skip` for boxes Saathi fills itself or leaves alone. Text questions can offer tap
  suggestions, for example relationships. Without AI, typed answers must be in English letters, because the clinic's
  PDF font can't show Devanagari and the clinic needs English. Nepali typing and speech go through the interpreter in
  slice 4.
- Dates also have a picker (Nepali or English calendar, year/month/day) that needs no AI. The server converts BS→AD
  exactly (`GET /api/dates/convert`). Speaking a date is added in slice 4.
- Slice 4 was verified with a fake Gemini, in unit tests and in a throwaway browser check of the both-sides card. The
  live Gemini check (one call per kind) waits for the learner's `GEMINI_API_KEY`. Spoken input on the patient pages
  can only be tried by a person at a microphone.
- Typed Nepali also goes through the interpreter, not just speech, so a patient can type in Devanagari once AI is on.
  Phone numbers, codes and email are cleaned up in code after Gemini, not trusted as-is.
- Clinic setup is two calls, not one. `POST /api/forms` reads the boxes in under a second and returns the count, then
  `POST /api/forms/{id}/convert` runs Gemini. This lets the progress screen show real steps, and lets a failed
  conversion be retried without uploading again. Editing and publishing need a per-form edit key, which the clinic's
  browser keeps, so a patient with the link can't change the form.
- The converter checks Gemini's output against the PDF. Every box is covered exactly once, and radio option values are
  the PDF's real export values. Boxes Gemini misses get a second, smaller call, then a plain fallback marked "Needs
  your wording" for the clinic. Verified with a fake Gemini (tests, and a browser run of
  upload → convert → edit → publish → patient link). The live conversion waits for the key (see Final Review).
- Patient links use `PUBLIC_BASE_URL` if set, else the address the clinic page was opened on.
- Mail statuses are `sent`, `saved` (file mode), `deferred` (inside the send gap) and `failed`. The patient's Sent
  screen says "sent to the clinic" for sent and saved, and "show this copy at the front desk" otherwise. Verified with
  a fake SMTP server. The one real Zoho send waits for the app password (see Final Review).
- The `LICENSE` copyright line uses the name from the learner's Devpost profile (Aryan Neopane). Confirmed by the
  learner on 2026-10-24.
- Live Gemini (2026-10-24): `gemini-2.5-flash` is closed to new keys, and 3.7 and 3.8 Flash timed out, so the default
  model is `gemini-3.6-flash`. The free tier allows 5 calls a minute per model, so a rate-limited or overloaded call
  moves on to `GEMINI_FALLBACK_MODEL` (`gemini-3.5-flash`). That happened in the live conversion (a 503) and it
  finished anyway. Every typed or spoken answer kind returned the right English: name, BS date, "yesterday", phone,
  email, member ID, free text, and "I don't know" coming back as not understood.
- The sample's questions are now Gemini's live conversion (about 70 s, every box covered, 4 consent sections,
  nothing needing review). The hand-written version became the tests' fixed copy (`tests/fixtures/sample-form.json`),
  so tests don't change when the sample is re-converted. A new test checks the shipped sample still fits the PDF.
- The learner's `/lab` test: Chrome's Nepali recognition heard nothing for all 6 answers (no error, no words). Per the
  spec's planned fallback, the patient mic now records the answer and Gemini listens to it
  (`POST /api/forms/{id}/interpret-audio`, one call per answer), with a level bar and auto-stop after a pause.
  Checked with generated Nepali clips through the API and through the real page with the clip played into the mic.
- The learner had to type "n/a" for middle name. Optional typed questions now have "मसँग छैन / लागू हुँदैन" (I don't
  have one / Doesn't apply), which writes N/A on the form so the clinic can tell it from a missed question.
- Static files are sent with `Cache-Control: no-cache`, because Chrome kept running an old copy of the page script
  after an update.
- The free tier turned out to be about 20 calls a day per model, and testing used up `gemini-3.6-flash` and
  `gemini-3.5-flash` for the day. Gemini now tries a chain of models (`GEMINI_FALLBACK_MODELS`), each with its own
  daily quota, and skips a model that reports its daily quota spent. The clinic retry then converted with
  `gemini-3-flash-preview`.
- That weaker model wrote many questions as bare labels ("City", "Member ID") and left yes/no buttons in English.
  The conversion prompt now asks for full questions (and क्लिनिक, not अस्पताल, for a clinic), and code gives yes/no
  buttons हो / होइन whatever the model returns.
- Final review run in Chrome at phone width (333 px), with the learner watching: clinic setup → conversion → wording
  edits → publish → patient journey by voice (Nepali clips played into the mic), typing, Nepali-calendar picker,
  N/A, skip, review, consent, signature → real send at 14:06.
- One real Zoho send on 2026-10-24 (13:36), from contact@ to contact@keepsrunning.com: status `sent`, filled PDF
  attached.
- After the final review, the learner asked to get Design and Innovation "as close to 10 as possible" before the
  video. Chosen by the learner: **tell the story once** (one recording fills every answer it heard; checked like single
  answers; then only the rest is asked). Live check with a 57 s Nepali story: 18 answers filled, including "last
  Thursday" → 10/22/2026; one miss ("right knee" heard as leg/hip), which the review screen is for. Also for design:
  questions read aloud in real Nepali with Gemini text-to-speech, recorded once per wording, the sample's recordings
  committed; README screenshots.
