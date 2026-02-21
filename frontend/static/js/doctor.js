import { api } from "./api.js";
import { initPlayer, playClip, formatSeconds } from "./videoplayer.js";

const videoEl = document.getElementById("main-video");
if (videoEl) initPlayer(videoEl);

// ── Upload ───────────────────────────────────────────────────────────────────
document.getElementById("upload-form")?.addEventListener("submit", async e => {
  e.preventDefault();
  const form = e.target;
  const status = document.getElementById("upload-status");
  status.textContent = "Uploading...";
  status.className = "loading";

  const fd = new FormData(form);
  try {
    const result = await api.upload(fd);
    status.textContent = `Uploaded! Task ID: ${result.task_id} | Video ID: ${result.video_id} — Indexing in progress. This may take a few minutes.`;
    status.className = "success";
    form.reset();
    pollStatus(result.task_id);
  } catch (e) {
    status.textContent = `Error: ${e.message}`;
    status.className = "error";
  }
});

async function pollStatus(taskId) {
  const el = document.getElementById("upload-status");
  const interval = setInterval(async () => {
    try {
      const s = await api.uploadStatus(taskId);
      if (s.status === "ready") {
        clearInterval(interval);
        el.textContent = `Indexing complete! Video ID: ${s.video_id}. Medication review available below.`;
        loadPendingReviews();
      } else if (s.status === "failed") {
        clearInterval(interval);
        el.textContent = "Indexing failed. Please try again.";
        el.className = "error";
      }
    } catch (_) { /* ignore poll errors */ }
  }, 10000);
}

// ── Pending Reviews ───────────────────────────────────────────────────────────
async function loadPendingReviews() {
  const el = document.getElementById("reviews-area");
  const countEl = document.getElementById("pending-count");
  el.innerHTML = '<span class="loading">Loading pending reviews...</span>';
  try {
    const data = await api.getPendingReviews();
    const pending = data.pending || [];
    if (countEl) countEl.textContent = pending.length || "";

    if (!pending.length) {
      el.innerHTML = '<p style="color:#718096">No pending medication reviews.</p>';
      return;
    }

    el.innerHTML = pending.map(item => `
      <div class="review-card" id="card-${item.video_id}">
        <h3>Patient: ${item.patient_id || "Unknown"}</h3>
        <p class="meta">Appointment: ${item.appointment_id || "—"} · Video: ${item.video_id}</p>
        <div>
          ${(item.ai_medications || []).map(m => `
            <div class="med-item">
              <strong>${m.name}</strong> — ${[m.dosage, m.frequency].filter(Boolean).join(", ")}
              ${m.purpose ? `<br><span style="color:#4a5568;font-size:0.85rem">For: ${m.purpose}</span>` : ""}
              ${m.video_start_seconds != null
                ? `<br><button class="play-clip-btn" onclick="playMedClip('${item.video_id}', ${m.video_start_seconds})">
                     ▶ Watch at ${formatSeconds(m.video_start_seconds)}
                   </button>` : ""}
            </div>`).join("") || "<p style='color:#718096;font-size:0.9rem'>No medications detected.</p>"}
        </div>
        <div class="review-actions">
          <button class="btn-approve" onclick="approve('${item.video_id}')">Approve</button>
          <button class="btn-override" onclick="showOverride('${item.video_id}')">Override</button>
        </div>
        <div class="override-area" id="override-${item.video_id}">
          <textarea placeholder="Write your medication instructions for the patient..."></textarea>
          <button class="btn-save-override" onclick="saveOverride('${item.video_id}')">Save Override</button>
        </div>
      </div>`).join("");
  } catch (e) {
    el.innerHTML = `<span class="error">${e.message}</span>`;
  }
}

window.approve = async function (videoId) {
  try {
    await api.approveMedications(videoId);
    document.getElementById(`card-${videoId}`)?.remove();
    updateCount();
  } catch (e) {
    alert(`Error approving: ${e.message}`);
  }
};

window.showOverride = function (videoId) {
  const area = document.getElementById(`override-${videoId}`);
  if (area) area.style.display = area.style.display === "flex" ? "none" : "flex";
};

window.saveOverride = async function (videoId) {
  const area = document.getElementById(`override-${videoId}`);
  const text = area?.querySelector("textarea")?.value?.trim();
  if (!text) return alert("Please enter override text.");
  try {
    await api.overrideMedications(videoId, text);
    document.getElementById(`card-${videoId}`)?.remove();
    updateCount();
  } catch (e) {
    alert(`Error saving override: ${e.message}`);
  }
};

window.playMedClip = function (videoId, startSeconds) {
  playClip(startSeconds, startSeconds + 30, null);
};

function updateCount() {
  const countEl = document.getElementById("pending-count");
  const remaining = document.querySelectorAll(".review-card").length;
  if (countEl) countEl.textContent = remaining || "";
}

loadPendingReviews();
