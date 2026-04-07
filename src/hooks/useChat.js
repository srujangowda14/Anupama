import { useState, useCallback, useRef } from "react";
import { api } from "../utils/api";

export function useChat(mode) {
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const abortRef = useRef(null);

  const addMessage = useCallback((msg) => {
    setMessages((prev) => [...prev, { id: Date.now() + Math.random(), ...msg }]);
  }, []);

  const send = useCallback(
    async (text) => {
      if (!text.trim() || loading) return;

      const userMsg = {
        role: "user",
        content: text,
        timestamp: new Date().toISOString(),
      };
      addMessage(userMsg);
      setLoading(true);
      setError(null);

      try {
        const data = await api.chat(sessionId, text, mode);

        if (!sessionId) setSessionId(data.session_id);

        addMessage({
          role: "assistant",
          content: data.reply,
          timestamp: data.timestamp,
          is_crisis: data.is_crisis,
          mood_score: data.mood_score,
          distortion: data.distortion,
          session_id: data.session_id,
        });

        // Auto-log mood detected by classifier
        const sid = sessionId || data.session_id;
        if (data.mood_score && sid) {
          api.logMood(sid, data.mood_score).catch(() => {});
        }

        return data;
      } catch (e) {
        setError("Could not reach the server. Is the backend running?");
        addMessage({
          role: "assistant",
          content: "I'm having trouble connecting right now. Please check that the backend is running on port 8000.",
          timestamp: new Date().toISOString(),
          is_error: true,
        });
      } finally {
        setLoading(false);
      }
    },
    [sessionId, mode, loading, addMessage]
  );

  const reset = useCallback(() => {
    if (sessionId) api.deleteSession(sessionId).catch(() => {});
    setMessages([]);
    setSessionId(null);
    setError(null);
  }, [sessionId]);

  return { messages, sessionId, loading, error, send, reset };
}