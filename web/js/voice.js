// Voice: recording the patient's answer, Chrome speech recognition (used by /lab), and reading aloud.
// See devpost/spec.md > Voice. The recording is sent to the server, where Gemini listens to it.

const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;

export class VoiceError extends Error {
  // code: "unsupported" | "not-allowed" | "no-speech" | "audio-capture" | "network" | "aborted" | "language-not-supported"
  constructor(code, message) {
    super(message || code);
    this.code = code;
  }
}

export function canListen() {
  return Boolean(Recognition) && window.isSecureContext;
}

let active = null;

// Listen once and resolve with {text, confidence, alternatives}.
// onInterim(text) gets the words as they arrive, so the patient sees they're being heard.
export function listen({ lang = "ne-NP", onInterim, maxSeconds = 25 } = {}) {
  if (!canListen()) return Promise.reject(new VoiceError("unsupported"));
  stopListening();
  return new Promise((resolve, reject) => {
    const rec = new Recognition();
    rec.lang = lang;
    rec.interimResults = true;
    rec.maxAlternatives = 3;
    rec.continuous = true;   // older patients pause mid-sentence; we stop after a quiet gap instead
    active = rec;

    let finalText = "";
    let best = { confidence: 0, alternatives: [] };
    let quietTimer = null;
    const hardStop = setTimeout(() => rec.stop(), maxSeconds * 1000);
    const armQuiet = () => {
      clearTimeout(quietTimer);
      quietTimer = setTimeout(() => rec.stop(), 2200);
    };

    rec.onresult = (e) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i];
        if (r.isFinal) {
          finalText = `${finalText} ${r[0].transcript}`.trim();
          best = {
            confidence: r[0].confidence,
            alternatives: Array.from(r).map((a) => a.transcript.trim()),
          };
        } else {
          interim += r[0].transcript;
        }
      }
      onInterim?.(`${finalText} ${interim}`.trim());
      armQuiet();
    };
    rec.onerror = (e) => {
      clearTimeout(hardStop);
      clearTimeout(quietTimer);
      if (e.error === "no-speech" && finalText) return; // keep what we heard
      active = null;
      reject(new VoiceError(e.error === "service-not-allowed" ? "not-allowed" : e.error));
    };
    rec.onend = () => {
      clearTimeout(hardStop);
      clearTimeout(quietTimer);
      if (active !== rec) return;   // superseded or already rejected
      active = null;
      if (finalText) resolve({ text: finalText, ...best });
      else reject(new VoiceError("no-speech"));
    };
    try {
      rec.start();
      armQuiet();
    } catch (err) {
      active = null;
      reject(new VoiceError("aborted", err.message));
    }
  });
}

export function stopListening() {
  if (active) {
    try { active.stop(); } catch { /* already stopped */ }
  }
}

export function isListening() {
  return active !== null;
}

// -- recording an answer (Gemini listens to it on the server) ----------------

export function canRecord() {
  return Boolean(navigator.mediaDevices?.getUserMedia && window.MediaRecorder && window.isSecureContext);
}

let recording = null;

