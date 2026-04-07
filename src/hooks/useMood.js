import React, { useState } from "react";
import { useMood } from "./useMood";

const MOODS = [
  { score: 1, emoji: "😔", label: "Very low" },
  { score: 2, emoji: "😕", label: "Low" },
  { score: 3, emoji: "😐", label: "Neutral" },
  { score: 4, emoji: "🙂", label: "Good" },
  { score: 5, emoji: "😊", label: "Great" },
];

function MoodDot({ score }) {
  const colors = ["", "#C04040", "#C87A50", "#C8944A", "#8FB87A", "#6B9E7A"];
  return (
    <div
      style={{
        width: 8,
        height: 8,
        borderRadius: "50%",
        background: colors[score] || "var(--text-muted)",
        flexShrink: 0,
      }}
    />
  );
}

export default function MoodPanel({ sessionId }) {
  const { moodLog, logMood } = useMood(sessionId);
  const [selected, setSelected] = useState(null);
  const [saved, setSaved] = useState(false);

  const handleLog = async (score) => {
    setSelected(score);
    await logMood(score);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div style={styles.root}>
      <p style={styles.sectionLabel}>How are you feeling?</p>

      {/* Mood buttons */}
      <div style={styles.moodRow}>
        {MOODS.map((m) => (
          <button
            key={m.score}
            title={m.label}
            onClick={() => handleLog(m.score)}
            style={{
              ...styles.moodBtn,
              background:
                selected === m.score
                  ? "rgba(107,158,122,0.2)"
                  : "rgba(255,255,255,0.03)",
              border: `1.5px solid ${selected === m.score ? "#6B9E7A" : "var(--border-subtle)"}`,
              transform: selected === m.score ? "scale(1.18)" : "scale(1)",
            }}
          >
            {m.emoji}
          </button>
        ))}
      </div>

      {saved && (
        <p style={{ fontSize: 12, color: "#6B9E7A", marginTop: 6 }}>✓ Logged</p>
      )}

      {/* Mood history */}
      {moodLog.length > 0 && (
        <>
          <p style={{ ...styles.sectionLabel, marginTop: 18 }}>Session history</p>
          <div style={styles.logList}>
            {moodLog.slice(-8).reverse().map((entry, i) => (
              <div key={i} style={styles.logRow}>
                <MoodDot score={entry.score} />
                <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                  Mood {entry.score}/5
                </span>
                <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: "auto" }}>
                  {new Date(entry.timestamp).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </div>
            ))}
          </div>

          {/* Mini sparkline */}
          {moodLog.length >= 2 && (
            <MoodSparkline log={moodLog.slice(-10)} />
          )}
        </>
      )}

      {!sessionId && (
        <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 8 }}>
          Start a conversation to track mood.
        </p>
      )}
    </div>
  );
}

function MoodSparkline({ log }) {
  const W = 220, H = 40, PAD = 6;
  const scores = log.map((e) => e.score);
  const n = scores.length;
  const xStep = (W - PAD * 2) / Math.max(n - 1, 1);

  const points = scores.map((s, i) => {
    const x = PAD + i * xStep;
    const y = H - PAD - ((s - 1) / 4) * (H - PAD * 2);
    return `${x},${y}`;
  });

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      width="100%"
      style={{ marginTop: 12, display: "block" }}
    >
      <polyline
        points={points.join(" ")}
        fill="none"
        stroke="#6B9E7A"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.7"
      />
      {scores.map((s, i) => {
        const [x, y] = points[i].split(",");
        return (
          <circle
            key={i}
            cx={x}
            cy={y}
            r="2.5"
            fill="#6B9E7A"
            opacity="0.9"
          />
        );
      })}
    </svg>
  );
}

const styles = {
  root: { width: "100%" },
  sectionLabel: {
    fontFamily: "var(--font-display)",
    fontStyle: "italic",
    fontSize: 13,
    color: "var(--text-muted)",
    marginBottom: 10,
  },
  moodRow: {
    display: "flex",
    gap: 6,
  },
  moodBtn: {
    flex: 1,
    fontSize: 20,
    padding: "8px 0",
    borderRadius: "var(--radius-sm)",
    border: "1.5px solid",
    background: "none",
    cursor: "pointer",
    transition: "all 0.18s ease",
  },
  logList: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  logRow: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "5px 8px",
    background: "rgba(255,255,255,0.02)",
    borderRadius: "var(--radius-sm)",
    border: "1px solid var(--border-subtle)",
  },
};