// Patient journey: welcome → intro → story (tell it once) → one question per screen → review → consent → sign → sent.
// See devpost/prd.md > The Core Journey (steps 5–11) and devpost/spec.md > Patient Pages.

import { canRecord, recordAnswer, stopRecording, speak, stopSpeaking, canSpeak, ICONS } from "./voice.js";
import { t, toNe, toAscii, hasDevanagari, BS_MONTHS, AD_MONTHS_NE, AD_MONTHS_EN } from "./nepali.js";

const FORM_ID = decodeURIComponent(location.pathname.split("/").filter(Boolean)[1] || "");
const STORE_KEY = `saathi:${FORM_ID}`;
const AUTO_KINDS = new Set(["signature", "auto_date", "auto_name", "skip"]);
const TYPED_KINDS = new Set(["text", "name", "number", "code", "email"]);
const SKIP = "__skip__";
const app = document.getElementById("app");

let form = null;
let asked = [];          // the questions a patient actually answers, in order
let ai = false;          // Gemini configured on the server
let speakable = false;   // a voice exists for the chosen language
let st = blankState();
let download = null;     // {url, filename, status} after sending

// -- state, kept on the phone until the form is sent ---------------------------

function blankState() {
  return { lang: null, screen: "welcome", index: 0, answers: {}, signer: "", agreed: false, autoRead: true, returnTo: null };
}

function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORE_KEY) || "null");
    return saved ? { ...blankState(), ...saved } : blankState();
  } catch {
    return blankState();
  }
}

function save() {
  try { localStorage.setItem(STORE_KEY, JSON.stringify(st)); } catch { /* private mode: keep going in memory */ }
}

function clearSaved() {
  try { localStorage.removeItem(STORE_KEY); } catch { /* nothing to clear */ }
}

// -- small helpers ---------------------------------------------------------------

const L = () => st.lang || "ne";
const tr = (key, vars) => t(L(), key, vars);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const qText = (q) => (L() === "ne" ? q.ne : q.en);
const optText = (o) => (L() === "ne" ? o.ne : o.en);
const num = (n) => (L() === "ne" ? toNe(n) : String(n));
const voicePrefs = () => (L() === "ne" ? ["ne", "hi"] : ["en"]);

function screen(html) {
  stopVoice();
  stopRecording();
  app.innerHTML = `<section class="screen">${html}</section>`;
  app.querySelector(".screen").lang = L() === "ne" ? "ne" : "en";
  window.scrollTo(0, 0);
  return app.querySelector(".screen");
}

function go(name) {
  st.screen = name;
  save();
  render();
}

// Read aloud. In Nepali, a key (question id, consent-<id>, or a screen's name) plays the clinic's real Nepali
// recording from the server; without one, or when it can't be had, the device's own voice reads the text.
let playing = null;

function stopVoice() {
  stopSpeaking();
  if (playing) { playing.pause(); playing = null; }
}

function say(text, key) {
  if (!speakable) return;
  stopVoice();
  const device = () => speak(text, { prefer: voicePrefs() }).catch(() => {});
  if (!key || L() !== "ne" || !form.voice) return device();
  const audio = new Audio(`/api/forms/${encodeURIComponent(FORM_ID)}/voice/${encodeURIComponent(key)}`);
  playing = audio;
  audio.play().catch(() => { if (playing === audio) { playing = null; device(); } });
}

function speakerButton(text, key = "") {
  if (!speakable) return "";
  return `<button class="icon-btn" data-say="${esc(text)}" data-key="${esc(key)}" aria-label="${esc(tr("listen"))}">${ICONS.speaker}</button>`;
}

function wireSpeakers(root) {
  root.querySelectorAll("[data-say]").forEach((b) => b.addEventListener("click", () => say(b.dataset.say, b.dataset.key)));
}

async function findVoice() {
  speakable = (L() === "ne" && Boolean(form.voice)) || (await canSpeak(voicePrefs()));
}

function answeredCount() {
  return asked.filter((q) => st.answers[q.id]).length;
}

// -- screens -----------------------------------------------------------------------

function render() {
  if (!form) return;
  const draw = { welcome, intro, story, question, review, consent, sign, sending, sent }[st.screen] || welcome;
  draw();
}

function brand() {
  return `<div class="topbar"><div class="brand">Saathi <span class="ne">साथी</span></div></div>`;
}

