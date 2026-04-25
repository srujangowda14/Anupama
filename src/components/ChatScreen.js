import React, { useEffect, useRef, useState } from "react";
import { useChat } from "../hooks/useChat";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";
import MoodPanel from "./MoodPanel";
import { CarePlanPanel, ProfilePanel, SummaryPanel } from "./SidebarPanels";

const MODE_META = {
  support: { icon: "🌿", label: "Support Buddy",     color: "#6B9E7A" },
  cbt:     { icon: "🧠", label: "CBT Coach",         color: "#7B7FD4" },
  intake:  { icon: "📋", label: "Intake Assistant",  color: "#C8944A" },
};

const TABS = ["profile", "mood", "plan", "summary"];

const OPENING_MESSAGES = {
  support: "Hello, I'm Anupama. This is a safe space — no judgment here.\n\nHow are you feeling today?",
  cbt:     "Hi, I'm Anupama in CBT Coach mode. We'll work through your thoughts together, step by step.\n\nWhat's been on your mind lately?",
  intake:  "Hello. I'm here to help you organize your thoughts before speaking with a therapist.\n\nTake your time — what's the main thing you'd like to talk about?",
};

export default function ChatScreen({ mode, onNewSession, profile, onProfileUpdate }) {
  const { messages, sessionId, loading, send, homework, previousSummary } = useChat(mode);
  const [tab, setTab] = useState("profile");
  const [hasOpened, setHasOpened] = useState(false);
  const bottomRef = useRef(null);
  const meta = MODE_META[mode];

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Show opening message once
  const allMessages = hasOpened
    ? messages
    : [
        {
          id: "opening",
          role: "assistant",
          content: OPENING_MESSAGES[mode],
          timestamp: new Date().toISOString(),
        },
        ...messages,
      ];

  const handleSend = (text) => {
    setHasOpened(true);
    send(text);
  };

  return (
    <div style={styles.root}>
      {/* ── Sidebar ─────────────────────────────────────── */}
      <aside style={styles.sidebar}>
        {/* Brand */}
        <div style={styles.brand}>
          <div style={styles.brandAvatar}>
            <span style={{ animation: "breathe 4s ease-in-out infinite", display: "inline-block" }}>
              🌿
            </span>
          </div>
          <div>
            <div style={styles.brandName}>Anupama</div>
            <div style={{ fontSize: 11, color: meta.color, fontWeight: 500 }}>
              {profile?.name || "Your profile"} · {meta.icon} {meta.label}
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div style={styles.tabs}>
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                ...styles.tab,
                background: tab === t ? "rgba(107,158,122,0.15)" : "none",
                color: tab === t ? "#6B9E7A" : "var(--text-muted)",
                fontWeight: tab === t ? 500 : 400,
              }}
            >
              {t}
            </button>
          ))}
        </div>

        {/* Panel content */}
        <div style={styles.panelContent}>
          {tab === "profile" && <ProfilePanel profile={profile} onProfileUpdate={onProfileUpdate} />}
          {tab === "mood"    && <MoodPanel sessionId={sessionId} />}
          {tab === "plan"    && <CarePlanPanel profileId={profile?.id} latestHomework={homework} previousSummary={previousSummary} />}
          {tab === "summary" && <SummaryPanel sessionId={sessionId} />}
        </div>

        {/* Footer */}
        <div style={styles.sidebarFooter}>
          <button onClick={onNewSession} style={styles.newSessionBtn}>
            ← New Session
          </button>
          <a
            href="tel:988"
            style={styles.crisisBtn}
          >
            🆘 988 Crisis Line
          </a>
        </div>
      </aside>

      {/* ── Chat area ───────────────────────────────────── */}
      <main style={styles.main}>
        {/* Header */}
        <header style={styles.header}>
          <span style={{ fontSize: 20 }}>{meta.icon}</span>
          <div>
            <div style={styles.headerTitle}>{meta.label}</div>
            <div style={styles.headerSub}>
              Custom BiLSTM model · Not a substitute for professional care
            </div>
          </div>
          <div style={styles.statusDot}>
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: "#6B9E7A",
                display: "inline-block",
                animation: "pulse 2s ease-in-out infinite",
                marginRight: 5,
              }}
            />
            <span style={{ fontSize: 11, color: "#6B9E7A" }}>Active</span>
          </div>
        </header>

        {/* Messages */}
        <div style={styles.messages}>
          {allMessages.map((msg) => (
            <ChatMessage key={msg.id} msg={msg} />
          ))}

          {/* Typing indicator */}
          {loading && (
            <div style={{ display: "flex", alignItems: "flex-end", gap: 10, marginBottom: 18 }}>
              <div style={styles.typingAvatar}>🌿</div>
              <div style={styles.typingBubble}>
                {[0, 0.2, 0.4].map((d, i) => (
                  <span
                    key={i}
                    style={{
                      width: 6,
                      height: 6,
                      borderRadius: "50%",
                      background: "#6B9E7A",
                      display: "inline-block",
                      animation: `pulse 1.2s ${d}s ease-in-out infinite`,
                    }}
                  />
                ))}
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <ChatInput onSend={handleSend} loading={loading} />
      </main>
    </div>
  );
}

