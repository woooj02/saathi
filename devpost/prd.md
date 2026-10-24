---
doc: prd
status: approved
---

# Saathi — Product Requirements

Saathi ("companion" in Nepali) lets an older Nepali-speaking patient fill a clinic's English intake form in Nepali,
by voice or tap, and sends the finished English form to the clinic.
Source: `scope.md > The Unique Kernel`, `scope.md > Who It's For`.

## The Core Journey
Source: `scope.md > The Core Loop`.

**Clinic (once per form)**
1. The clinic opens Saathi, enters its clinic name and email, and uploads its fillable intake PDF.
2. Saathi reads the form and turns every fillable box into a plain question, in English and in Nepali.
3. The clinic reviews the converted questions, fixes any wording, and publishes.
4. The clinic gets a patient link to send to its patients.

**Patient (every visit)**
5. The patient taps the clinic's link and lands on that clinic's page. They choose Nepali.
6. A short intro in Nepali explains what will happen. It can be read aloud.
7. Saathi asks one question at a time, in Nepali, on screen and read aloud. The patient answers by speaking or
   tapping.
8. After each answer, the patient sees both sides of it: what they said in Nepali, and the English that will go on
   the form. They confirm it, try again, or skip it.
9. The patient reviews all their answers in one list and can change any of them.
10. Consent sections are explained in plain Nepali. The patient types their full name, which is shown as a signature.
11. The patient sends the form. The filled English PDF is emailed to the clinic, and the patient can download a copy.

Success is the clinic receiving its own form, filled in correct English, by a patient who never had to read English.

## Screens and Layout

**Clinic**
- **Clinic setup:** clinic name, clinic email, PDF upload, and a "Convert" action.
- **Question review:** a list of every converted question, grouped by the form's sections. Each row shows the
  original English field label, the Nepali question and its answer type, and wording can be edited. A "Publish"
  action finishes the screen.
- **Patient link:** the link, a copy button, and a "Preview as patient" link.

**Patient** (phone first)
- **Welcome:** clinic name and a language choice: नेपाली / English.
- **Intro:** what will happen, how many questions there are, and "you can speak or tap".
- **Question:** one question per screen (described under `Answering a Question`).
- **Review:** every answer in one list.
- **Consent and sign.**
- **Sent:** confirmation and a "Download your copy" button.

## Look and Feel
Source: `scope.md > Inspiration & Identity`.
- Black and white only. "Very very modern and minimalistic." No colour except a single accent where a state needs it,
  for example a skipped answer.
- Large type and big tap targets, so an older patient never feels lost. One idea per screen.
- Calm and uncluttered. No dense tables on the patient side.
- Nepali shown in clear Devanagari type.
- Numbers in Nepali numerals (०–१०), with words such as शून्य, एक, दुई, तीन read aloud where useful.

## Features and Behavior

### Clinic Setup and Conversion
- As a clinic, I want to upload my existing intake PDF so that Nepali-speaking patients can fill it without an
  interpreter.
  - [ ] Uploading a fillable PDF with a clinic name and email starts the conversion and shows a progress state.
  - [ ] Every fillable box in the PDF becomes one question: text, date, yes/no, checkbox/choice, scale or signature.
  - [ ] Each question has a plain English wording and a plain Nepali wording. The wording is based on the visible
        label near the box, not the PDF's internal field name.
  - [ ] The clinic can edit the English or Nepali wording of any question before publishing.
  - [ ] Publishing gives a patient link that opens this clinic's form.

### Telling the Story Once
Added in the final review, at the learner's choice, to make the idea stand out ("goal is as close to 10 as
possible"). Source: `scope.md > The Unique Kernel`.
- As an older patient, I want to tell my story the way I'd tell an interpreter, not fill in fields, so that most of the
  form is done before the questions start.
  - [x] After the intro, a story screen asks the patient to talk about themselves and what happened, in their own
        words, with a list of topics (name, birthday, address, phone, what happened, where it hurts, insurance).
  - [x] One recording (up to 2 minutes; it waits through pauses) fills every answer the patient clearly said, and only
        those. Each one is checked like a single answer, so nothing goes on the form that a question couldn't put there.
  - [x] A results screen shows each filled answer both ways and says how many questions are left. The patient can say
        it again, or go on to the questions that are left, which skip what the story answered.
  - [x] Story answers are marked "तपाईंको कुराबाट" (from your story) on the review screen, where any can be changed.
  - [x] "एक-एक प्रश्न गरेर भर्छु" skips the story. Without AI, there's no story screen.

### Answering a Question
Source: `scope.md > The POC Boundary`.
- As an older Nepali-speaking patient, I want each question asked in Nepali, one at a time, so that I'm never
  confused by an English form.
  - [ ] Each question screen shows progress (for example प्रश्न ३ / ४२), the section name, and the question in large
        Nepali text, with a speaker button to hear it.
  - [x] The speaker plays the question in real Nepali (Gemini text-to-speech, recorded once per wording and kept), and
        falls back to the device's voice. Added in the final review: the only device voice on Linux Chrome is Hindi.
  - [ ] Answering matches the question type:
        - **Text or date:** a big microphone button to speak, plus an option to type instead.
        - **Yes/no:** two big buttons, हो and होइन.
        - **Checkbox/choice:** large tappable options in Nepali.
        - **Pain scale 0–10:** tiles with Nepali numerals ० to १०.
  - [ ] After a spoken or typed answer, a "both sides" card shows what Saathi understood in Nepali, next to the English
        that will go on the form. The patient can confirm, say it again, or type it.
  - [ ] Spoken answers become proper English for the form. Names are spelled in English letters, and dates are written
        in the English format the form expects, including dates given in the Nepali calendar.
  - [ ] A Back button returns to the previous question with its answer kept.