function welcome() {
  const root = screen(`
    ${brand()}
    <div class="grow">
      <div class="hero">${esc(form.clinic_name)}</div>
      <p class="ne" lang="ne" style="font-size:20px">${esc(form.form_title_ne || "")}</p>
      <p class="muted">${esc(form.form_title_en || "")}</p>
      <hr>
      <p class="ne" lang="ne" style="font-size:19px">${esc(t("ne", "welcomeLine"))}</p>
      <p class="muted small">${esc(t("en", "welcomeLine"))}</p>
    </div>
    <div class="foot">
      <div class="section-label"><span class="ne">भाषा छान्नुहोस्</span> · Choose your language</div>
      <button class="btn primary big ne" data-lang="ne">नेपाली</button>
      <button class="btn big" data-lang="en">English</button>
    </div>`);
  root.querySelectorAll("[data-lang]").forEach((b) =>
    b.addEventListener("click", async () => {
      st.lang = b.dataset.lang;
      await findVoice();
      go("intro");
    }),
  );
}

function intro() {
  const total = asked.length;
  const resumable = answeredCount() > 0;
  const body = storyReady() ? tr("introBodyStory") : tr("introBody");
  const root = screen(`
    <div class="q-top"><button class="icon-btn" data-act="back" aria-label="${esc(tr("back"))}">${ICONS.back}</button><div class="grow"></div>${speakerButton(`${tr("introTitle")}। ${body}`, storyReady() ? "intro-story" : "intro")}</div>
    <div class="grow">
      <h1 class="hero">${esc(tr("introTitle"))}</h1>
      <p style="font-size:20px">${esc(body)}</p>
      <p class="muted">${esc(tr("introCount", { total, minutes: Math.max(5, Math.round(total * 0.25)) }))}</p>
      ${speakable ? `<label class="toggle"><input type="checkbox" id="autoread" ${st.autoRead ? "checked" : ""}> ${esc(tr("readAloud"))}</label>` : ""}
    </div>
    <div class="foot">
      ${resumable
        ? `<button class="btn primary big" data-act="resume">${esc(tr("continueWhere"))} · ${esc(num(answeredCount()))}/${esc(num(total))}</button>
           <button class="btn link skip" data-act="restart">${esc(tr("startOver"))}</button>`
        : `<button class="btn primary big" data-act="start">${esc(tr("start"))}</button>`}
    </div>`);
  wireSpeakers(root);
  root.querySelector("#autoread")?.addEventListener("change", (e) => { st.autoRead = e.target.checked; save(); });
  root.querySelector('[data-act="back"]').addEventListener("click", () => go("welcome"));
  root.querySelector('[data-act="start"]')?.addEventListener("click", () => { st.index = 0; go(storyReady() ? "story" : "question"); });
  root.querySelector('[data-act="resume"]')?.addEventListener("click", () => {
    const next = asked.findIndex((q) => !st.answers[q.id]);
    st.index = next === -1 ? asked.length - 1 : next;
    go(next === -1 ? "review" : "question");
  });
  root.querySelector('[data-act="restart"]')?.addEventListener("click", () => {
    st = { ...blankState(), lang: st.lang, screen: "question" };
    save();
    render();
  });
}

// -- the story: tell it once, and Saathi fills what it heard ---------------------------

function storyReady() {
  return ai && canRecord();
}

// the next (step 1) or previous (step -1) question that wasn't already answered by the story
function openIndex(from, step) {
  let i = from;
  while (i >= 0 && i < asked.length && st.answers[asked[i].id]?.story) i += step;
  return i;
}

function story() {
  const root = screen(`
    <div class="q-top"><button class="icon-btn" data-act="back" aria-label="${esc(tr("back"))}">${ICONS.back}</button><div class="grow"></div>${speakerButton(`${tr("storyTitle")}। ${tr("storyBody")}`, "story")}</div>
    <div id="story-prompt">
      <h1 class="question">${esc(tr("storyTitle"))}</h1>
      <p style="font-size:19px">${esc(tr("storyBody"))}</p>
      <p class="muted small">${esc(tr("storyTopics"))}</p>
    </div>
    <div id="story-area">${micBlock(tr("storyTap"))}</div>
    <div class="foot near"><button class="btn link skip" data-act="skip-story">${esc(tr("storySkip"))}</button></div>`);
  wireSpeakers(root);
  root.querySelector('[data-act="back"]').addEventListener("click", () => go("intro"));
  root.querySelector('[data-act="skip-story"]').addEventListener("click", () => {
    st.index = openIndex(0, 1);
    go(st.index >= asked.length ? "review" : "question");
  });
  const area = root.querySelector("#story-area");
  const filled = asked.filter((q) => st.answers[q.id]?.story);
  if (filled.length) return storyResult(root, area, filled);
  if (st.autoRead && speakable) say(`${tr("storyTitle")}। ${tr("storyBody")}`, "story");

  const mic = area.querySelector('[data-act="mic"]');
  const status = area.querySelector(".status");
  const level = area.querySelector(".meter span");
  mic.addEventListener("click", async () => {
    if (mic.classList.contains("listening")) return stopRecording();
    stopVoice();
    mic.classList.add("listening");
    mic.innerHTML = ICONS.stop;
    status.textContent = tr("storyListening");
    try {
      // older patients pause to think, so wait longer for the end of the story than for one answer
      const clip = await recordAnswer({ maxSeconds: 120, quietMs: 4000, waitMs: 10000, onLevel: (v) => (level.style.width = `${Math.round(v * 100)}%`) });
      mic.classList.remove("listening");
      mic.innerHTML = ICONS.mic;
      mic.disabled = true;
      status.textContent = tr("storyUnderstanding");
      const body = new FormData();
      body.append("audio", clip.blob, `story.${clip.type.includes("mp4") ? "m4a" : clip.type.includes("ogg") ? "ogg" : "webm"}`);
      const res = await fetch(`/api/forms/${encodeURIComponent(FORM_ID)}/story`, { method: "POST", body });
      if (!res.ok) throw new Error(`story ${res.status}`);
      const r = await res.json();
      const heard = asked.filter((q) => r.answers[q.id]);
      if (!heard.length) { status.textContent = tr("storyNothing"); return; }
      heard.forEach((q) => (st.answers[q.id] = r.answers[q.id]));
      save();
      storyResult(root, area, heard);
    } catch (err) {
      status.textContent = err.code === "not-allowed" || err.code === "audio-capture" ? tr("micBlocked") : tr("storyNothing");
    } finally {
      mic.classList.remove("listening");
      mic.innerHTML = ICONS.mic;
      mic.disabled = false;
    }
  });
}

