import { createClient } from "@supabase/supabase-js";

const url = process.env.REACT_APP_SUPABASE_URL;
const anonKey = process.env.REACT_APP_SUPABASE_ANON_KEY;
const SESSION_STARTED_AT_KEY = "anupama_session_started_at";
const SESSION_MAX_AGE_MS = 2 * 60 * 60 * 1000;

export const supabase = createClient(url, anonKey);

export function markSessionStarted() {
  window.localStorage.setItem(SESSION_STARTED_AT_KEY, String(Date.now()));
}

export function ensureSessionStarted() {
  if (!window.localStorage.getItem(SESSION_STARTED_AT_KEY)) {
    markSessionStarted();
  }
}

export function clearSessionStarted() {
  window.localStorage.removeItem(SESSION_STARTED_AT_KEY);
}

export function getRemainingSessionMs() {
  const raw = window.localStorage.getItem(SESSION_STARTED_AT_KEY);
  if (!raw) return SESSION_MAX_AGE_MS;
  const startedAt = Number(raw);
  if (!Number.isFinite(startedAt)) return SESSION_MAX_AGE_MS;
  return Math.max(0, SESSION_MAX_AGE_MS - (Date.now() - startedAt));
}

export function hasSessionExpired() {
  return getRemainingSessionMs() <= 0;
}
