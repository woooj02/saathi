---
doc: scope
status: approved
---

# Speak-to-Form (working name)

A browser app that lets a patient who doesn't speak English fill a clinic's English intake form by answering
questions in their own language, then sends the finished English form to the clinic.

## The Unique Kernel
It fills **the clinic's actual form**. The patient never reads or writes English. They answer one clear question at a
time in Nepali, and the app writes correct English answers into the real PDF the clinic gave them. Translators today
mean "copy-pasting a lot", or a website that is "very very unclear and un objective". This removes both.

## Who It's For
An older Nepali-speaking patient, like the learner's parents or elders in their community, going to a first visit at
a physical therapy clinic after an accident. The clinic sends a 5–10 page intake form that "literally asks for
everything": insurance, accident details, pain, history, medications. They fill it in **themselves**, on their own,
in their own language.

Today, the learner (an in-person interpreter) or a paid interpreter fills it for them. Sometimes the interpreter's cost
is "charged back to them".

## The Core Loop
**Clinic, once:** the clinic signs up and uploads its fillable intake PDF. The app automatically converts it into a
guided, translated form, and the clinic gets a link to send to its patients.

**Patient, every visit:** the patient opens the clinic's link and picks Nepali. The app walks through the form
one question at a time, in plain Nepali (shown and read aloud), and the patient answers by speaking or tapping. They
check their answers, then sign the DocuSign way, with their typed full name rendered as a signature after the
consent text is explained in Nepali. The filled English form goes to the clinic by email. They can keep a copy if they want.

They come back for every new clinic, doctor or appointment with a form.

## Inspiration & Identity
Black and white. "Very very modern and minimalistic." Calm and uncluttered, so an older patient never feels lost.

## Why This Matters to the Learner
"It's gonna help my community the most." The learner interprets at in-person appointments, and nearly every one
starts with a form. "It will help me lots", and while they focus on their tech career, it can be "a gift to community
and my parents and family as well."

## What "Working" Looks Like
A clinic uploads a real-looking, fillable PT accident intake PDF and gets a patient link. A patient answers its questions in Nepali, by voice. The
filled **English** PDF arrives in the clinic's inbox, with a copy for the patient.

The "oh, that's cool" beat: Nepali spoken answers on one side, and the clinic's English form filling itself in on the
other.

## The POC Boundary
- One input type: fillable PDF forms, with the boxes built in. Demonstrated on one realistic PT first-visit /
  accident intake form.
- Nepali ↔ English only.
- The app reads the form's fields and turns them into plain, one-at-a-time questions in Nepali, shown on screen and
  read aloud.
- The patient answers by voice in Nepali, or by tapping for yes/no and checkbox items. Answers are put into proper
  English for the form.
- A review step before sending.
- Clinic setup: clinic name, its email and its PDF upload, then automatic conversion and a shareable patient link. No
  passwords or real login in the proof of concept.
- Signing: consent and signature text explained in Nepali, and the typed full name rendered as a signature on the PDF.
- Email the filled English PDF to the clinic, plus an optional copy for the patient.
- A black-and-white, minimal interface that is readable for older users.

## Later
- A couple more languages, if time allows.
- Real clinic accounts: login, a dashboard, and managing several forms.

## Explicitly Cut
- **Camera / photo of paper forms.** The learner said it "adds a layer of extra hassle and more mistake chances to
  [an] already complicated process."
- **Scanned or flat PDFs without fillable boxes.** Fillable boxes are the most reliable to fill, and cover the email
  case.
- **Immigration forms.** A wrong answer has legal consequences, and there are rules about who may help fill them.
  Medical intake is the focus.
- **Patient accounts and long-term storage of patient data.** Not needed to prove the loop. The proof of concept is
  demoed with made-up sample answers only.