### Not Sure or Misunderstood
- As a patient, I want a way out when I don't know an answer, like I'd have with a real interpreter.
  - [ ] If Saathi can't understand the speech, it says so in Nepali and asks the patient to try again or type.
  - [ ] A "थाहा छैन / पछि दिन्छु" ("don't know / I'll give it later") option skips the question. The form gets
        "Patient will provide at visit", and the clinic's email lists the skipped fields.

### Review
- As a patient, I want to see all my answers before sending so that I'm sure they're right.
  - [ ] The review list shows each question in Nepali, the patient's answer, and the English that will be written.
        Skipped answers are marked.
  - [ ] Tapping any answer opens that question to change it, then returns to the review.

### Consent and Signature
- As a patient, I want to understand what I'm signing.
  - [ ] Each consent or agreement section of the form is explained in plain Nepali and can be read aloud.
  - [ ] The patient ticks that they understand, then types their full name. The name is previewed in a signature
        style, DocuSign-like, and today's date is filled in automatically.
  - [ ] The typed signature appears in the form's signature box on the PDF.

### Sending the Form
Source: `scope.md > What "Working" Looks Like`.
- As a clinic, I want the completed form in my inbox, in English, in my own PDF layout.
  - [ ] Sending emails the clinic's original PDF, filled in English, to the clinic email given at setup.
  - [ ] The email body names the patient and lists any skipped fields.
  - [ ] The Sent screen confirms in Nepali that it was sent to the named clinic, and offers "Download your copy" of the
        filled PDF.

## States and Boundaries
- **First use (clinic):** an empty setup screen with one clear instruction to upload your fillable intake PDF.
- **Not a fillable PDF:** "This PDF has no fillable boxes. Saathi needs a fillable PDF." Nothing is converted.
- **Not a PDF or unreadable:** a clear message, and a chance to try another file.
- **Converting:** a progress state. If the AI conversion fails, the clinic sees a retry option.
- **Invalid or unpublished link:** the patient sees "This form link isn't active" in Nepali and English.
- **Microphone blocked or unavailable:** speaking is hidden or explained, and typing and tapping still work.
- **Speech not understood:** see `Not Sure or Misunderstood`.
- **Leaving partway (assumption):** the patient's answers are kept on their device until they send, so a reload or
  accidental close doesn't lose them. Once sent, they're cleared.
- **Sending fails:** the patient sees a retry option and can still download their copy.
- **Sent:** the success screen.

## Product Decisions
- **Name: Saathi.** The learner chose it from offered options; it means "companion", like an interpreter sitting with
  the patient.
- **The patient fills it alone, in their own language.** The clinic gets English.
- **The clinic publishes the form and the patient arrives by link.** The clinic's email comes from setup.
- **The clinic checks the converted questions before publishing.** The learner said yes to a review step.
- **Fillable PDFs only.** Camera and scanned forms are cut (`scope.md > Explicitly Cut`).
- **Answers are shown both ways, Nepali and English, before they're accepted.** In the learner's words, the app should
  be "clear with both sides".
- **Nepali numerals for numbers and the pain scale.** The learner asked for the Nepali number system.
- **Signature the DocuSign way:** a typed full name shown as a signature.
- **Assumption: the "don't know / later" skip.** The learner asked for "some real life kinda solution". This mirrors
  what an interpreter does: leave it for the front desk, and flag it to the clinic.
- **Assumption: the patient copy is a download of the same English PDF.** It's not emailed, so the patient's email
  isn't collected.
- **Assumption: the demo uses a sample PT accident intake form made for the project, with made-up answers.** No real
  patient data.

- **Tell the story once (added in the final review).** The learner chose it over flat-PDF support as the way to make
  the project stand out. It mirrors how elders talk to an interpreter.
- **Questions read aloud in real Nepali (added in the final review),** to get the design "to 10".

## What We're Building
- Clinic setup, conversion of a fillable PDF into Nepali/English questions, question review and editing, and a
  patient link.
- A patient flow in Nepali: welcome, intro, one question at a time with read-aloud, voice/type/tap answers, the "both
  sides" check, and skip.
- Review, consent explained in Nepali, and a typed signature.
- A filled English PDF emailed to the clinic, and a patient download.
- A black-and-white, large-type, phone-first interface.

## Deferred From the POC
- **Real clinic accounts (login, dashboard, multiple forms).** Setup without a password proves the loop.
- **Storing submissions for the clinic in the app.** Email is the delivery. A clinic inbox inside Saathi comes later.
- **More languages.** Only if time allows after Nepali works end to end (`scope.md > Later`).
- **Emailing the patient their copy.** A download is enough for now.

## Possible Later Enhancements
- Languages such as Hindi, Bhutanese/Lhotshampa Nepali dialects, Burmese, Spanish and Arabic, for other communities.
- A clinic dashboard with multiple forms, a submissions history, and resend.
- Saathi reading a scanned form, once fillable forms are solid.

## Non-Goals
- **Medical or legal advice.** Saathi translates questions and answers, and never suggests what to answer.
- **Interpreting the appointment itself.** Only the form.
- **Immigration forms.** Cut in scope for legal risk.
- **A claim of HIPAA compliance.** This is a proof of concept with sample data. Real deployment would need that work.
- **Camera or photo input, and scanned PDFs.** Cut in scope.

## Open Questions
- **How accurately Nepali speech is recognised.** Answer in `4-spec`, by testing before the build.
- **The sample form.** We'll create a realistic fillable PT accident intake PDF rather than use a real clinic's
  copyrighted form. This can wait for the build.
