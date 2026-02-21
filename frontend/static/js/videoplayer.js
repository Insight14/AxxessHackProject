let videoEl = null;
let clipEndTime = null;
let endTimer = null;

export function initPlayer(videoElement) {
  videoEl = videoElement;
  videoEl.addEventListener("timeupdate", () => {
    if (clipEndTime !== null && videoEl.currentTime >= clipEndTime) {
      videoEl.pause();
      clipEndTime = null;
    }
  });
}

export function playClip(start, end, src) {
  if (!videoEl) return;
  const container = document.getElementById("video-container");
  if (container) container.style.display = "block";

  if (src && videoEl.src !== src) {
    videoEl.src = src;
    videoEl.load();
    videoEl.addEventListener("loadedmetadata", () => seekAndPlay(start, end), { once: true });
  } else {
    seekAndPlay(start, end);
  }
}

function seekAndPlay(start, end) {
  if (!videoEl) return;
  clipEndTime = end || null;
  videoEl.currentTime = start || 0;
  videoEl.play();
}

export function formatSeconds(secs) {
  if (secs == null) return "--:--";
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}
