const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const folderInput = document.getElementById("folder-input");
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

let allBooks = [];
let activeGenre = "All";
let activeType = "All";
let activeStatus = "All";
let sortBy = "recent";
const searchInput = document.getElementById("search");
const sortButtons = document.getElementById("sort-buttons");
const typeChips = document.getElementById("type-chips");
const statusChips = document.getElementById("status-chips");
const genreChips = document.getElementById("genre-chips");
const libraryEmpty = document.getElementById("library-empty");
const libraryLoading = document.getElementById("library-loading");

function bookStatus(book) {
  const pct = book.num_chunks ? book.current_chunk / book.num_chunks : 0;
  if (pct <= 0) return "unstarted";
  if (pct >= (book.num_chunks - 1) / book.num_chunks) return "finished";
  return "progress";
}

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
  libraryLoading.hidden = false;
  try {
    const { books } = await api("/books");
    allBooks = books;
    renderGenreChips();
    renderLibrary();
  } catch (err) {
    toast(`Could not load your library: ${err.message}`, "error");
  } finally {
    libraryLoading.hidden = true;
  }
}

function renderSortButtons() {
  sortButtons.querySelectorAll(".chip").forEach((btn) => btn.classList.toggle("active", btn.dataset.sort === sortBy));
}

sortButtons.addEventListener("click", (e) => {
  const btn = e.target.closest(".chip");
  if (!btn) return;
  sortBy = btn.dataset.sort;
  renderSortButtons();
  renderLibrary();
});

typeChips.addEventListener("click", (e) => {
  const btn = e.target.closest(".chip");
  if (!btn) return;
  activeType = btn.dataset.type;
  typeChips.querySelectorAll(".chip").forEach((c) => c.classList.toggle("active", c === btn));
  renderLibrary();
});

statusChips.addEventListener("click", (e) => {
  const btn = e.target.closest(".chip");
  if (!btn) return;
  activeStatus = btn.dataset.status;
  statusChips.querySelectorAll(".chip").forEach((c) => c.classList.toggle("active", c === btn));
  renderLibrary();
});

function renderGenreChips() {
  const genres = [...new Set(allBooks.map((b) => b.genre).filter(Boolean))].sort();
  if (!genres.length) {
    genreChips.innerHTML = "";
    return;
  }
  const all = ["All", ...genres];
  if (!all.includes(activeGenre)) activeGenre = "All";
  genreChips.innerHTML = all
    .map((g) => `<button class="chip${g === activeGenre ? " active" : ""}" data-genre="${escapeHtml(g)}">${escapeHtml(g)}</button>`)
    .join("");
  genreChips.querySelectorAll(".chip").forEach((chip) =>
    chip.addEventListener("click", () => {
      activeGenre = chip.dataset.genre;
      renderGenreChips();
      renderLibrary();
    })
  );
}

