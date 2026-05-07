import React, { useEffect, useState } from "react";
import "./styles/globals.css";
import WelcomeScreen from "./components/WelcomeScreen";
import AuthScreen from "./components/AuthScreen";
import WorkspaceShell from "./components/WorkspaceShell";
import { api } from "./utils/api";
import {
  clearSessionStarted,
  ensureSessionStarted,
  getRemainingSessionMs,
  hasSessionExpired,
  markSessionStarted,
  supabase,
} from "./utils/supabase";

export default function App() {
  const [profile, setProfile] = useState(null);
  const [session, setSession] = useState(null);
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [authNotice, setAuthNotice] = useState(null);

  useEffect(() => {
    let active = true;
    let expiryTimer = null;

    const expireSession = async () => {
      clearSessionStarted();
      setAuthNotice("Your session expired after 2 hours. Please sign in again.");
      await supabase.auth.signOut();
    };

    const scheduleExpiry = () => {
      if (expiryTimer) {
        window.clearTimeout(expiryTimer);
      }
      const remaining = getRemainingSessionMs();
      expiryTimer = window.setTimeout(() => {
        expireSession();
      }, remaining);
    };

    const loadForSession = async (nextSession, authEvent = null) => {
      if (!active) return;
      setLoadingProfile(true);

      if (!nextSession) {
        clearSessionStarted();
      } else if (authEvent === "SIGNED_IN") {
        markSessionStarted();
        setAuthNotice(null);
      } else {
        ensureSessionStarted();
      }

      if (nextSession && hasSessionExpired()) {
        await expireSession();
        if (active) {
          setProfile(null);
          setSession(null);
          setLoadingProfile(false);
        }
        return;
      }

      setSession(nextSession);

      if (nextSession?.user?.id) {
        scheduleExpiry();
        try {
          const result = await api.getProfile(nextSession.user.id);
          if (active) {
            setProfile(result.profile);
          }
        } catch (_err) {
          if (active) {
            setProfile(null);
          }
        } finally {
          if (active) {
            setLoadingProfile(false);
          }
        }
        return;
      }

      setProfile(null);
      setLoadingProfile(false);
    };

    supabase.auth.getSession().then(({ data }) => {
      loadForSession(data.session);
    });

    const { data: listener } = supabase.auth.onAuthStateChange((event, nextSession) => {
      if (event === "SIGNED_OUT") {
        clearSessionStarted();
      }
      loadForSession(nextSession, event);
    });

    return () => {
      active = false;
      if (expiryTimer) {
        window.clearTimeout(expiryTimer);
      }
      listener.subscription.unsubscribe();
    };
  }, []);

  const handleStart = async (selectedMode, profileDraft) => {
    const data = await api.saveProfile({
      id: session?.user?.id,
      ...profileDraft,
      preferred_mode: selectedMode,
    });
    setProfile(data.profile);
    window.location.hash = "chat";
  };

  if (!session) {
    return <AuthScreen notice={authNotice} />;
  }

  if (loadingProfile) {
    return <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", color: "var(--text-muted)" }}>Loading your account…</div>;
  }

  if (!profile) {
    return <WelcomeScreen onStart={handleStart} profile={profile} accountEmail={session.user?.email || ""} />;
  }

  return (
    <WorkspaceShell
      profile={profile}
      session={session}
      onProfileUpdate={setProfile}
    />
  );
}
