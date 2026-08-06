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

let current = null; // { id, num_chunks, index, voice, rate }
let isPlaying = false;

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
    card.innerHTML = `
      <div style="flex:1">
        <div class="title">${escapeHtml(book.title)}</div>
        <div class="sub">${book.format.toUpperCase()} &middot; ${book.num_chunks} sections &middot; ${pct}% done</div>
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
  current = { id: book.id, num_chunks: book.num_chunks, index: book.current_chunk, voice: book.voice, rate: book.rate };
  voiceSelect.value = book.voice;
  rateSelect.value = book.rate;
  reader.classList.add("active");
  readerTitle.textContent = book.title;
  await showChunk(current.index);
}

async function showChunk(index) {
  const { text } = await api(`/books/${current.id}/chunks/${index}`);
  readerText.textContent = text;
  chunkCounter.textContent = `${index + 1} / ${current.num_chunks}`;
  prevBtn.disabled = index === 0;
  nextBtn.disabled = index === current.num_chunks - 1;
  current.index = index;
  await api(`/books/${current.id}/progress?current_chunk=${index}`, { method: "PATCH" });

  const wasPlaying = isPlaying;
  player.pause();
  player.src = audioUrl(index);
  if (wasPlaying) play();
}

function audioUrl(index) {
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
prevBtn.addEventListener("click", () => current.index > 0 && showChunk(current.index - 1));
nextBtn.addEventListener("click", () => current.index < current.num_chunks - 1 && showChunk(current.index + 1));
backBtn.addEventListener("click", () => {
  pause();
  reader.classList.remove("active");
  current = null;
  loadLibrary();
});

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
    dropzone.innerHTML = `<p>drag a .txt / .pdf / .epub here, or click to choose</p>`;
    loadLibrary();
  }
}

loadVoices();
loadLibrary();