// What the story filled in, both sides, before moving on to the questions that are left.
function storyResult(root, area, filled) {
  const left = asked.filter((q) => !st.answers[q.id]).length;
  root.querySelector(".foot.near")?.remove();
  root.querySelector("#story-prompt")?.remove();
  area.innerHTML = `
    <div class="story-done">
      <div class="big-check small">${ICONS.check}</div>
      <h1 class="question">${esc(tr("storyFilled", { n: filled.length }))}</h1>
      <p class="help">${esc(tr("storyFilledBody", { left }))}</p>
      <div class="review-list">${filled.map((q) => {
        const a = st.answers[q.id];
        return `<div class="review-item static"><div class="rq">${esc(qText(q))}</div><div class="ra">${esc(a.said)}</div>${L() === "ne" && a.en !== a.said ? `<div class="re" lang="en">${esc(a.en)}</div>` : ""}</div>`;
      }).join("")}</div>
      <button class="btn primary big" data-act="go">${ICONS.check} ${esc(tr("storyNext"))}</button>
      <button class="btn big" data-act="again">${esc(tr("storyAgain"))}</button>
    </div>`;
  if (st.autoRead && speakable) say(tr("storyFilled", { n: filled.length }));
  area.querySelector('[data-act="go"]').addEventListener("click", () => {
    st.index = asked.findIndex((q) => !st.answers[q.id]);
    go(st.index === -1 ? "review" : "question");
  });
  area.querySelector('[data-act="again"]').addEventListener("click", () => {
    for (const q of asked) if (st.answers[q.id]?.story) delete st.answers[q.id];
    save();
    render();
  });
}

// -- one question --------------------------------------------------------------------

function question() {
  const q = asked[st.index];
  if (!q) return go("review");
  const total = asked.length;
  const long = q.long || qText(q).length > 70;
  const root = screen(`
    <div class="q-top">
      <button class="icon-btn" data-act="back" aria-label="${esc(tr("back"))}">${ICONS.back}</button>
      <div class="progress">${esc(tr("progress", { n: st.index + 1, total }))}</div>
      ${speakerButton(qText(q), q.id)}
    </div>
    <div class="bar"><span style="width:${((st.index + 1) / total) * 100}%"></span></div>
    <div class="section-label">${esc(L() === "ne" ? q.section_ne : q.section_en)}</div>
    <h1 class="question ${long ? "long" : ""}">${esc(qText(q))}</h1>
    ${L() === "ne" ? `<p class="en-hint" lang="en">${esc(q.en)}</p>` : ""}
    ${q.help_ne && L() === "ne" ? `<p class="help">${esc(q.help_ne)}</p>` : ""}
    <div class="answer" id="answer"></div>
    <div class="foot near">
      ${q.optional && TYPED_KINDS.has(q.kind) ? `<button class="btn link skip" data-act="na">${esc(tr("notApplicable"))}</button>` : ""}
      <button class="btn link skip" data-act="skip">${esc(tr("skip"))}</button>
    </div>`);
  wireSpeakers(root);
  root.querySelector('[data-act="back"]').addEventListener("click", back);
  root.querySelector('[data-act="skip"]').addEventListener("click", () => record(q, { skipped: true, said: tr("skipped"), en: "Patient will provide at visit" }));
  // "I don't have one": N/A on the form, so the clinic can tell it from a question that was missed
  root.querySelector('[data-act="na"]')?.addEventListener("click", () => record(q, { value: "N/A", said: tr("notApplicable"), en: "N/A" }));
  const area = root.querySelector("#answer");
  const existing = st.answers[q.id];
  if (TYPED_KINDS.has(q.kind)) typedAnswer(q, area, existing);
  else if (q.kind === "date") dateAnswer(q, area, existing);
  else if (q.kind === "multi") multiAnswer(q, area, existing);
  else tapAnswer(q, area, existing);
  if (st.autoRead && speakable) say(qText(q), q.id);
}

