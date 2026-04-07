import React, { useState, useRef, useEffect } from "react";

export default function ChatInput({ onSend, loading, disabled }) {
  const [value, setValue] = useState("");
  const ref = useRef(null);

  useEffect(() => {
    if (!loading) ref.current?.focus();
  }, [loading]);

  const handleSend = () => {
    const text = value.trim();
    if (!text || loading || disabled) return;
    onSend(text);
    setValue("");
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const canSend = value.trim().length > 0 && !loading && !disabled;

  return (
    <div style={styles.root}>
      <div
        style={{
          ...styles.inputWrap,
          borderColor: value ? "rgba(107,158,122,0.35)" : "var(--border-subtle)",
        }}
      >
        <textarea
          ref={ref}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Share what's on your mind… (Enter to send)"
          rows={1}
          style={styles.textarea}
          disabled={disabled}
        />
        <button
          onClick={handleSend}
          disabled={!canSend}
          style={{
            ...styles.sendBtn,
            background: canSend
              ? "linear-gradient(135deg, #4E8A5E, #3A7050)"
              : "rgba(255,255,255,0.06)",
            color: canSend ? "#fff" : "var(--text-muted)",
          }}
        >
          {loading ? (
            <span style={styles.loadingDots}>
              {[0, 0.15, 0.3].map((d, i) => (
                <span
                  key={i}
                  style={{
                    width: 4,
                    height: 4,
                    borderRadius: "50%",
                    background: "currentColor",
                    display: "inline-block",
                    animation: `pulse 1.2s ${d}s ease-in-out infinite`,
                  }}
                />
              ))}
            </span>
          ) : (
            "↑"
          )}
        </button>
      </div>
      <p style={styles.hint}>Shift + Enter for a new line</p>
    </div>
  );
}

const styles = {
  root: { padding: "0 20px 20px" },
  inputWrap: {
    display: "flex",
    gap: 8,
    alignItems: "flex-end",
    background: "var(--bg-raised)",
    border: "1.5px solid",
    borderRadius: "var(--radius-md)",
    padding: "8px 8px 8px 14px",
    transition: "border-color 0.2s ease",
  },
  textarea: {
    flex: 1,
    background: "none",
    border: "none",
    outline: "none",
    color: "var(--text-primary)",
    fontSize: 14,
    fontFamily: "var(--font-body)",
    resize: "none",
    lineHeight: 1.6,
    paddingTop: 4,
    minHeight: 28,
    maxHeight: 120,
    overflowY: "auto",
  },
  sendBtn: {
    width: 36,
    height: 36,
    borderRadius: 10,
    border: "none",
    fontSize: 15,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
    transition: "all 0.15s ease",
    cursor: "pointer",
  },
  loadingDots: {
    display: "flex",
    gap: 3,
    alignItems: "center",
  },
  hint: {
    fontSize: 11,
    color: "var(--text-muted)",
    marginTop: 5,
    paddingLeft: 4,
  },
};