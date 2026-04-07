import { useState, useEffect, useCallback } from "react";
import { api } from "../utils/api";

export function useMood(sessionId) {
  const [moodLog, setMoodLog] = useState([]);

  const refresh = useCallback(async () => {
    if (!sessionId) return;
    try {
      const data = await api.getMood(sessionId);
      setMoodLog(data.mood_log || []);
    } catch (e) {}
  }, [sessionId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const logMood = useCallback(
    async (score, note) => {
      if (!sessionId) return;
      await api.logMood(sessionId, score, note);
      refresh();
    },
    [sessionId, refresh]
  );

  return { moodLog, logMood, refresh };
}