function back() {
  if (st.returnTo === "review") { st.returnTo = null; return go("review"); }
  const prev = openIndex(st.index - 1, -1);
  if (prev >= 0) { st.index = prev; return go("question"); }
  go(storyReady() ? "story" : "intro");
}

function record(q, rec) {
  st.answers[q.id] = rec;
  save();
  if (st.returnTo === "review") { st.returnTo = null; return go("review"); }
  st.index = openIndex(st.index + 1, 1);
  go(st.index >= asked.length ? "review" : "question");
}

// yes/no, single choice, 0–10 scale: one tap answers and moves on
function tapAnswer(q, area, existing) {
  const current = existing && !existing.skipped ? existing.value : null;
  const opts = q.options || [];
  const cls = q.kind === "yesno" ? "yesno" : q.kind === "scale" ? "scale" : "";
  area.innerHTML = `
    <div class="${cls}" style="${cls ? "" : "display:flex;flex-direction:column;gap:12px"}">
      ${opts.map((o, i) => `<button class="option" data-i="${i}" aria-pressed="${o.value === current}">${esc(q.kind === "scale" ? num(o.value) : optText(o))}</button>`).join("")}
    </div>
    ${q.kind === "scale" ? `<div class="scale-ends"><span>${num(0)} = ${esc(tr("noPain"))}</span><span>${num(10)} = ${esc(tr("worstPain"))}</span></div>` : ""}`;
  area.querySelectorAll(".option").forEach((b) =>
    b.addEventListener("click", () => {
      const o = opts[Number(b.dataset.i)];
      area.querySelectorAll(".option").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      setTimeout(() => record(q, { value: o.value, said: q.kind === "scale" ? num(o.value) : optText(o), en: o.en }), 220);
    }),
  );
}

// checkboxes under one question: tap all that apply, then Next
function multiAnswer(q, area, existing) {
  const chosen = new Set(existing && !existing.skipped ? existing.value : []);
  const opts = q.options || [];
  area.innerHTML = `
    ${opts.map((o, i) => `<button class="option" data-i="${i}" aria-pressed="${chosen.has(o.value)}"><span class="box">${ICONS.check}</span>${esc(optText(o))}${L() === "ne" ? `<span class="sub" lang="en">${esc(o.en)}</span>` : ""}</button>`).join("")}
    <div class="row" style="margin-top:6px">
      <button class="btn big" data-act="none" style="flex:1">${esc(tr("none"))}</button>
      <button class="btn primary big" data-act="next" style="flex:1">${esc(tr("next"))}</button>
    </div>`;
  area.querySelectorAll(".option").forEach((b) =>
    b.addEventListener("click", () => {
      const v = opts[Number(b.dataset.i)].value;
      chosen.has(v) ? chosen.delete(v) : chosen.add(v);
      b.setAttribute("aria-pressed", String(chosen.has(v)));
    }),
  );
  const finish = (values) => {
    const picked = opts.filter((o) => values.includes(o.value));
    record(q, {
      value: picked.map((o) => o.value),
      said: picked.length ? picked.map(optText).join(", ") : tr("none"),
      en: picked.length ? picked.map((o) => o.en).join(", ") : "None",
    });
  };
  area.querySelector('[data-act="next"]').addEventListener("click", () => finish([...chosen]));
  area.querySelector('[data-act="none"]').addEventListener("click", () => finish([]));
}

// The "both sides" card: what the patient said, and the English that goes on the form.
function bothSides(q, area, rec, { onAgain, spoken = false } = {}) {
  area.innerHTML = `
    <div class="both">
      <div><div class="side-label">${esc(tr("youSaid"))}</div><div class="said">${esc(rec.said)}</div></div>
      <div class="form-side"><div class="side-label">${esc(tr("onTheForm"))}</div><div class="value" lang="en">${esc(rec.en)}</div></div>
    </div>
    <button class="btn primary big" data-act="ok">${ICONS.check} ${esc(tr("looksRight"))}</button>
    <button class="btn big" data-act="again">${esc(tr(spoken ? "tryAgain" : "edit"))}</button>`;
  area.querySelector('[data-act="ok"]').addEventListener("click", () => record(q, rec));
  area.querySelector('[data-act="again"]').addEventListener("click", () => (onAgain ? onAgain() : render()));
}