function renderLibrary() {
  const query = searchInput.value.trim().toLowerCase();
  let books = allBooks.filter((b) => {
    if (activeGenre !== "All" && b.genre !== activeGenre) return false;
    if (activeType !== "All" && (activeType === "audio") !== !!b.is_audio) return false;
    if (activeStatus !== "All" && bookStatus(b) !== activeStatus) return false;
    if (!query) return true;
    return b.title.toLowerCase().includes(query) || (b.author || "").toLowerCase().includes(query);
  });

  books = [...books].sort((a, b) => {
    if (sortBy === "title") return a.title.localeCompare(b.title);
    if (sortBy === "author") return (a.author || "").localeCompare(b.author || "");
    if (sortBy === "progress") {
      const pctA = a.num_chunks ? a.current_chunk / a.num_chunks : 0;
      const pctB = b.num_chunks ? b.current_chunk / b.num_chunks : 0;
      const inProgressA = pctA > 0 && pctA < 1;
      const inProgressB = pctB > 0 && pctB < 1;
      if (inProgressA !== inProgressB) return inProgressA ? -1 : 1;
      return pctB - pctA;
    }
    return (b.added_at || 0) - (a.added_at || 0);
  });

  library.innerHTML = "";
  libraryEmpty.hidden = books.length > 0;

  for (const book of books) {
    const card = document.createElement("div");
    card.className = "book-card";
    const pct = book.num_chunks ? Math.round((book.current_chunk / book.num_chunks) * 100) : 0;
    const subParts = [];
    if (book.author) subParts.push(escapeHtml(book.author));
    else subParts.push(book.is_audio ? "audiobook" : book.format.toUpperCase());
    if (book.genre) subParts.push(escapeHtml(book.genre));
    const icon = book.is_audio ? "&#127911;" : "&#128214;";
    const cover = book.cover_url
      ? `<img src="${escapeHtml(book.cover_url)}" alt="" loading="lazy">`
      : `<span class="placeholder-icon">${icon}</span>`;

    card.innerHTML = `
      <div class="cover">${cover}</div>
      <div class="title">${escapeHtml(book.title)}</div>
      <div class="sub">${subParts.join(" &middot; ")}</div>
      <div class="progress-bar"><div style="width:${pct}%"></div></div>
      <button class="delete" title="delete">&times;</button>
    `;
    card.addEventListener("click", () => openBook(book));
    card.querySelector(".delete").addEventListener("click", async (e) => {
      e.stopPropagation();
      const ok = await confirmDialog(`Delete "${book.title}"? This can't be undone.`);
      if (!ok) return;
      try {
        await api(`/books/${book.id}`, { method: "DELETE" });
        toast(`Deleted "${book.title}"`);
        loadLibrary();
      } catch (err) {
        toast(`Could not delete: ${err.message}`, "error");
      }
    });
    library.appendChild(card);
  }
}

searchInput.addEventListener("input", renderLibrary);

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

const SUPPORTED_EXTENSIONS = [".txt", ".pdf", ".epub", ".mp3", ".m4a", ".m4b"];
const DROPZONE_DEFAULT_HTML = `<p>drag books or a whole folder here, or <a href="#" id="choose-files">choose files</a> / <a href="#" id="choose-folder">choose a folder</a></p>`;

function isSupported(file) {
  const name = file.name.toLowerCase();
  return SUPPORTED_EXTENSIONS.some((ext) => name.endsWith(ext));
}

dropzone.addEventListener("click", (e) => {
  if (e.target.id === "choose-folder") {
    e.preventDefault();
    folderInput.click();
    return;
  }
  e.preventDefault();
  fileInput.click();
});

dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("dragover");
});
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
dropzone.addEventListener("drop", async (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  const files = await filesFromDataTransfer(e.dataTransfer);
  if (files.length) uploadFiles(files);
});
fileInput.addEventListener("change", () => {
  if (fileInput.files.length) uploadFiles([...fileInput.files]);
  fileInput.value = "";
});
folderInput.addEventListener("change", (e) => {
  if (e.target.files.length) uploadFiles([...e.target.files]);
  e.target.value = "";
});

async function filesFromDataTransfer(dataTransfer) {
  const items = dataTransfer.items;
  if (!items || !items[0] || typeof items[0].webkitGetAsEntry !== "function") {
    return [...dataTransfer.files];
  }
  const entries = [...items].map((item) => item.webkitGetAsEntry()).filter(Boolean);
  const files = [];
  await Promise.all(entries.map((entry) => walkEntry(entry, files)));
  return files;
}

function walkEntry(entry, files) {
  return new Promise((resolve) => {
    if (entry.isFile) {
      entry.file((file) => {
        files.push(file);
        resolve();
      }, resolve);
    } else if (entry.isDirectory) {
      const reader = entry.createReader();
      const readBatch = () => {
        reader.readEntries(async (batch) => {
          if (!batch.length) {
            resolve();
            return;
          }
          await Promise.all(batch.map((child) => walkEntry(child, files)));
          readBatch();
        }, resolve);
      };
      readBatch();
    } else {
      resolve();
    }
  });
}

