// Clinic side: setup → reading → converting → review and edit → published link.
// See devpost/prd.md > Clinic Setup and Conversion and devpost/spec.md > Clinic Pages.

import { ICONS } from "./voice.js";

const view = document.getElementById("view");
const params = new URLSearchParams(location.search);
const KEYS = "saathi-clinic";
const KIND_LABEL = {
  text: "Typed or spoken", name: "Name", date: "Date", number: "Number", code: "ID / code", email: "Email",
  yesno: "Yes / No", choice: "One choice", multi: "Choose all", scale: "0–10 scale",
  signature: "Signature", auto_date: "Filled automatically: today's date", auto_name: "Filled automatically: signer's name",
  skip: "Left blank (office or other signer)",
};
const AUTO = new Set(["signature", "auto_date", "auto_name", "skip"]);

let form = null;
let editKey = null;

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

function keys() {
  try { return JSON.parse(localStorage.getItem(KEYS) || "{}"); } catch { return {}; }
}
function remember(id, key) {
  try { localStorage.setItem(KEYS, JSON.stringify({ ...keys(), [id]: key })); } catch { /* keep it in memory */ }
}

async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (editKey) headers["x-edit-key"] = editKey;
  const res = await fetch(path, { ...opts, headers });
  const body = res.headers.get("content-type")?.includes("json") ? await res.json() : null;
  if (!res.ok) throw new Error(body?.detail || `Something went wrong (${res.status}).`);
  return body;
}

// -- 1. setup ---------------------------------------------------------------------

function setup(error = "") {
  view.innerHTML = `
    <h1 style="font-size:40px;max-width:720px">Let Nepali-speaking patients fill your intake form themselves.</h1>
    <p class="lead">Upload the fillable PDF you already use. Saathi turns every box into a plain question in Nepali, read aloud and answered by voice or tap, and emails you the same PDF, filled in English.</p>
    ${error ? `<div class="error-box" style="margin:18px 0">${esc(error)}</div>` : ""}
    <form id="setup" class="card stack" style="margin-top:24px">
      <div class="grid2">
        <label class="field"><span>Clinic name</span><input type="text" name="clinic_name" required minlength="2" placeholder="Riverbend Physical Therapy"></label>
        <label class="field"><span>Email for completed forms</span><input type="email" name="clinic_email" required placeholder="frontdesk@clinic.com"></label>
      </div>
      <label class="drop" id="drop">
        <input type="file" name="pdf" accept="application/pdf,.pdf" hidden required>
        <strong id="fname">Choose your intake form (PDF)</strong>
        <span class="muted small">or drop it here · fillable PDFs only</span>
      </label>
      <div class="row wrap spread">
        <button type="button" class="btn link" id="use-sample">Use the sample PT intake form</button>
        <button class="btn primary" type="submit">Convert to Nepali</button>
      </div>
    </form>
    <p class="muted small" style="margin-top:14px">Want to see the patient side first? <a href="/f/sample">Open the sample form as a patient</a>.</p>`;
  const f = view.querySelector("#setup");
  const fileInput = f.querySelector('input[type="file"]');
  const drop = view.querySelector("#drop");
  const showName = () => (view.querySelector("#fname").textContent = fileInput.files[0]?.name || "Choose your intake form (PDF)");
  fileInput.addEventListener("change", showName);
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("over"));
  drop.addEventListener("drop", (e) => {
    e.preventDefault();
    drop.classList.remove("over");
    if (e.dataTransfer.files.length) { fileInput.files = e.dataTransfer.files; showName(); }
  });
  view.querySelector("#use-sample").addEventListener("click", async () => {
    const blob = await (await fetch("/samples/pt-intake.pdf")).blob();
    const dt = new DataTransfer();
    dt.items.add(new File([blob], "riverbend-pt-intake-sample.pdf", { type: "application/pdf" }));
    fileInput.files = dt.files;
    showName();
    if (!f.clinic_name.value) f.clinic_name.value = "Riverbend Physical Therapy";
  });
  f.addEventListener("submit", (e) => {
    e.preventDefault();
    if (!fileInput.files.length) return setup("Please choose your intake form as a PDF.");
    run(new FormData(f));
  });
}

// -- 2. reading and converting --------------------------------------------------------

function progress(steps) {
  view.innerHTML = `
    <h1>Preparing your form</h1>
    <p class="lead">This takes about a minute. Gemini writes each question in plain Nepali.</p>
    <ul class="steps card" style="margin-top:20px">${steps.map((s) => `
      <li class="${s.state}"><span class="dot">${s.state === "done" ? ICONS.check : ""}</span>${esc(s.label)}<span class="muted">${esc(s.note || "")}</span></li>`).join("")}
    </ul>`;
}