// Ask the server to turn a typed Nepali answer into English (Gemini).
async function interpret(q, transcript) {
  const res = await fetch(`/api/forms/${encodeURIComponent(FORM_ID)}/interpret`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ question_id: q.id, transcript, lang: L() }),
  });
  if (!res.ok) throw new Error(`interpret ${res.status}`);
  return res.json();   // {ok, said, en, value}
}

// A recording of the spoken answer: Gemini listens to it and writes the English.
async function interpretAudio(q, { blob, type }) {
  const body = new FormData();
  body.append("question_id", q.id);
  body.append("audio", blob, `answer.${type.includes("mp4") ? "m4a" : type.includes("ogg") ? "ogg" : "webm"}`);
  const res = await fetch(`/api/forms/${encodeURIComponent(FORM_ID)}/interpret-audio`, { method: "POST", body });
  if (!res.ok) throw new Error(`interpret-audio ${res.status}`);
  return res.json();   // {ok, said, en, value, parts?}
}

function micBlock(label = tr("tapToSpeak")) {
  return `
    <div class="speak-area">
      <button class="mic" data-act="mic" aria-label="${esc(label)}">${ICONS.mic}</button>
      <div class="meter" aria-hidden="true"><span></span></div>
      <div class="status" role="status">${esc(label)}</div>
    </div>`;
}

// onResult(r) gets the interpreter's reply; it throws (or returns false) if the answer didn't fit.
function wireMic(q, area, onResult) {
  const mic = area.querySelector('[data-act="mic"]');
  if (!mic) return;
  const status = area.querySelector(".status");
  const level = area.querySelector(".meter span");
  mic.addEventListener("click", async () => {
    if (mic.classList.contains("listening")) return stopRecording();
    stopVoice();
    mic.classList.add("listening");
    mic.innerHTML = ICONS.stop;
    status.textContent = tr("listening");
    try {
      const clip = await recordAnswer({ onLevel: (v) => (level.style.width = `${Math.round(v * 100)}%`) });
      mic.classList.remove("listening");
      mic.innerHTML = ICONS.mic;
      mic.disabled = true;
      status.textContent = tr("understanding");
      const r = await interpretAudio(q, clip);
      if (!r.ok || (await onResult(r)) === false) status.textContent = tr("heardNothing");
    } catch (err) {
      status.textContent = err.code === "not-allowed" || err.code === "audio-capture" ? tr("micBlocked") : tr("heardNothing");
    } finally {
      mic.classList.remove("listening");
      mic.innerHTML = ICONS.mic;
      mic.disabled = false;
    }
  });
}

function typedAnswer(q, area, existing) {
  const canSpeakAnswer = ai && canRecord();
  const placeholder = ai ? tr("typeHere") : tr("typeHereLatin");
  const inputmode = q.kind === "number" ? "tel" : q.kind === "email" ? "email" : "text";
  const prior = existing && !existing.skipped ? existing.en : "";
  area.innerHTML = `
    ${canSpeakAnswer ? micBlock() : ""}
    ${(q.suggestions || []).length ? `<div class="chips">${q.suggestions.map((s, i) => `<button class="chip" data-s="${i}">${esc(L() === "ne" ? s.ne : s.en)}</button>`).join("")}</div>` : ""}
    <div class="type-row">
      ${q.long
        ? `<textarea id="typed" placeholder="${esc(placeholder)}" rows="3">${esc(prior)}</textarea>`
        : `<input id="typed" type="text" inputmode="${inputmode}" autocomplete="off" placeholder="${esc(placeholder)}" value="${esc(prior)}">`}
    </div>
    <div class="error-line hidden" id="err"></div>
    <button class="btn primary big" data-act="done">${esc(tr("done"))}</button>`;
  const input = area.querySelector("#typed");
  const err = area.querySelector("#err");
  const showErr = (msg) => { err.textContent = msg; err.classList.remove("hidden"); };

  const handle = async (text) => {
    text = toAscii(text).trim();
    if (!text) return;
    if (hasDevanagari(text)) {
      if (!ai) return showErr(tr("latinOnly"));
      try {
        const r = await interpret(q, text);
        if (!r.ok) return showErr(tr("heardNothing"));
        bothSides(q, area, { value: r.value, said: r.said || text, en: r.en }, { onAgain: () => render() });
      } catch {
        showErr(tr("heardNothing"));
      }
      return;
    }
    if (q.kind === "email" && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(text)) return showErr(tr("badEmail"));
    if (q.kind === "number" && (text.match(/[0-9]/g) || []).length < 3) return showErr(tr("badNumber"));
    record(q, { value: text, said: text, en: text });   // typed in English letters: nothing to translate
  };

  wireMic(q, area, (r) => bothSides(q, area, { value: r.value, said: r.said, en: r.en }, { onAgain: () => render(), spoken: true }));
  area.querySelectorAll("[data-s]").forEach((b) =>
    b.addEventListener("click", () => {
      const s = q.suggestions[Number(b.dataset.s)];
      const rec = { value: s.en, said: L() === "ne" ? s.ne : s.en, en: s.en };
      L() === "ne" ? bothSides(q, area, rec) : record(q, rec);
    }),
  );
  area.querySelector('[data-act="done"]').addEventListener("click", () => handle(input.value));
  input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !q.long) handle(input.value); });
  if (!canSpeakAnswer && !matchMedia("(pointer: coarse)").matches) input.focus();
}

