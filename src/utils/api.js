const BASE = process.env.REACT_APP_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  chat: (sessionId, message, mode) =>
    request("/chat", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, user_id: localStorage.getItem("anupama_profile_id"), message, mode }),
    }),

  logMood: (sessionId, score, note = null) =>
    request(`/mood/${sessionId}`, {
      method: "POST",
      body: JSON.stringify({ user_id: localStorage.getItem("anupama_profile_id"), score, note }),
    }),

  getMood: (sessionId) => request(`/mood/${sessionId}`),

  getSummary: (sessionId) => request(`/summary/${sessionId}`),

  saveProfile: (profile) =>
    request("/profiles", {
      method: "POST",
      body: JSON.stringify(profile),
    }),

  getProfile: (profileId) => request(`/profiles/${profileId}`),

  getDashboard: (profileId) => request(`/profiles/${profileId}/dashboard`),

  scheduleSession: (profileId, payload) =>
    request(`/profiles/${profileId}/schedule`, {
      method: "POST",
      body: JSON.stringify({ ...payload, profile_id: profileId }),
    }),

  getSchedule: (profileId) => request(`/profiles/${profileId}/schedule`),

  updateHomework: (homeworkId, payload) =>
    request(`/homework/${homeworkId}`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  deleteSession: (sessionId) =>
    request(`/session/${sessionId}`, { method: "DELETE" }),

  health: () => request("/health"),
};
