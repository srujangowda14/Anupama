import React, { useEffect, useState } from "react";
import "./styles/globals.css";
import WelcomeScreen from "./components/WelcomeScreen";
import AuthScreen from "./components/AuthScreen";
import WorkspaceShell from "./components/WorkspaceShell";
import { api } from "./utils/api";
import { supabase } from "./utils/supabase";

export default function App() {
  const [profile, setProfile] = useState(null);
  const [session, setSession] = useState(null);
  const [loadingProfile, setLoadingProfile] = useState(true);

  useEffect(() => {
    let active = true;

    const loadForSession = async (nextSession) => {
      if (!active) return;
      setLoadingProfile(true);
      setSession(nextSession);

      if (nextSession?.user?.id) {
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

    const { data: listener } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      loadForSession(nextSession);
    });

    return () => {
      active = false;
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
    return <AuthScreen />;
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