// -- dates: either calendar, converted exactly on the server ---------------------------

function bsToday() {
  const now = new Date();
  // BS new year falls in mid-April
  return now.getFullYear() + (now.getMonth() > 3 || (now.getMonth() === 3 && now.getDate() >= 14) ? 57 : 56);
}

function dateAnswer(q, area, existing) {
  const parts = (existing && existing.parts) || { calendar: L() === "ne" ? "BS" : "AD", year: "", month: "", day: "" };
  const canSpeakAnswer = ai && canRecord();

  const draw = () => {
    const bs = parts.calendar === "BS";
    const top = bs ? bsToday() : new Date().getFullYear();
    const years = [];
    for (let y = top; y >= top - 105; y--) years.push(y);
    const months = bs ? BS_MONTHS : L() === "ne" ? AD_MONTHS_NE : AD_MONTHS_EN;
    area.innerHTML = `
      ${canSpeakAnswer ? micBlock() : ""}
      <div class="segmented">
        <button data-cal="BS" aria-pressed="${bs}">${esc(tr("calendarBS"))}</button>
        <button data-cal="AD" aria-pressed="${!bs}">${esc(tr("calendarAD"))}</button>
      </div>
      <div class="date-grid">
        <select id="y" aria-label="${esc(tr("year"))}"><option value="">${esc(tr("year"))}</option>${years.map((y) => `<option value="${y}" ${String(y) === String(parts.year) ? "selected" : ""}>${esc(num(y))}</option>`).join("")}</select>
        <select id="m" aria-label="${esc(tr("month"))}"><option value="">${esc(tr("month"))}</option>${months.map((m, i) => `<option value="${i + 1}" ${String(i + 1) === String(parts.month) ? "selected" : ""}>${esc(m)}</option>`).join("")}</select>
        <select id="d" aria-label="${esc(tr("day"))}"></select>
      </div>
      <div class="error-line hidden" id="err"></div>
      <button class="btn primary big" data-act="done">${esc(tr("done"))}</button>`;
    const [ys, ms, ds] = ["#y", "#m", "#d"].map((s) => area.querySelector(s));
    const fillDays = async () => {
      let max = 31;
      if (bs && ys.value && ms.value) {
        try {
          const r = await fetch(`/api/dates/bs-month-length?year=${ys.value}&month=${ms.value}`);
          if (r.ok) max = (await r.json()).days;
        } catch { /* keep 31 */ }
      } else if (!bs && ys.value && ms.value) {
        max = new Date(Number(ys.value), Number(ms.value), 0).getDate();
      }
      const keep = parts.day;
      ds.innerHTML = `<option value="">${esc(tr("day"))}</option>` +
        Array.from({ length: max }, (_, i) => `<option value="${i + 1}" ${String(i + 1) === String(keep) ? "selected" : ""}>${esc(num(i + 1))}</option>`).join("");
    };
    fillDays();
    ys.addEventListener("change", () => { parts.year = ys.value; fillDays(); });
    ms.addEventListener("change", () => { parts.month = ms.value; fillDays(); });
    ds.addEventListener("change", () => { parts.day = ds.value; });
    area.querySelectorAll("[data-cal]").forEach((b) =>
      b.addEventListener("click", () => {
        if (parts.calendar === b.dataset.cal) return;
        Object.assign(parts, { calendar: b.dataset.cal, year: "", month: "", day: "" });
        draw();
      }),
    );
    area.querySelector('[data-act="done"]').addEventListener("click", () => confirmDate(parts));
    wireMic(q, area, async (r) => {
      if (!r.parts) return false;
      Object.assign(parts, r.parts);
      await confirmDate(parts, true);
    });
  };

  const confirmDate = async (p, spoken = false) => {
    const err = area.querySelector("#err");
    if (!p.year || !p.month || !p.day) {
      err.textContent = `${tr("year")} · ${tr("month")} · ${tr("day")}`;
      return err.classList.remove("hidden");
    }
    const qs = new URLSearchParams({ calendar: p.calendar, year: p.year, month: p.month, day: p.day, fmt: q.format || "MM/DD/YYYY" });
    const res = await fetch(`/api/dates/convert?${qs}`);
    if (!res.ok) {
      err.textContent = (await res.json()).detail || "Invalid date";
      return err.classList.remove("hidden");
    }
    const d = await res.json();
    bothSides(q, area, { value: d.value, said: L() === "ne" ? d.ne : d.en, en: `${d.value} (${d.en})`, parts: { ...p } }, { onAgain: draw, spoken });
  };

  draw();
}

