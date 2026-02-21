const BASE = "";  // Same origin

async function apiFetch(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export const api = {
  upload(formData) {
    return fetch("/api/upload", { method: "POST", body: formData }).then(r => {
      if (!r.ok) return r.json().then(e => Promise.reject(new Error(e.detail)));
      return r.json();
    });
  },
  uploadStatus(taskId) { return apiFetch(`/api/upload/status/${taskId}`); },
  getSummary(videoId) { return apiFetch(`/api/summary/${videoId}`); },
  getChapters(videoId) { return apiFetch(`/api/chapters/${videoId}`); },
  getGist(videoId) { return apiFetch(`/api/gist/${videoId}`); },
  search(query, appointmentId, patientId) {
    return apiFetch("/api/search", {
      method: "POST",
      body: JSON.stringify({ query, appointment_id: appointmentId, patient_id: patientId }),
    });
  },
  getPendingReviews() { return apiFetch("/api/review/pending"); },
  approveMedications(videoId) {
    return apiFetch(`/api/review/${videoId}/approve`, { method: "POST", body: "{}" });
  },
  overrideMedications(videoId, manualText) {
    return apiFetch(`/api/review/${videoId}/override`, {
      method: "POST",
      body: JSON.stringify({ manual_text: manualText }),
    });
  },
};
