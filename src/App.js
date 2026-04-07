import React, { useState } from "react";
import "./styles/globals.css";
import WelcomeScreen from "./components/WelcomeScreen";
import ChatScreen from "./components/ChatScreen";

export default function App() {
  const [screen, setScreen] = useState("welcome"); // "welcome" | "chat"
  const [mode, setMode] = useState("support");

  const handleStart = (selectedMode) => {
    setMode(selectedMode);
    setScreen("chat");
  };

  const handleNewSession = () => {
    setScreen("welcome");
  };

  return screen === "welcome" ? (
    <WelcomeScreen onStart={handleStart} />
  ) : (
    <ChatScreen mode={mode} onNewSession={handleNewSession} />
  );
}