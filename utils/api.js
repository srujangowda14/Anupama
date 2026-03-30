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
      body: JSON.stringify({ session_id: sessionId, message, mode }),
    }),

  logMood: (sessionId, score, note = null) =>
    request(`/mood/${sessionId}`, {
      method: "POST",
      body: JSON.stringify({ score, note }),
    }),

  getMood: (sessionId) => request(`/mood/${sessionId}`),

  getSummary: (sessionId) => request(`/summary/${sessionId}`),

  deleteSession: (sessionId) =>
    request(`/session/${sessionId}`, { method: "DELETE" }),

  health: () => request("/health"),
};