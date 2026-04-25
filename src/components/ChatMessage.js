import React from "react";

const DISTORTION_COLORS = {
  catastrophizing:       "#C06A50",
  all_or_nothing:        "#7B7FD4",
  mind_reading:          "#C8944A",
  fortune_telling:       "#6B9E7A",
  emotional_reasoning:   "#A07BC8",
  should_statements:     "#C8944A",
  labeling:              "#C06A50",
  personalization:       "#7BAFC8",
  mental_filter:         "#8FB87A",
  discounting_positives: "#C87A7A",
};

const MOOD_EMOJIS = ["", "😔", "😕", "😐", "🙂", "😊"];

function MetaBadge({ label, value, color }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        fontSize: 11,
        color: color || "var(--text-muted)",
        background: color ? `${color}18` : "rgba(255,255,255,0.05)",
        border: `1px solid ${color ? `${color}30` : "rgba(255,255,255,0.08)"}`,
        borderRadius: 6,
        padding: "2px 7px",
      }}
    >
      {label && <span style={{ opacity: 0.6 }}>{label}</span>}
      <span>{value}</span>
    </span>
  );
}

export default function ChatMessage({ msg }) {
  const isUser = msg.role === "user";
  const isCrisis = msg.is_crisis;
  const isError = msg.is_error;

  const time = msg.timestamp
    ? new Date(msg.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : "";

  return (
    <div
      className="fade-up"
      style={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        marginBottom: 18,
        gap: 10,
        alignItems: "flex-end",
      }}
    >
      {/* Bot avatar */}
      {!isUser && (
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            background: isCrisis
              ? "linear-gradient(135deg, #6B2020, #4A1010)"
              : "linear-gradient(135deg, #2A3D2E, #1E3028)",
            border: `1.5px solid ${isCrisis ? "rgba(192,64,64,0.4)" : "rgba(107,158,122,0.25)"}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 14,
            flexShrink: 0,
            marginBottom: 20,
          }}
        >
          {isCrisis ? "🆘" : "🌿"}
        </div>
      )}

      <div style={{ maxWidth: "70%", minWidth: 60 }}>
        {/* Bubble */}
        <div
          style={{
            background: isCrisis
              ? "linear-gradient(135deg, rgba(192,64,64,0.18), rgba(140,30,30,0.12))"
              : isUser
              ? "linear-gradient(135deg, rgba(78,138,94,0.2), rgba(58,112,80,0.15))"
              : isError
              ? "rgba(192,64,64,0.08)"
              : "var(--bg-raised)",
            border: isCrisis
              ? "1.5px solid rgba(192,64,64,0.4)"
              : isUser
              ? "1.5px solid rgba(107,158,122,0.25)"
              : isError
              ? "1.5px solid rgba(192,64,64,0.2)"
              : "1.5px solid var(--border-subtle)",
            borderRadius: isUser
              ? "18px 18px 4px 18px"
              : "18px 18px 18px 4px",
            padding: "12px 16px",
            fontSize: 14,
            color: "var(--text-primary)",
            lineHeight: 1.7,
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
          }}
        >
          {msg.content}
        </div>

        {/* Metadata row — only for bot messages */}
        {!isUser && !isCrisis && !isError && (msg.mood_score || msg.distortion) && (
          <div
            style={{
              display: "flex",
              gap: 5,
              marginTop: 6,
              flexWrap: "wrap",
            }}
          >
            {msg.mood_score && (
              <MetaBadge
                value={`${MOOD_EMOJIS[msg.mood_score]} mood ${msg.mood_score}/5`}
                color="#6B9E7A"
              />
            )}
            {msg.distortion && msg.distortion !== "none" && (
              <MetaBadge
                label="distortion:"
                value={msg.distortion.replace(/_/g, " ")}
                color={DISTORTION_COLORS[msg.distortion] || "#A09890"}
              />
            )}
          </div>
        )}

        {!isUser && msg.homework && (
          <div style={{ marginTop: 8, padding: "8px 10px", borderRadius: 8, background: "rgba(123,127,212,0.12)", border: "1px solid rgba(123,127,212,0.2)", fontSize: 12, color: "var(--text-secondary)" }}>
            <strong style={{ color: "#B8BBF0" }}>Homework:</strong> {msg.homework.title}
          </div>
        )}

        {/* Timestamp */}
        <div
          style={{
            fontSize: 11,
            color: "var(--text-muted)",
            marginTop: 4,
            textAlign: isUser ? "right" : "left",
            paddingLeft: isUser ? 0 : 4,
            paddingRight: isUser ? 4 : 0,
          }}
        >
          {time}
        </div>
      </div>
    </div>
  );
}