async function run(data) {
  const steps = [
    { label: "Upload the PDF", state: "doing" },
    { label: "Find every fillable box and its printed label", state: "" },
    { label: "Write plain questions in English and Nepali", state: "" },
  ];
  progress(steps);
  let created;
  try {
    created = await api("/api/forms", { method: "POST", body: data });
  } catch (err) {
    return setup(err.message);
  }
  editKey = created.edit_key;
  remember(created.id, created.edit_key);
  history.replaceState(null, "", `/clinic?form=${created.id}`);
  steps[0].state = "done";
  steps[1].state = "done";
  steps[1].note = `${created.box_count} boxes on ${created.pages} pages`;
  steps[2].state = "doing";
  steps[2].note = "Gemini";
  progress(steps);
  await convert(created.id, steps);
}

async function convert(id, steps) {
  try {
    form = await api(`/api/forms/${id}/convert`, { method: "POST" });
    review();
  } catch (err) {
    steps[2].state = "";
    progress(steps);
    view.insertAdjacentHTML("beforeend", `
      <div class="error-box" style="margin-top:18px">${esc(err.message)}</div>
      <div class="row" style="margin-top:14px"><button class="btn primary" id="retry">Try again</button><a class="btn" href="/clinic">Start over</a></div>`);
    view.querySelector("#retry").addEventListener("click", () => { steps[2].state = "doing"; progress(steps); convert(id, steps); });
  }
}

// -- 3. review and edit -----------------------------------------------------------------

let saveTimer = null;
const pending = { questions: {}, consent: {} };

function queueSave(kind, id, key, value) {
  pending[kind][id] = { ...(pending[kind][id] || {}), id, [key]: value };
  view.querySelector("#saved").textContent = "Saving…";
  clearTimeout(saveTimer);
  saveTimer = setTimeout(flush, 600);
}

