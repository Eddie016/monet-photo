"use strict";

const $ = (id) => document.getElementById(id);
const KEY_STORE = "monet.apiKey";
const state = { file: null, srcUrl: null, preset: "impression", strength: "medium", history: [], busy: false };

const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch {} },
};

init();

async function init() {
  const cfg = await fetch("/api/config").then((r) => r.json());
  renderRadios($("presets"), cfg.presets, "preset", (p) => `<b>${esc(p.name)}</b><small>${esc(p.works)}</small>`, "preset");
  renderRadios($("strength"), cfg.strengths.map((s) => ({ id: s })), "strength", (s) => esc(s));

  for (const [id, label] of Object.entries(cfg.backends)) $("backend").add(new Option(label, id));
  $("model").value = cfg.default_model;
  $("modelList").innerHTML = ["gemini-2.5-flash-image", "gemini-3-pro-image-preview"]
    .map((m) => `<option value="${m}">`).join("");

  const saved = store.get(KEY_STORE);
  if (saved) { $("apiKey").value = saved; $("remember").checked = true; }
  if (cfg.server_has_key) $("keyHint").insertAdjacentHTML("afterbegin", "<b>Server has a key configured</b> — leave blank to use it. ");
  // Without any key, default to the offline preview so the UI is usable immediately.
  if (!cfg.server_has_key && !saved) { $("backend").value = "preview"; $("engine").open = true; }
  syncEngine();

  ["backend", "model", "apiKey"].forEach((id) => $(id).addEventListener("input", syncEngine));
  $("remember").addEventListener("change", syncEngine);
  $("apiKey").addEventListener("change", () => {
    try { $("apiKey").value = apiKey(); status(""); loadModels(); } catch (e) { status(e.message, true); }
  });
  if (saved || cfg.server_has_key) loadModels();

  bindDrop();
  bindCompare();
  $("controls").addEventListener("submit", (e) => { e.preventDefault(); run(); });
}

function renderRadios(root, items, key, html, cls = "") {
  root.innerHTML = items.map((it) =>
    `<button type="button" role="radio" class="${cls}" data-id="${it.id}" aria-checked="${it.id === state[key]}">${html(it)}</button>`).join("");
  root.addEventListener("click", (e) => {
    const btn = e.target.closest("[role=radio]");
    if (!btn) return;
    state[key] = btn.dataset.id;
    root.querySelectorAll("[role=radio]").forEach((b) => b.setAttribute("aria-checked", b === btn));
  });
}

// Pasted keys often carry newlines, zero-width or full-width characters, which make fetch() throw
// a bare "TypeError" before the request is sent. NFKC turns full-width ASCII into normal ASCII.
function apiKey() {
  const key = $("apiKey").value.normalize("NFKC").replace(/[\s​-‍﻿]/g, "");
  if (!/^[\x21-\x7e]*$/.test(key)) throw new Error("API key has invalid characters — copy it again from AI Studio (it starts with “AIza”).");
  return key;
}

function keyHeaders() {
  const key = apiKey();
  return key ? { "X-Gemini-Key": key } : {};
}

function syncEngine() {
  const isGemini = $("backend").value === "gemini";
  $("model").disabled = $("apiKey").disabled = !isGemini;
  $("engineSummary").textContent = isGemini ? `· ${$("model").value}` : "· offline preview";
  let key = "";
  try { key = apiKey(); } catch {}
  store.set(KEY_STORE, $("remember").checked && key ? key : null);
}

async function loadModels() {
  try {
    const r = await fetch("/api/models", { headers: keyHeaders() });
    if (!r.ok) return;
    const { models } = await r.json();
    if (!models.length) return;
    $("modelList").innerHTML = models.map((m) => `<option value="${esc(m)}">`).join("");
    // Image models get retired often; if the default is gone, switch to an available (cheaper) Flash one.
    if (!models.includes($("model").value)) {
      $("model").value = models.find((m) => m.includes("flash")) || models[0];
      syncEngine();
    }
  } catch {}
}

function bindDrop() {
  const drop = $("drop");
  drop.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); $("file").click(); } });
  $("file").addEventListener("change", () => setFile($("file").files[0]));
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("over"));
  drop.addEventListener("drop", (e) => { e.preventDefault(); drop.classList.remove("over"); setFile(e.dataTransfer.files[0]); });
  window.addEventListener("paste", (e) => {
    const f = [...e.clipboardData.files].find((f) => f.type.startsWith("image/"));
    if (f) setFile(f);
  });
}

