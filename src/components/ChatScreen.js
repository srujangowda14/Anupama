import React, { useEffect, useRef } from "react";
import { useChat } from "../hooks/useChat";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";
import { useIsMobile } from "../hooks/useIsMobile";

const MODE_META = {
  support: { icon: "🌿", label: "Support Buddy", color: "#6B9E7A" },
  cbt: { icon: "🧠", label: "CBT Coach", color: "#7B7FD4" },
  intake: { icon: "📋", label: "Intake Assistant", color: "#C8944A" },
};

const OPENING_MESSAGES = {
  support: "Hi, I’m Anupama. We can start gently. What has this week felt like for you?",
  cbt: "Hi, I’m Anupama in CBT Coach mode. We’ll start by understanding what has been weighing on you, then work toward one helpful next step.",
  intake: "Hi, I’m Anupama in Intake Assistant mode. We can use this session to gather your story, what feels hardest lately, and what you want support with.",
};

export default function ChatScreen({ mode, profile, onSessionActivity, onOpenPage, onStartNextSession }) {
  const isMobile = useIsMobile();
  const { messages, loading, send, homework, previousSummary, sessionMeta } = useChat(mode);
  const bottomRef = useRef(null);
  const meta = MODE_META[mode];
  const sessionEnded = Boolean(sessionMeta.sessionClosing);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const allMessages = messages.length
    ? messages
    : [
        {
          id: "opening",
          role: "assistant",
          content: OPENING_MESSAGES[mode],
          timestamp: new Date().toISOString(),
        },
      ];

  const handleSend = async (text) => {
    const data = await send(text);
    if (data && onSessionActivity) {
      onSessionActivity(data);
    }
  };

  return (
    <div style={styles.root}>
      <header style={{ ...styles.header, flexDirection: isMobile ? "column" : "row", padding: isMobile ? "18px 16px 14px" : "24px 28px 18px" }}>
        <div>
          <div style={styles.eyebrow}>Session Workspace</div>
          <div style={{ ...styles.headerTitle, fontSize: isMobile ? 20 : 22 }}>
            <span style={{ fontSize: 20 }}>{meta.icon}</span>
            <span>{meta.label}</span>
          </div>
          <div style={styles.headerSub}>
            {profile?.name || "You"} · {sessionMeta.treatmentPlan?.phase_title || "Therapeutic support"}
          </div>
        </div>
        <div style={styles.headerActions}>
          <button style={styles.secondaryBtn} onClick={() => onOpenPage?.("sessions")}>
            Sessions
          </button>
          <button style={styles.secondaryBtn} onClick={() => onOpenPage?.("homework")}>
            Homework
          </button>
        </div>
      </header>

      <div style={{ ...styles.contextGrid, gridTemplateColumns: isMobile ? "1fr" : styles.contextGrid.gridTemplateColumns, padding: isMobile ? "14px 16px 0" : "18px 28px 0" }}>
        <div style={{ ...styles.contextCard, padding: isMobile ? 14 : 16 }}>
          <div style={styles.contextTitle}>Current phase</div>
          <div style={{ ...styles.phaseBadge, borderColor: `${meta.color}55`, color: meta.color }}>
            {sessionMeta.sessionPhase === "closing"
              ? "Closing"
              : sessionMeta.sessionPhase === "working"
                ? "Working"
                : "Opening"}
          </div>
          <p style={styles.contextText}>
            {sessionMeta.isFirstSession
              ? "This first session is being used to get to know the person, understand their history, and agree on what future work should focus on."
              : sessionMeta.sessionPhase === "opening"
                ? "This is a good time for mood check-ins, bridging from the last session, and choosing one focus for today."
                : sessionMeta.sessionPhase === "closing"
                  ? "The assistant is shifting toward summarizing the key takeaway and setting up the between-session practice."
                  : "The assistant should stay with one main concern and work it collaboratively rather than rushing through several topics."}
          </p>
        </div>

        {previousSummary && (
          <div style={{ ...styles.contextCard, padding: isMobile ? 14 : 16 }}>
            <div style={styles.contextTitle}>Prior context in memory</div>
            <p style={styles.contextText}>
              {previousSummary.length > 280 ? `${previousSummary.slice(0, 280)}…` : previousSummary}
            </p>
          </div>
        )}

        {homework && (
          <div style={{ ...styles.contextCard, padding: isMobile ? 14 : 16 }}>
            <div style={styles.contextTitle}>Assigned for next time</div>
            <div style={styles.homeworkTitle}>{homework.title}</div>
            <p style={styles.contextText}>{homework.instructions}</p>
          </div>
        )}
      </div>

      <div style={{ ...styles.messages, padding: isMobile ? "18px 16px 8px" : "24px 28px 8px" }}>
        {allMessages.map((msg) => (
          <ChatMessage key={msg.id} msg={msg} />
        ))}

        {loading && (
          <div style={styles.loadingRow}>
            <div style={styles.loadingAvatar}>🌿</div>
            <div style={styles.loadingBubble}>
              {[0, 0.2, 0.4].map((delay, index) => (
                <span
                  key={index}
                  style={{
                    ...styles.loadingDot,
                    animation: `pulse 1.2s ${delay}s ease-in-out infinite`,
                  }}
                />
              ))}
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {sessionEnded && (
        <div style={{ ...styles.endCap, margin: isMobile ? "0 16px 14px" : "0 28px 18px", padding: isMobile ? 16 : 18 }}>
          <div style={styles.endCapTitle}>This session has wrapped up.</div>
          <p style={styles.endCapText}>
            The current session is closed so the next one can begin with fresh context, homework review, and a new agenda.
          </p>
          <div style={styles.endCapActions}>
            <button style={styles.secondaryBtn} onClick={() => onOpenPage?.("homework")}>
              Review homework
            </button>
            <button style={styles.primaryBtn} onClick={() => onStartNextSession?.(mode)}>
              Start next session
            </button>
          </div>
        </div>
      )}

      <ChatInput onSend={handleSend} loading={loading} disabled={sessionEnded} compact={isMobile} />
    </div>
  );
}

const styles = {
  root: {
    display: "flex",
    flexDirection: "column",
    height: "100%",
    minHeight: 0,
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    gap: 16,
    alignItems: "flex-start",
    padding: "24px 28px 18px",
    borderBottom: "1px solid var(--border-subtle)",
    background: "rgba(255,255,255,0.02)",
  },
  eyebrow: {
    fontSize: 11,
    letterSpacing: "0.16em",
    textTransform: "uppercase",
    color: "var(--text-muted)",
    marginBottom: 8,
  },
  headerTitle: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    fontFamily: "var(--font-display)",
    fontSize: 22,
    color: "var(--text-primary)",
  },
  headerSub: {
    marginTop: 6,
    fontSize: 13,
    color: "var(--text-secondary)",
    lineHeight: 1.5,
  },
  headerActions: {
    display: "flex",
    gap: 10,
    flexWrap: "wrap",
  },
  secondaryBtn: {
    border: "1px solid var(--border-subtle)",
    background: "rgba(255,255,255,0.03)",
    color: "var(--text-primary)",
    borderRadius: 999,
    padding: "10px 14px",
    fontSize: 12,
    cursor: "pointer",
  },
  contextGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
    gap: 14,
    padding: "18px 28px 0",
    flexShrink: 0,
  },
  contextCard: {
    border: "1px solid var(--border-subtle)",
    background: "rgba(255,255,255,0.02)",
    borderRadius: 18,
    padding: 16,
  },
  contextTitle: {
    fontFamily: "var(--font-display)",
    fontSize: 15,
    color: "var(--text-primary)",
    marginBottom: 10,
  },
  phaseBadge: {
    display: "inline-flex",
    alignItems: "center",
    border: "1px solid",
    borderRadius: 999,
    padding: "4px 10px",
    fontSize: 11,
    marginBottom: 10,
  },
  contextText: {
    fontSize: 12,
    color: "var(--text-secondary)",
    lineHeight: 1.65,
    whiteSpace: "pre-wrap",
  },
  homeworkTitle: {
    fontSize: 13,
    color: "var(--text-primary)",
    marginBottom: 8,
    fontWeight: 600,
  },
  messages: {
    flex: 1,
    minHeight: 0,
    overflowY: "auto",
    padding: "24px 28px 8px",
  },
  loadingRow: {
    display: "flex",
    alignItems: "flex-end",
    gap: 10,
    marginBottom: 18,
  },
  loadingAvatar: {
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
  loadingBubble: {
    display: "flex",
    gap: 6,
    padding: "12px 14px",
    borderRadius: 16,
    background: "rgba(255,255,255,0.03)",
  },
  loadingDot: {
    width: 6,
    height: 6,
    borderRadius: "50%",
    background: "#6B9E7A",
    display: "inline-block",
  },
  endCap: {
    margin: "0 28px 18px",
    padding: 18,
    borderRadius: 18,
    border: "1px solid rgba(107,158,122,0.22)",
    background: "rgba(107,158,122,0.08)",
  },
  endCapTitle: {
    fontFamily: "var(--font-display)",
    fontSize: 18,
    color: "var(--text-primary)",
    marginBottom: 8,
  },
  endCapText: {
    fontSize: 13,
    color: "var(--text-secondary)",
    lineHeight: 1.65,
    marginBottom: 14,
  },
  endCapActions: {
    display: "flex",
    gap: 10,
    flexWrap: "wrap",
  },
  primaryBtn: {
    border: "none",
    borderRadius: 14,
    padding: "10px 16px",
    background: "linear-gradient(135deg, #4E8A5E, #3A7050)",
    color: "#fff",
    fontSize: 13,
    cursor: "pointer",
  },
};