async function flush() {
  const body = { questions: Object.values(pending.questions), consent: Object.values(pending.consent) };
  pending.questions = {};
  pending.consent = {};
  try {
    form = await api(`/api/forms/${form.id}`, { method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
    view.querySelector("#saved").textContent = "All changes saved";
  } catch (err) {
    view.querySelector("#saved").textContent = err.message;
  }
}

function review() {
  if (form.status === "published") return published(`${location.origin}/f/${form.id}`);
  const asked = form.questions.filter((q) => !AUTO.has(q.kind));
  const auto = form.questions.length - asked.length;
  const flagged = form.questions.filter((q) => q.needs_review).length;
  let lastSec = null;
  const rows = form.questions.map((q) => {
    const sec = q.section_en;
    const head = sec !== lastSec ? `<div class="sec-title">${esc(sec)} <span class="ne">${esc(q.section_ne)}</span></div>` : "";
    lastSec = sec;
    const opts = (q.options || []).length && !["scale"].includes(q.kind)
      ? `<div class="opts">${q.options.map((o) => `<span>${esc(o.en)} · <span class="ne">${esc(o.ne)}</span></span>`).join("")}</div>` : "";
    if (AUTO.has(q.kind)) {
      return `${head}<div class="qrow auto"><div class="meta"><span class="tag quiet">${esc(KIND_LABEL[q.kind])}</span><span class="from">PDF box: ${esc(q.fields.join(", "))}</span></div></div>`;
    }
    return `${head}<div class="qrow ${q.needs_review ? "review" : ""}" data-id="${esc(q.id)}">
      <div class="meta"><span class="tag">${esc(KIND_LABEL[q.kind] || q.kind)}</span>${q.optional ? '<span class="tag quiet">Optional</span>' : ""}${q.needs_review ? '<span class="tag">Needs your wording</span>' : ""}<span class="from">PDF box: ${esc(q.fields.length > 1 ? `${q.fields.length} checkboxes` : q.fields[0])}</span></div>
      <label class="field"><span>English</span><textarea data-k="en" rows="2">${esc(q.en)}</textarea></label>
      <label class="field"><span>Nepali</span><textarea class="ne" lang="ne" data-k="ne" rows="2">${esc(q.ne)}</textarea></label>
      ${opts}
    </div>`;
  }).join("");
  const consent = (form.consent || []).map((c) => `
    <div class="qrow" data-cid="${esc(c.id)}">
      <div class="meta"><span class="tag">Consent</span><strong>${esc(c.title_en)}</strong></div>
      <div class="small muted">${esc(c.en)}</div>
      <label class="field"><span>Plain Nepali explanation the patient reads</span><textarea class="ne" lang="ne" data-k="ne" rows="5">${esc(c.ne)}</textarea></label>
    </div>`).join("");
  view.innerHTML = `
    <h1>Check the Nepali questions</h1>
    <p class="lead">Every box on <strong>${esc(form.file_name || "your form")}</strong> is covered. Fix any wording, then publish to get the link for your patients.</p>
    <div class="stats card" style="margin-top:18px">
      <div class="stat"><b>${asked.length}</b><span>questions patients answer</span></div>
      <div class="stat"><b>${(form.consent || []).length}</b><span>consent sections explained</span></div>
      <div class="stat"><b>${auto}</b><span>boxes filled automatically</span></div>
      <div class="stat"><b>${form.box_count ?? "—"}</b><span>PDF boxes covered</span></div>
    </div>
    ${flagged ? `<div class="notice" style="margin-top:14px">${flagged} question${flagged > 1 ? "s" : ""} need your wording (dashed outline).</div>` : ""}
    <div>${rows}</div>
    ${consent ? `<div class="sec-title">Consent <span class="ne">सहमति</span></div>${consent}` : ""}
    <div class="sticky">
      <button class="btn primary" id="publish">Publish and get the patient link</button>
      <a class="btn quiet" href="/f/${esc(form.id)}?preview=1" id="preview" target="_blank">Preview as patient</a>
      <span class="saved" id="saved">All changes saved</span>
    </div>`;
  view.querySelectorAll(".qrow[data-id] textarea").forEach((t) =>
    t.addEventListener("input", () => queueSave("questions", t.closest(".qrow").dataset.id, t.dataset.k, t.value)),
  );
  view.querySelectorAll(".qrow[data-cid] textarea").forEach((t) =>
    t.addEventListener("input", () => queueSave("consent", t.closest(".qrow").dataset.cid, t.dataset.k, t.value)),
  );
  view.querySelector("#preview").addEventListener("click", (e) => {
    if (form.status !== "published") {
      e.preventDefault();
      view.querySelector("#saved").textContent = "Publish first: the patient link only works once it's published.";
    }
  });
  view.querySelector("#publish").addEventListener("click", async () => {
    clearTimeout(saveTimer);
    await flush();
    try {
      const { link } = await api(`/api/forms/${form.id}/publish`, { method: "POST" });
      form.status = "published";
      published(link);
    } catch (err) {
      view.querySelector("#saved").textContent = err.message;
    }
  });
}

// -- 4. published --------------------------------------------------------------------

function published(link) {
  view.innerHTML = `
    <div class="big-check" style="width:72px;height:72px;border-radius:50%;background:#000;color:#fff;display:flex;align-items:center;justify-content:center">${ICONS.check}</div>
    <h1 style="margin-top:18px">Your Nepali form is live</h1>
    <p class="lead">Send this link to Nepali-speaking patients before their first visit, by text or email. Completed forms arrive at <strong>${esc(form.clinic_email)}</strong> as your own PDF, filled in English.</p>
    <div class="linkbox" style="margin-top:20px"><code id="link">${esc(link)}</code><button class="btn primary" id="copy">Copy link</button></div>
    <div class="row wrap" style="margin-top:16px">
      <a class="btn" href="${esc(link)}" target="_blank">Open as a patient</a>
      <button class="btn quiet" id="edit">Edit the wording</button>
      <a class="btn link" href="/clinic">Set up another form</a>
    </div>`;
  view.querySelector(".big-check svg").setAttribute("style", "width:40px;height:40px");
  view.querySelector("#copy").addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(link); view.querySelector("#copy").textContent = "Copied"; } catch { /* select instead */ }
  });
  view.querySelector("#edit").addEventListener("click", () => { form.status = "draft-view"; review(); form.status = "published"; });
}

// -- start -------------------------------------------------------------------------------

async function boot() {
  const id = params.get("form");
  if (!id) return setup();
  editKey = keys()[id];
  if (!editKey) return setup("This browser didn't set up that form, so it can't edit it.");
  try {
    form = await api(`/api/clinic/forms/${id}`);
  } catch (err) {
    return setup(err.message);
  }
  if (form.status === "reading") {
    const steps = [
      { label: "Upload the PDF", state: "done" },
      { label: "Find every fillable box and its printed label", state: "done", note: `${form.box_count} boxes on ${form.pages} pages` },
      { label: "Write plain questions in English and Nepali", state: "doing", note: "Gemini" },
    ];
    progress(steps);
    return convert(id, steps);
  }
  review();
}

boot();
