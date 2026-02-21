import { api } from "./api.js";
import { initPlayer, playClip, formatSeconds } from "./videoplayer.js";

const videoEl = document.getElementById("main-video");
if (videoEl) initPlayer(videoEl);

let currentVideoId = null;
let currentVideoSrc = null;
let chaptersData = [];

// ── Load data ────────────────────────────────────────────────────────────────
async function loadPatientView(videoId) {
  currentVideoId = videoId;
  document.getElementById("video-id-display").textContent = videoId;

  await Promise.all([loadGist(videoId), loadSummary(videoId), loadChapters(videoId)]);
}

async function loadGist(videoId) {
  const el = document.getElementById("topics-area");
  el.innerHTML = '<span class="loading">Loading topics...</span>';
  try {
    const data = await api.getGist(videoId);
    const chips = [...(data.topics || [])].map(t => `<span class="chip">${t}</span>`).join("");
    el.innerHTML = chips || '<span class="loading">No topics found.</span>';
    document.getElementById("visit-title").textContent = data.title || "Your Visit Summary";
  } catch (e) {
    el.innerHTML = `<span class="error">${e.message}</span>`;
  }
}

async function loadSummary(videoId) {
  const el = document.getElementById("summary-area");
  const medEl = document.getElementById("medication-area");
  el.innerHTML = '<span class="loading">Generating your summary...</span>';

  try {
    const data = await api.getSummary(videoId);
    el.innerHTML = `<p class="summary-text">${data.summary}</p>`;

    if (data.medication_plan) {
      const plan = data.medication_plan;
      let html = `
        <div class="medication-plan">
          <div class="badge">✓ Doctor Verified Medication Plan</div>`;
      if (plan.override_text) {
        html += `<p>${plan.override_text}</p>`;
      } else {
        (plan.medications || []).forEach(m => {
          html += `<div class="medication-item">
            <strong>${m.name}</strong>
            <span>${[m.dosage, m.frequency, m.purpose].filter(Boolean).join(" · ")}</span>
            ${m.instructions ? `<span style="display:block;color:#4a5568;font-size:0.85rem">${m.instructions}</span>` : ""}
          </div>`;
        });
      }
      html += `<p style="font-size:0.78rem;color:#276749;margin-top:0.6rem">Reviewed by your doctor</p></div>`;
      medEl.innerHTML = html;
    } else {
      medEl.innerHTML = `<p style="color:#718096;font-size:0.9rem">Your medication plan is being reviewed by your doctor and will appear here shortly.</p>`;
    }
  } catch (e) {
    el.innerHTML = `<span class="error">${e.message}</span>`;
  }
}

async function loadChapters(videoId) {
  const el = document.getElementById("chapters-area");
  el.innerHTML = '<span class="loading">Loading chapters...</span>';
  try {
    const data = await api.getChapters(videoId);
    chaptersData = data.chapters || [];
    if (!chaptersData.length) {
      el.innerHTML = '<span class="loading">No chapters available yet.</span>';
      return;
    }
    el.innerHTML = `<ul class="chapter-list">${chaptersData.map((ch, i) => `
      <li data-start="${ch.start}" data-end="${ch.end}">
        <span class="chapter-ts">${formatSeconds(ch.start)}</span>
        <span class="chapter-title">${ch.chapter_title}</span>
        <button class="go-btn" onclick="jumpToChapter(${i})">Go</button>
      </li>`).join("")}</ul>`;
  } catch (e) {
    el.innerHTML = `<span class="error">${e.message}</span>`;
  }
}

// ── Playback ─────────────────────────────────────────────────────────────────
window.jumpToChapter = function (index) {
  const ch = chaptersData[index];
  if (!ch) return;
  playClip(ch.start, ch.end, currentVideoSrc);
};

// ── Search ───────────────────────────────────────────────────────────────────
document.getElementById("search-btn")?.addEventListener("click", doSearch);
document.getElementById("search-input")?.addEventListener("keydown", e => {
  if (e.key === "Enter") doSearch();
});

async function doSearch() {
  const query = document.getElementById("search-input").value.trim();
  if (!query) return;
  const el = document.getElementById("search-results");
  el.innerHTML = '<span class="loading">Searching...</span>';

  const apptId = document.getElementById("appointment-id-input")?.value;

  try {
    const data = await api.search(query, apptId, null);
    const clips = data.results || [];
    if (!clips.length) {
      el.innerHTML = '<span class="loading">No results found.</span>';
      return;
    }
    el.innerHTML = clips.map(clip => `
      <div class="clip-result">
        <p class="quote">"${clip.transcription || "..."}"</p>
        <p class="ts-label">${formatSeconds(clip.start)} – ${formatSeconds(clip.end)}</p>
        <button class="play-clip-btn" onclick="playSearchClip(${clip.start}, ${clip.end})">
          ▶ Play Clip
        </button>
      </div>`).join("");
  } catch (e) {
    el.innerHTML = `<span class="error">${e.message}</span>`;
  }
}

window.playSearchClip = function (start, end) {
  playClip(start, end, currentVideoSrc);
};

// ── Init ─────────────────────────────────────────────────────────────────────
const params = new URLSearchParams(location.search);
const videoId = params.get("video_id");
if (videoId) {
  loadPatientView(videoId);
} else {
  document.getElementById("main-content").innerHTML = `
    <div class="card">
      <h2>Enter your video ID</h2>
      <div style="display:flex;gap:0.5rem">
        <input id="vid-input" placeholder="Video ID from your doctor..." style="flex:1;padding:0.6rem;border:1.5px solid #cbd5e0;border-radius:8px">
        <button onclick="location.search='?video_id='+document.getElementById('vid-input').value"
          style="background:#2b6cb0;color:white;border:none;border-radius:8px;padding:0.6rem 1rem;cursor:pointer">Go</button>
      </div>
    </div>`;
}