async function uploadFiles(files) {
  const supported = files.filter(isSupported);
  const skipped = files.length - supported.length;
  let failed = 0;

  if (!supported.length) {
    if (skipped) toast(`No supported files in that selection (${skipped} skipped).`, "error");
    return;
  }

  for (let i = 0; i < supported.length; i++) {
    const file = supported[i];
    const pct = Math.round((i / supported.length) * 100);
    dropzone.innerHTML = `
      <p>uploading ${i + 1} / ${supported.length}: ${escapeHtml(file.name)}</p>
      <div class="upload-progress"><div style="width:${pct}%"></div></div>
    `;
    const form = new FormData();
    form.append("file", file);
    try {
      await api("/books", { method: "POST", body: form });
    } catch (err) {
      failed++;
      console.error(`Upload failed for ${file.name}: ${err.message}`);
    }
  }

  dropzone.innerHTML = DROPZONE_DEFAULT_HTML;
  loadLibrary();

  const added = supported.length - failed;
  if (!failed && !skipped) {
    toast(`Added ${added} book${added === 1 ? "" : "s"} to your library.`);
  } else {
    const parts = [`Added ${added} book${added === 1 ? "" : "s"}`];
    if (failed) parts.push(`${failed} failed`);
    if (skipped) parts.push(`${skipped} skipped (unsupported type)`);
    toast(parts.join(", "), failed ? "error" : "info");
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
    toast(`Cast failed: ${err.message}`, "error");
    resetCastUI();
  }
}

castBtn.addEventListener("click", async () => {
  if (!current) return;
  if (casting) {
    try {
      await api(`/books/${current.id}/cast/stop`, { method: "POST" });
    } catch (err) {
      toast(`Could not stop casting cleanly: ${err.message}`, "error");
    }
    resetCastUI();
    await showChunk(current.index);
    return;
  }
  const prevLabel = castBtn.textContent;
  castBtn.textContent = "finding devices...";
  try {
    const { devices } = await api("/cast/devices");
    if (!devices.length) {
      toast("No Cast devices found on the network. Try again — mDNS discovery can be flaky.", "error");
      castBtn.textContent = prevLabel;
      return;
    }
    castDevices.innerHTML =
      `<option value="" disabled selected>pick a speaker...</option>` +
      devices.map((d) => `<option value="${escapeHtml(d.name)}">${escapeHtml(d.name)}</option>`).join("");
    castDevices.hidden = false;
    castBtn.textContent = prevLabel;
  } catch (err) {
    toast(`Could not list cast devices: ${err.message}`, "error");
    castBtn.textContent = prevLabel;
  }
});

castDevices.addEventListener("change", () => startCast(castDevices.value));

const toastContainer = document.getElementById("toast-container");

function toast(message, type = "info") {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  toastContainer.appendChild(el);
  setTimeout(() => {
    el.classList.add("fade-out");
    setTimeout(() => el.remove(), 250);
  }, 3500);
}

const confirmOverlay = document.getElementById("confirm-overlay");
const confirmMessage = document.getElementById("confirm-message");
const confirmOk = document.getElementById("confirm-ok");
const confirmCancel = document.getElementById("confirm-cancel");

function confirmDialog(message) {
  confirmMessage.textContent = message;
  confirmOverlay.hidden = false;
  return new Promise((resolve) => {
    const cleanup = (result) => {
      confirmOverlay.hidden = true;
      confirmOk.removeEventListener("click", onOk);
      confirmCancel.removeEventListener("click", onCancel);
      confirmOverlay.removeEventListener("click", onOverlay);
      resolve(result);
    };
    const onOk = () => cleanup(true);
    const onCancel = () => cleanup(false);
    const onOverlay = (e) => {
      if (e.target === confirmOverlay) cleanup(false);
    };
    confirmOk.addEventListener("click", onOk);
    confirmCancel.addEventListener("click", onCancel);
    confirmOverlay.addEventListener("click", onOverlay);
  });
}

renderSortButtons();
loadVoices();
loadLibrary();
