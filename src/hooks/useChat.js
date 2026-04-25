import { useState, useCallback } from "react";
import { api } from "../utils/api";

export function useChat(mode) {
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [homework, setHomework] = useState(null);
  const [previousSummary, setPreviousSummary] = useState(null);
  const [sessionMeta, setSessionMeta] = useState({
    isFirstSession: false,
    sessionClosing: false,
    sessionPhase: "opening",
    treatmentPlan: null,
    pendingHomework: [],
  });
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
        if (data.homework) setHomework(data.homework);
        if (data.previous_session_summary) setPreviousSummary(data.previous_session_summary);
        setSessionMeta({
          isFirstSession: Boolean(data.is_first_session),
          sessionClosing: Boolean(data.session_closing),
          sessionPhase: data.session_phase || "working",
          treatmentPlan: data.treatment_plan || null,
          pendingHomework: data.pending_homework || [],
        });

        addMessage({
          role: "assistant",
          content: data.reply,
          timestamp: data.timestamp,
          is_crisis: data.is_crisis,
          mood_score: data.mood_score,
          distortion: data.distortion,
          session_id: data.session_id,
          homework: data.homework,
        });

        // Auto-log mood detected by classifier
        const sid = sessionId || data.session_id;
        if (data.mood_score && sid) {
          api.logMood(sid, data.mood_score).catch(() => {});
        }

        return data;
      } catch (e) {
        setError("I couldn't complete that session request right now.");
        addMessage({
          role: "assistant",
          content: "I'm having trouble completing that request right now. Please try again in a moment.",
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
    setMessages([]);
    setSessionId(null);
    setError(null);
    setHomework(null);
    setPreviousSummary(null);
    setSessionMeta({
      isFirstSession: false,
      sessionClosing: false,
      sessionPhase: "opening",
      treatmentPlan: null,
      pendingHomework: [],
    });
  }, []);

  return { messages, sessionId, loading, error, send, reset, homework, previousSummary, sessionMeta };
}
