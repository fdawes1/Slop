const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const library = document.getElementById("library");
const reader = document.getElementById("reader");
const readerTitle = document.getElementById("reader-title");
const readerText = document.getElementById("reader-text");
const playBtn = document.getElementById("play");
const prevBtn = document.getElementById("prev");
const nextBtn = document.getElementById("next");
const voiceSelect = document.getElementById("voice");
const rateSelect = document.getElementById("rate");
const chunkCounter = document.getElementById("chunk-counter");
const player = document.getElementById("player");
const backBtn = document.getElementById("back");
const castBtn = document.getElementById("cast-btn");
const castDevices = document.getElementById("cast-devices");
const castStatusEl = document.getElementById("cast-status");

let current = null; // { id, num_chunks, index, voice, rate }
let isPlaying = false;
let casting = false;
let castPollTimer = null;
let castDeviceName = null;

async function api(path, opts = {}) {
  const res = await fetch(`/api${path}`, opts);
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.headers.get("content-type")?.includes("application/json") ? res.json() : res;
}

async function loadVoices() {
  const { voices, default: def } = await api("/voices");
  voiceSelect.innerHTML = "";
  for (const [id, label] of Object.entries(voices)) {
    const opt = document.createElement("option");
    opt.value = id;
    opt.textContent = label;
    if (id === def) opt.selected = true;
    voiceSelect.appendChild(opt);
  }
}

async function loadLibrary() {
  const { books } = await api("/books");
  library.innerHTML = "";
  for (const book of books) {
    const card = document.createElement("div");
    card.className = "book-card";
    const pct = book.num_chunks ? Math.round((book.current_chunk / book.num_chunks) * 100) : 0;
    const sub = book.is_audio
      ? `${book.format.toUpperCase()} &middot; audiobook`
      : `${book.format.toUpperCase()} &middot; ${book.num_chunks} sections &middot; ${pct}% done`;
    card.innerHTML = `
      <div style="flex:1">
        <div class="title">${escapeHtml(book.title)}</div>
        <div class="sub">${sub}</div>
        <div class="progress-bar"><div style="width:${pct}%"></div></div>
      </div>
      <button class="delete" title="delete">&times;</button>
    `;
    card.addEventListener("click", () => openBook(book));
    card.querySelector(".delete").addEventListener("click", async (e) => {
      e.stopPropagation();
      if (!confirm(`Delete "${book.title}"?`)) return;
      await api(`/books/${book.id}`, { method: "DELETE" });
      loadLibrary();
    });
    library.appendChild(card);
  }
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

async function openBook(book) {
  current = {
    id: book.id,
    num_chunks: book.num_chunks,
    index: book.current_chunk,
    voice: book.voice,
    rate: book.rate,
    isAudio: book.is_audio,
  };
  voiceSelect.value = book.voice;
  rateSelect.value = book.rate;
  reader.classList.add("active");
  readerTitle.textContent = book.title;

  const ttsOnly = [prevBtn, nextBtn, voiceSelect, rateSelect, chunkCounter];
  ttsOnly.forEach((el) => (el.style.display = book.is_audio ? "none" : ""));
  readerText.style.display = book.is_audio ? "none" : "";

  resetCastUI();
  await showChunk(current.index);
  await syncCastStatus();
}

async function showChunk(index, { loadAudio = true } = {}) {
  if (!current.isAudio) {
    const { text } = await api(`/books/${current.id}/chunks/${index}`);
    readerText.textContent = text;
    chunkCounter.textContent = `${index + 1} / ${current.num_chunks}`;
    prevBtn.disabled = index === 0;
    nextBtn.disabled = index === current.num_chunks - 1;
  }
  current.index = index;
  await api(`/books/${current.id}/progress?current_chunk=${index}`, { method: "PATCH" });

  if (!loadAudio) return;
  const wasPlaying = isPlaying;
  player.pause();
  player.src = audioUrl(index);
  if (wasPlaying) play();
}

function audioUrl(index) {
  if (current.isAudio) return `/api/books/${current.id}/audio/${index}`;
  const v = encodeURIComponent(voiceSelect.value);
  const r = encodeURIComponent(rateSelect.value);
  return `/api/books/${current.id}/audio/${index}?voice=${v}&rate=${r}`;
}

function play() {
  player.play();
  isPlaying = true;
  playBtn.textContent = "pause";
}

function pause() {
  player.pause();
  isPlaying = false;
  playBtn.textContent = "play";
}

playBtn.addEventListener("click", () => (isPlaying ? pause() : play()));
prevBtn.addEventListener("click", () => current.index > 0 && jumpTo(current.index - 1));
nextBtn.addEventListener("click", () => current.index < current.num_chunks - 1 && jumpTo(current.index + 1));
backBtn.addEventListener("click", () => {
  pause();
  clearInterval(castPollTimer);
  castPollTimer = null;
  reader.classList.remove("active");
  current = null;
  loadLibrary();
});

async function jumpTo(index) {
  if (casting) {
    await showChunk(index, { loadAudio: false });
    startCast(castDeviceName);
  } else {
    showChunk(index);
  }
}

player.addEventListener("ended", () => {
  if (current && current.index < current.num_chunks - 1) {
    showChunk(current.index + 1).then(play);
  } else {
    pause();
  }
});

[voiceSelect, rateSelect].forEach((el) =>
  el.addEventListener("change", async () => {
    if (!current) return;
    await api(`/books/${current.id}/settings?voice=${encodeURIComponent(voiceSelect.value)}&rate=${encodeURIComponent(rateSelect.value)}`, {
      method: "PATCH",
    });
    showChunk(current.index);
  })
);

dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("dragover");
});
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  if (e.dataTransfer.files.length) uploadFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener("change", () => {
  if (fileInput.files.length) uploadFile(fileInput.files[0]);
});