// -- review, consent, signature ---------------------------------------------------------

function review() {
  let lastSection = null;
  const items = asked.map((q, i) => {
    const a = st.answers[q.id];
    const sec = L() === "ne" ? q.section_ne : q.section_en;
    const head = sec !== lastSection ? `<div class="review-sec">${esc(sec)}</div>` : "";
    lastSection = sec;
    const said = !a ? "—" : a.skipped ? tr("skipped") : a.said;
    const en = a && !a.skipped && L() === "ne" && a.en !== a.said ? `<div class="re" lang="en">${esc(a.en)}</div>` : "";
    const tag = a?.story ? `<span class="from-story">${esc(tr("fromStory"))}</span>` : "";
    return `${head}<button class="review-item ${a?.skipped ? "skipped" : ""}" data-i="${i}">
      <div class="rq">${esc(qText(q))}${tag}</div><div class="ra">${esc(said)}</div>${en}</button>`;
  }).join("");
  const root = screen(`
    <div class="q-top"><button class="icon-btn" data-act="back" aria-label="${esc(tr("back"))}">${ICONS.back}</button><div class="grow"></div></div>
    <h1 class="question">${esc(tr("reviewTitle"))}</h1>
    <p class="help">${esc(tr("reviewBody"))}</p>
    <div class="review-list">${items}</div>
    <div class="foot"><button class="btn primary big" data-act="next">${esc(tr("reviewDone"))}</button></div>`);
  root.querySelector('[data-act="back"]').addEventListener("click", () => {
    st.index = openIndex(asked.length - 1, -1);
    if (st.index < 0) st.index = asked.length - 1;
    go("question");
  });
  root.querySelectorAll(".review-item").forEach((b) =>
    b.addEventListener("click", () => { st.index = Number(b.dataset.i); st.returnTo = "review"; go("question"); }),
  );
  root.querySelector('[data-act="next"]').addEventListener("click", () => go((form.consent || []).length ? "consent" : "sign"));
}

function consent() {
  const cards = (form.consent || []).map((c) => {
    const title = L() === "ne" ? c.title_ne : c.title_en;
    const body = L() === "ne" ? c.ne : c.en;
    return `<div class="consent-card stack">
      <h3><span>${esc(title)}</span>${speakerButton(`${title}। ${body}`, `consent-${c.id}`)}</h3>
      <p>${esc(body)}</p>
      ${L() === "ne" ? `<details lang="en"><summary>${esc(tr("originalEnglish"))}</summary><p class="small" style="margin-top:8px">${esc(c.en)}</p></details>` : ""}
    </div>`;
  }).join("");
  const root = screen(`
    <div class="q-top"><button class="icon-btn" data-act="back" aria-label="${esc(tr("back"))}">${ICONS.back}</button><div class="grow"></div></div>
    <h1 class="question">${esc(tr("consentTitle"))}</h1>
    <p class="help">${esc(tr("consentBody"))}</p>
    <div class="stack">${cards}</div>
    <div class="foot">
      <label class="agree"><input type="checkbox" id="agree" ${st.agreed ? "checked" : ""}> ${esc(tr("understood"))}</label>
      <button class="btn primary big" data-act="next" ${st.agreed ? "" : "disabled"}>${esc(tr("next"))}</button>
    </div>`);
  wireSpeakers(root);
  const next = root.querySelector('[data-act="next"]');
  root.querySelector("#agree").addEventListener("change", (e) => { st.agreed = e.target.checked; next.disabled = !st.agreed; save(); });
  root.querySelector('[data-act="back"]').addEventListener("click", () => go("review"));
  next.addEventListener("click", () => go("sign"));
}

function suggestedSigner() {
  const part = (id) => {
    const a = st.answers[id];
    return a && !a.skipped && !hasDevanagari(a.en || "") ? a.en : "";
  };
  return [part("first_name"), part("last_name")].filter(Boolean).join(" ");
}

function todayText() {
  const d = new Date();
  return L() === "ne"
    ? `${toNe(d.getFullYear())} ${AD_MONTHS_NE[d.getMonth()]} ${toNe(d.getDate())}`
    : d.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
}