// Record one spoken answer and resolve with {blob, type}. Stops by itself after a quiet
// pause once the patient has spoken, or when stopRecording() is called (tapping the mic again).
// onLevel(0..1) is called many times a second so the page can show that the mic hears them.
export async function recordAnswer({ onLevel, maxSeconds = 30, quietMs = 1800, waitMs = 8000 } = {}) {
  stopRecording();
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
  } catch (err) {
    throw new VoiceError(err.name === "NotAllowedError" ? "not-allowed" : "audio-capture", err.message);
  }
  const type = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg"].find((t) => MediaRecorder.isTypeSupported(t)) || "";
  const rec = new MediaRecorder(stream, type ? { mimeType: type } : undefined);
  const ctx = new AudioContext();
  ctx.resume().catch(() => {});   // some browsers start it suspended
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 1024;
  ctx.createMediaStreamSource(stream).connect(analyser);
  const samples = new Float32Array(analyser.fftSize);
  const chunks = [];
  recording = rec;

  return new Promise((resolve, reject) => {
    const started = performance.now();
    let floor = null, heardAt = 0, lastLoud = 0;
    const tick = () => {
      analyser.getFloatTimeDomainData(samples);
      const rms = Math.sqrt(samples.reduce((sum, x) => sum + x * x, 0) / samples.length);
      const now = performance.now();
      if (now - started < 300) floor = Math.max(floor ?? 0, rms);   // the room's own noise, before they start
      const loud = rms > Math.max(0.015, (floor ?? 0) * 2.5);
      if (loud) { lastLoud = now; if (!heardAt) heardAt = now; }
      onLevel?.(Math.min(1, rms * 8));
      const done = (heardAt && now - lastLoud > quietMs) || (!heardAt && now - started > waitMs) || now - started > maxSeconds * 1000;
      if (done && rec.state !== "inactive") rec.stop();
    };
    rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    rec.onstop = () => {
      clearInterval(timer);
      stream.getTracks().forEach((t) => t.stop());
      ctx.close();
      onLevel?.(0);
      if (recording === rec) recording = null;
      if (!heardAt) return reject(new VoiceError("no-speech"));
      resolve({ blob: new Blob(chunks, { type: rec.mimeType || type }), type: rec.mimeType || type });
    };
    rec.start();
    const timer = setInterval(tick, 50);
  });
}

export function stopRecording() {
  if (recording && recording.state !== "inactive") recording.stop();
}

// -- reading aloud ----------------------------------------------------------

function loadVoices() {
  if (!("speechSynthesis" in window)) return Promise.resolve([]);
  const now = speechSynthesis.getVoices();
  if (now.length) return Promise.resolve(now);
  return new Promise((resolve) => {
    const done = () => resolve(speechSynthesis.getVoices());
    speechSynthesis.addEventListener("voiceschanged", done, { once: true });
    setTimeout(done, 1500);   // some browsers never fire the event
  });
}

export async function listVoices() {
  return (await loadVoices()).map((v) => ({ name: v.name, lang: v.lang, local: v.localService }));
}

// Nepali first; Hindi voices read Devanagari well enough as a fallback.
export async function pickVoice(preferred = ["ne", "hi"]) {
  const voices = await loadVoices();
  for (const code of preferred) {
    const matches = voices.filter((v) => v.lang.toLowerCase().replace("_", "-").startsWith(code));
    if (matches.length) {
      // prefer network voices (usually more natural), then local ones
      return matches.find((v) => !v.localService) || matches[0];
    }
  }
  return null;
}

export async function canSpeak(prefer = ["ne", "hi"]) {
  return Boolean(await pickVoice(prefer));
}

export async function speak(text, { rate = 0.9, prefer = ["ne", "hi"] } = {}) {
  const voice = await pickVoice(prefer);
  if (!voice) throw new VoiceError("unsupported", "No Nepali or Hindi voice on this device");
  speechSynthesis.cancel();
  return new Promise((resolve, reject) => {
    const u = new SpeechSynthesisUtterance(text);
    u.voice = voice;
    u.lang = voice.lang;
    u.rate = rate;
    u.onend = () => resolve(voice);
    u.onerror = (e) => (e.error === "interrupted" || e.error === "canceled" ? resolve(voice) : reject(new VoiceError(e.error)));
    speechSynthesis.speak(u);
  });
}

export function stopSpeaking() {
  if ("speechSynthesis" in window) speechSynthesis.cancel();
}

// -- icons shared by the pages ----------------------------------------------

export const ICONS = {
  mic: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></svg>',
  stop: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="7" y="7" width="10" height="10" rx="2"/></svg>',
  speaker: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 5 6 9H3v6h3l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13"/></svg>',
  back: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 18l-6-6 6-6"/></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
  keyboard: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M7 14h10"/></svg>',
};