async function uploadFile(file) {
  const form = new FormData();
  form.append("file", file);
  dropzone.textContent = `uploading ${file.name}...`;
  try {
    await api("/books", { method: "POST", body: form });
  } catch (err) {
    alert(`Upload failed: ${err.message}`);
  } finally {
    dropzone.innerHTML = `<p>drag a .txt / .pdf / .epub / .mp3 / .m4a / .m4b here, or click to choose</p>`;
    loadLibrary();
  }
}

function resetCastUI() {
  casting = false;
  castDeviceName = null;
  clearInterval(castPollTimer);
  castPollTimer = null;
  castBtn.textContent = "\u{1F4E1} cast";
  castBtn.classList.remove("primary");
  castDevices.hidden = true;
  castDevices.innerHTML = "";
  castStatusEl.textContent = "";
}

async function syncCastStatus() {
  if (!current) return;
  const status = await api(`/books/${current.id}/cast/status`);
  if (!status.casting) return;
  casting = true;
  castDeviceName = status.device;
  castBtn.textContent = "\u{1F4E1} stop cast";
  castBtn.classList.add("primary");
  castStatusEl.textContent = `casting to ${status.device}`;
  pause();
  if (status.index !== current.index) await showChunk(status.index, { loadAudio: false });
  startCastPolling();
}

function startCastPolling() {
  clearInterval(castPollTimer);
  castPollTimer = setInterval(async () => {
    if (!current) return;
    try {
      const status = await api(`/books/${current.id}/cast/status`);
      if (!status.casting) {
        resetCastUI();
        return;
      }
      if (status.index !== current.index) await showChunk(status.index, { loadAudio: false });
    } catch {
      resetCastUI();
    }
  }, 3000);
}

async function startCast(deviceName) {
  if (!deviceName || !current) return;
  pause();
  castBtn.textContent = "connecting...";
  castDevices.hidden = true;
  try {
    const result = await api(
      `/books/${current.id}/cast?device_name=${encodeURIComponent(deviceName)}&index=${current.index}`,
      { method: "POST" }
    );
    casting = true;
    castDeviceName = result.device;
    castBtn.textContent = "\u{1F4E1} stop cast";
    castBtn.classList.add("primary");
    castStatusEl.textContent = `casting to ${result.device}`;
    startCastPolling();
  } catch (err) {
    alert(`Cast failed: ${err.message}`);
    resetCastUI();
  }
}

castBtn.addEventListener("click", async () => {
  if (!current) return;
  if (casting) {
    await api(`/books/${current.id}/cast/stop`, { method: "POST" });
    resetCastUI();
    return;
  }
  const prevLabel = castBtn.textContent;
  castBtn.textContent = "finding devices...";
  try {
    const { devices } = await api("/cast/devices");
    if (!devices.length) {
      alert("No Cast devices found on the network.");
      castBtn.textContent = prevLabel;
      return;
    }
    castDevices.innerHTML =
      `<option value="" disabled selected>pick a speaker...</option>` +
      devices.map((d) => `<option value="${escapeHtml(d.name)}">${escapeHtml(d.name)}</option>`).join("");
    castDevices.hidden = false;
    castBtn.textContent = prevLabel;
  } catch (err) {
    alert(`Could not list cast devices: ${err.message}`);
    castBtn.textContent = prevLabel;
  }
});

castDevices.addEventListener("change", () => startCast(castDevices.value));

loadVoices();
loadLibrary();