function sign() {
  if (!st.signer) st.signer = suggestedSigner();
  const root = screen(`
    <div class="q-top"><button class="icon-btn" data-act="back" aria-label="${esc(tr("back"))}">${ICONS.back}</button><div class="grow"></div>${speakerButton(tr("signBody"))}</div>
    <h1 class="question">${esc(tr("signTitle"))}</h1>
    <p class="help">${esc(tr("signBody"))}</p>
    <input id="signer" type="text" autocomplete="name" placeholder="${esc(tr("signPlaceholder"))}" value="${esc(st.signer)}" lang="en">
    <div class="error-line hidden" id="err"></div>
    <div style="margin-top:22px">
      <div class="sig-preview"><span id="preview" lang="en">${esc(st.signer)}</span></div>
      <div class="sig-meta"><span>${esc(tr("signed"))}</span><span>${esc(todayText())}</span></div>
    </div>
    <div class="foot"><button class="btn primary big" data-act="send">${esc(tr("send"))}</button></div>`);
  wireSpeakers(root);
  const input = root.querySelector("#signer");
  const err = root.querySelector("#err");
  input.addEventListener("input", () => {
    st.signer = input.value;
    root.querySelector("#preview").textContent = input.value;
    err.classList.add("hidden");
    save();
  });
  root.querySelector('[data-act="back"]').addEventListener("click", () => go((form.consent || []).length ? "consent" : "review"));
  root.querySelector('[data-act="send"]').addEventListener("click", () => {
    const name = st.signer.trim().replace(/\s+/g, " ");
    if (name.length < 2 || hasDevanagari(name)) {
      err.textContent = tr("latinOnly");
      return err.classList.remove("hidden");
    }
    st.signer = name;
    go("sending");
  });
}

async function sending() {
  const root = screen(`<div class="grow center"><div class="spinner"></div><p style="font-size:20px">${esc(tr("sending"))}</p></div>`);
  const answers = {};
  for (const q of asked) {
    const a = st.answers[q.id];
    if (a) answers[q.id] = a.skipped ? SKIP : a.value;
  }
  try {
    const res = await fetch(`/api/forms/${encodeURIComponent(FORM_ID)}/submit`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ answers, signer_name: st.signer }),
    });
    if (!res.ok) throw new Error(`submit ${res.status}`);
    const blob = await res.blob();
    const match = /filename="([^"]+)"/.exec(res.headers.get("content-disposition") || "");
    download = { url: URL.createObjectURL(blob), filename: match ? match[1] : "intake.pdf", status: res.headers.get("x-mail-status") || "saved" };
    const lang = st.lang;
    clearSaved();
    st = { ...blankState(), lang, screen: "sent" };
    render();
  } catch {
    root.innerHTML = `<div class="grow center"><p class="hero" style="font-size:26px">${esc(tr("sendFailed"))}</p></div>
      <div class="foot"><button class="btn primary big" data-act="retry">${esc(tr("retry"))}</button></div>`;
    root.querySelector('[data-act="retry"]').addEventListener("click", () => go("sending"));
  }
}

function sent() {
  if (!download) return go("welcome");
  const delivered = download.status === "sent" || download.status === "saved";
  const root = screen(`
    ${brand()}
    <div class="grow center">
      <div class="big-check">${ICONS.check}</div>
      <h1 class="hero" style="font-size:28px">${esc(delivered ? tr("sentTitle", { clinic: form.clinic_name }) : tr("savedTitle"))}</h1>
      <p style="font-size:19px">${esc(delivered ? tr("sentBody") : tr("savedBody"))}</p>
    </div>
    <div class="foot">
      <a class="btn primary big" href="${download.url}" download="${esc(download.filename)}">${esc(tr("download"))}</a>
    </div>`);
  if (speakable && st.autoRead) say(delivered ? tr("sentTitle", { clinic: form.clinic_name }) : tr("savedTitle"));
  return root;
}

// -- start -----------------------------------------------------------------------------

async function boot() {
  try {
    const [f, h] = await Promise.all([
      fetch(`/api/forms/${encodeURIComponent(FORM_ID)}`).then((r) => (r.ok ? r.json() : Promise.reject(r.status))),
      fetch("/api/health").then((r) => r.json()).catch(() => ({ ai: false })),
    ]);
    form = f;
    ai = Boolean(h.ai);
  } catch {
    screen(`${brand()}<div class="grow center"><p class="hero ne" lang="ne" style="font-size:24px">${esc(t("ne", "notActive"))}</p><p class="muted">${esc(t("en", "notActive"))}</p></div>`);
    return;
  }
  asked = form.questions.filter((q) => !AUTO_KINDS.has(q.kind));
  st = loadState();
  if (st.lang) await findVoice();
  if (["sending", "sent"].includes(st.screen)) st.screen = "review";   // never resend on reload
  render();
}

boot();