const styles = {
  root: {
    display: "flex",
    height: "100vh",
    overflow: "hidden",
    background: "var(--bg-deep)",
  },

  // Sidebar
  sidebar: {
    width: 260,
    flexShrink: 0,
    borderRight: "1px solid var(--border-subtle)",
    display: "flex",
    flexDirection: "column",
    padding: "20px 16px",
    background: "var(--bg-surface)",
    overflowY: "auto",
  },
  brand: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    marginBottom: 22,
  },
  brandAvatar: {
    width: 38,
    height: 38,
    borderRadius: "50%",
    background: "linear-gradient(135deg, #2A3D2E, #1E3028)",
    border: "1.5px solid rgba(107,158,122,0.25)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 16,
    flexShrink: 0,
  },
  brandName: {
    fontFamily: "var(--font-display)",
    fontSize: 17,
    color: "var(--text-primary)",
  },
  tabs: {
    display: "flex",
    background: "rgba(255,255,255,0.03)",
    borderRadius: "var(--radius-sm)",
    padding: 3,
    marginBottom: 18,
    gap: 2,
  },
  tab: {
    flex: 1,
    padding: "6px 0",
    borderRadius: 6,
    border: "none",
    fontSize: 11,
    cursor: "pointer",
    textTransform: "capitalize",
    transition: "all 0.15s ease",
    letterSpacing: "0.02em",
  },
  panelContent: {
    flex: 1,
    overflowY: "auto",
  },
  sidebarFooter: {
    marginTop: 20,
    paddingTop: 16,
    borderTop: "1px solid var(--border-subtle)",
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  newSessionBtn: {
    width: "100%",
    padding: "8px",
    borderRadius: "var(--radius-sm)",
    border: "1px solid var(--border-subtle)",
    background: "none",
    color: "var(--text-muted)",
    fontSize: 12,
    cursor: "pointer",
    transition: "color 0.15s ease",
  },
  crisisBtn: {
    display: "block",
    width: "100%",
    padding: "8px",
    borderRadius: "var(--radius-sm)",
    border: "1px solid rgba(192,64,64,0.25)",
    background: "rgba(192,64,64,0.05)",
    color: "#C87A7A",
    fontSize: 12,
    textAlign: "center",
    textDecoration: "none",
    cursor: "pointer",
  },

  // Chat
  main: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
  header: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "14px 22px",
    borderBottom: "1px solid var(--border-subtle)",
    background: "var(--bg-surface)",
    flexShrink: 0,
  },
  headerTitle: {
    fontFamily: "var(--font-display)",
    fontSize: 16,
    color: "var(--text-primary)",
  },
  headerSub: {
    fontSize: 11,
    color: "var(--text-muted)",
  },
  statusDot: {
    marginLeft: "auto",
    display: "flex",
    alignItems: "center",
  },
  messages: {
    flex: 1,
    overflowY: "auto",
    padding: "24px 22px 8px",
  },
  typingAvatar: {
    width: 32,
    height: 32,
    borderRadius: "50%",
    background: "linear-gradient(135deg, #2A3D2E, #1E3028)",
    border: "1.5px solid rgba(107,158,122,0.25)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 14,
    flexShrink: 0,
    marginBottom: 20,
  },
  typingBubble: {
    background: "var(--bg-raised)",
    border: "1.5px solid var(--border-subtle)",
    borderRadius: "18px 18px 18px 4px",
    padding: "12px 16px",
    display: "flex",
    gap: 5,
    alignItems: "center",
  },
};
