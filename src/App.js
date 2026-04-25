import React, { useState } from "react";
import "./styles/globals.css";
import WelcomeScreen from "./components/WelcomeScreen";
import ChatScreen from "./components/ChatScreen";
import { api } from "./utils/api";
import AuthScreen from "./components/AuthScreen";
import { supabase } from "./utils/supabase";

export default function App() {
  const [screen, setScreen] = useState("welcome"); // "welcome" | "chat"
  const [mode, setMode] = useState("support");
  const [profile, setProfile] = useState(null);
  const [session, setSession] = useState(null);
  const [loadingProfile, setLoadingProfile] = useState(true);

  React.useEffect(() => {
    supabase.auth.getSession().then(async ({ data }) => {
      setSession(data.session);
      if (data.session?.user?.id) {
        try {
          const result = await api.getProfile(data.session.user.id);
          setProfile(result.profile);
          setMode(result.profile.preferred_mode || "support");
        } catch (_err) {
          setProfile(null);
        }
      } else {
        setProfile(null);
      }
      setLoadingProfile(false);
    });
    const { data: listener } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      setLoadingProfile(false);
    });
    return () => listener.subscription.unsubscribe();
  }, []);

  const handleStart = async (selectedMode, profileDraft) => {
    const userId = session?.user?.id;
    const data = await api.saveProfile({
      id: userId,
      ...profileDraft,
      preferred_mode: selectedMode,
    });
    setProfile(data.profile);
    setMode(selectedMode);
    setScreen("chat");
  };

  const handleNewSession = () => {
    setScreen("welcome");
  };

  if (!session) {
    return <AuthScreen />;
  }

  if (loadingProfile) {
    return null;
  }

  return (!profile || screen === "welcome") ? (
    <WelcomeScreen onStart={handleStart} profile={profile} />
  ) : (
    <ChatScreen mode={mode} onNewSession={handleNewSession} profile={profile} onProfileUpdate={setProfile} session={session} />
  );
}