async function setFile(file) {
  if (!file) return;
  const isHeic = /\.(heic|heif)$/i.test(file.name) || /hei[cf]/.test(file.type);
  if (!isHeic && !file.type.startsWith("image/")) return status("That is not an image.", true);
  if (isHeic) {
    // Most browsers can't display HEIC, so let the server decode it once and use the JPEG from then on.
    status("Converting HEIC…");
    const fd = new FormData();
    fd.append("image", file);
    try {
      const r = await fetch("/api/convert", { method: "POST", body: fd });
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `Conversion failed (${r.status})`);
      file = new File([await r.blob()], file.name.replace(/\.\w+$/, ".jpg"), { type: "image/jpeg" });
    } catch (e) {
      return status(e.message, true);
    }
  }
  if (state.srcUrl) URL.revokeObjectURL(state.srcUrl);
  state.file = file;
  state.srcUrl = URL.createObjectURL(file);
  $("drop").classList.add("has");
  $("drop").style.backgroundImage = `url("${state.srcUrl}")`;
  $("dropText").textContent = file.name;
  $("go").disabled = false;
  showSource();
  status("");
}

function showSource() {
  const before = $("before");
  before.onload = () => {
    const ar = before.naturalWidth / before.naturalHeight;
    $("compare").style.setProperty("--ar", `${before.naturalWidth} / ${before.naturalHeight}`);
    $("compare").style.setProperty("--ar-num", ar);
  };
  before.src = state.srcUrl;
  $("empty").hidden = true;
  $("compare").hidden = false;
  showResult(null);
}

function showResult(item) {
  const has = !!item;
  $("after").hidden = $("handle").hidden = $("bar").hidden = !has;
  document.querySelectorAll(".lbl").forEach((l) => (l.hidden = !has));
  $("compare").classList.toggle("done", has);
  if (has) {
    $("before").src = item.srcUrl;
    $("after").src = item.url;
    $("download").href = item.url;
    $("download").download = `monet-${item.preset}.jpg`;
    $("meta").textContent = `${item.presetName} · ${item.strength} · ${item.backend} · ${item.seconds}s`;
    setPos(50);
  }
  document.querySelectorAll("#history button").forEach((b) => b.setAttribute("aria-current", has && b.dataset.url === item.url));
}

async function run() {
  if (!state.file || state.busy) return;
  state.busy = true;
  $("go").disabled = true;
  showSource();
  $("veil").hidden = false;
  const t0 = performance.now();
  const tick = setInterval(() => ($("veilText").textContent = `Mixing paint… ${((performance.now() - t0) / 1000).toFixed(0)}s`), 500);
  status("");

  const fd = new FormData();
  fd.append("image", state.file);
  fd.append("preset", state.preset);
  fd.append("strength", state.strength);
  fd.append("extra", $("extra").value);
  fd.append("backend", $("backend").value);
  fd.append("model", $("model").value.trim());

  try {
    const headers = $("backend").value === "gemini" ? keyHeaders() : {};
    const r = await fetch("/api/paint", { method: "POST", body: fd, headers }).catch(() => {
      throw new Error("Could not reach the local server — is monet-web still running?");
    });
    if (!r.ok) {
      const body = await r.json().catch(() => ({}));
      throw new Error(typeof body.detail === "string" ? body.detail : `Request failed (${r.status})`);
    }
    const url = URL.createObjectURL(await r.blob());
    const presetBtn = document.querySelector(`#presets [data-id="${state.preset}"] b`);
    const item = {
      url, srcUrl: state.srcUrl, preset: state.preset, presetName: presetBtn.textContent, strength: state.strength,
      backend: r.headers.get("X-Backend"), seconds: r.headers.get("X-Seconds"),
    };
    state.history.unshift(item);
    renderHistory();
    showResult(item);
  } catch (e) {
    status(e.message, true);
  } finally {
    clearInterval(tick);
    $("veil").hidden = true;
    $("veilText").textContent = "Mixing paint…";
    state.busy = false;
    $("go").disabled = false;
  }
}

function renderHistory() {
  const root = $("history");
  root.innerHTML = state.history.map((h, i) =>
    `<button type="button" data-i="${i}" data-url="${h.url}" title="${esc(h.presetName)} · ${h.strength}"><img src="${h.url}" alt=""><small>${esc(h.presetName)}</small></button>`).join("");
  root.onclick = (e) => {
    const b = e.target.closest("button");
    if (b) showResult(state.history[+b.dataset.i]);
  };
}

function bindCompare() {
  const box = $("compare");
  const at = (e) => {
    const r = box.getBoundingClientRect();
    setPos(((e.clientX - r.left) / r.width) * 100);
  };
  box.addEventListener("pointerdown", (e) => {
    if (!box.classList.contains("done")) return;
    box.setPointerCapture(e.pointerId);
    at(e);
    box.onpointermove = at;
  });
  box.addEventListener("pointerup", () => (box.onpointermove = null));
  $("handle").addEventListener("keydown", (e) => {
    const cur = parseFloat(box.style.getPropertyValue("--pos")) || 50;
    if (e.key === "ArrowLeft") setPos(cur - 5);
    else if (e.key === "ArrowRight") setPos(cur + 5);
  });
}

function setPos(p) {
  p = Math.max(0, Math.min(100, p));
  $("compare").style.setProperty("--pos", `${p}%`);
  $("handle").setAttribute("aria-valuenow", Math.round(p));
}

function status(msg, err = false) {
  $("status").textContent = msg;
  $("status").classList.toggle("err", err);
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}
