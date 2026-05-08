import { useState, useCallback, useEffect, useRef } from "react";
import { api } from "../utils/api";

const SESSION_DURATION_SECONDS = 20 * 60;
const SESSION_AUTO_CLOSE_SECONDS = 19 * 60;

export function useChat(mode) {
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [homework, setHomework] = useState(null);
  const [previousSummary, setPreviousSummary] = useState(null);
  const [sessionStartedAt, setSessionStartedAt] = useState(null);
  const [remainingSeconds, setRemainingSeconds] = useState(SESSION_DURATION_SECONDS);
  const [sessionMeta, setSessionMeta] = useState({
    isFirstSession: false,
    sessionClosing: false,
    sessionPhase: "opening",
    treatmentPlan: null,
    pendingHomework: [],
    openingMessage: null,
  });
  const closeTriggeredRef = useRef(false);
  const addMessage = useCallback((msg) => {
    setMessages((prev) => [...prev, { id: Date.now() + Math.random(), ...msg }]);
  }, []);

  const syncSessionMeta = useCallback((data) => {
    if (data.session_started_at) {
      setSessionStartedAt(data.session_started_at);
    }
    if (typeof data.session_time_remaining_seconds === "number") {
      setRemainingSeconds(data.session_time_remaining_seconds);
    }
    setSessionMeta({
      isFirstSession: Boolean(data.is_first_session),
      sessionClosing: Boolean(data.session_closing),
      sessionPhase: data.session_phase || "working",
      treatmentPlan: data.treatment_plan || null,
      pendingHomework: data.pending_homework || [],
      openingMessage: data.opening_message || null,
    });
  }, []);

  const closeSession = useCallback(async () => {
    if (!sessionId || closeTriggeredRef.current) return null;
    closeTriggeredRef.current = true;
    setLoading(true);
    try {
      const data = await api.closeSession(sessionId, mode);
      if (data.homework) setHomework(data.homework);
      if (data.previous_session_summary) setPreviousSummary(data.previous_session_summary);
      syncSessionMeta(data);
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
      return data;
    } catch (_err) {
      setSessionMeta((prev) => ({
        ...prev,
        sessionClosing: true,
        sessionPhase: "closing",
      }));
      setError("The session time limit was reached.");
      addMessage({
        role: "assistant",
        content: "This session has reached its time limit. Please start a new session to continue.",
        timestamp: new Date().toISOString(),
        is_error: true,
      });
      return null;
    } finally {
      setLoading(false);
    }
  }, [sessionId, mode, syncSessionMeta, addMessage]);

  const send = useCallback(
    async (text) => {
      if (!text.trim() || loading || sessionMeta.sessionClosing) return;

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
        syncSessionMeta(data);
        if (data.session_closing) {
          closeTriggeredRef.current = true;
        }

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
    [sessionId, mode, loading, addMessage, syncSessionMeta, sessionMeta.sessionClosing]
  );

  useEffect(() => {
    if (!sessionStartedAt || !sessionId || sessionMeta.sessionClosing) return undefined;

    const updateRemaining = () => {
      const started = new Date(sessionStartedAt).getTime();
      const nextRemaining = Math.max(0, SESSION_DURATION_SECONDS - Math.floor((Date.now() - started) / 1000));
      setRemainingSeconds(nextRemaining);
      return nextRemaining;
    };

    updateRemaining();
    const interval = window.setInterval(() => {
      const nextRemaining = updateRemaining();
      if (nextRemaining <= SESSION_DURATION_SECONDS - SESSION_AUTO_CLOSE_SECONDS && !closeTriggeredRef.current) {
        closeSession();
      }
    }, 1000);

    return () => window.clearInterval(interval);
  }, [sessionStartedAt, sessionId, sessionMeta.sessionClosing, closeSession]);

  const reset = useCallback(() => {
    closeTriggeredRef.current = false;
    setMessages([]);
    setSessionId(null);
    setError(null);
    setHomework(null);
    setPreviousSummary(null);
    setSessionStartedAt(null);
    setRemainingSeconds(SESSION_DURATION_SECONDS);
    setSessionMeta({
      isFirstSession: false,
      sessionClosing: false,
      sessionPhase: "opening",
      treatmentPlan: null,
      pendingHomework: [],
      openingMessage: null,
    });
  }, []);

  return { messages, sessionId, loading, error, send, reset, homework, previousSummary, sessionMeta, remainingSeconds };
}
