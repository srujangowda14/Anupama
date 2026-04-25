import React, { useState } from "react";
import "./styles/globals.css";
import WelcomeScreen from "./components/WelcomeScreen";
import ChatScreen from "./components/ChatScreen";
import { api } from "./utils/api";

export default function App() {
  const [screen, setScreen] = useState("welcome"); // "welcome" | "chat"
  const [mode, setMode] = useState("support");
  const [profile, setProfile] = useState(null);

  const handleStart = async (selectedMode, profileDraft) => {
    const existingId = localStorage.getItem("anupama_profile_id");
    const data = await api.saveProfile({
      id: existingId || undefined,
      ...profileDraft,
      preferred_mode: selectedMode,
    });
    localStorage.setItem("anupama_profile_id", data.profile.id);
    setProfile(data.profile);
    setMode(selectedMode);
    setScreen("chat");
  };

  const handleNewSession = () => {
    setScreen("welcome");
  };

  return screen === "welcome" ? (
    <WelcomeScreen onStart={handleStart} profile={profile} />
  ) : (
    <ChatScreen mode={mode} onNewSession={handleNewSession} profile={profile} onProfileUpdate={setProfile} />
  );
}
