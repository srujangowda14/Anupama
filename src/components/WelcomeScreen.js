import React, { useState } from "react";

const MODES = [
  {
    id: "support",
    icon: "🌿",
    label: "Support Buddy",
    desc: "Empathetic listening, coping tools & journaling prompts",
    accent: "#6B9E7A",
  },
  {
    id: "cbt",
    icon: "🧠",
    label: "CBT Coach",
    desc: "Thought records, distortion reframes & Socratic questioning",
    accent: "#7B7FD4",
  },
  {
    id: "intake",
    icon: "📋",
    label: "Intake Assistant",
    desc: "Organize your thoughts before seeing a therapist",
    accent: "#C8944A",
  },
];

export default function WelcomeScreen({ onStart, profile }) {
  const [selected, setSelected] = useState("support");
  const [name, setName] = useState(profile?.name || "");
  const [email, setEmail] = useState(profile?.email || "");
  const [goals, setGoals] = useState((profile?.goals || []).join(", "));
  const [starting, setStarting] = useState(false);

  const handleStart = async () => {
    setStarting(true);
    try {
      await onStart(selected, {
        name: name.trim() || "Anupama user",
        email: email.trim() || null,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        goals: goals.split(",").map((goal) => goal.trim()).filter(Boolean),
      });
    } finally {
      setStarting(false);
    }
  };

  return (
    <div style={styles.root}>
      {/* Ambient glow */}
      <div style={styles.glow} />

      <div style={styles.card} className="fade-up">
        {/* Avatar */}
        <div style={styles.avatarWrap}>
          <div style={styles.avatar}>🌿</div>
          <div style={styles.avatarRing} />
        </div>

        <h1 style={styles.title}>Anupama</h1>
        <p style={styles.subtitle}>
          A safe space to be heard — powered by a model trained entirely from scratch.
        </p>

        {/* Disclaimer */}
        <div style={styles.disclaimer}>
          <span style={{ fontSize: 13 }}>⚠️</span>
          <span>
            This is a research project, not a licensed clinical tool. In a crisis, call{" "}
            <strong style={{ color: "#C8944A" }}>988</strong>.
          </span>
        </div>

        <p style={styles.pickLabel}>Create your profile</p>
        <div style={styles.profileForm}>
          <input style={styles.input} value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" />
          <input style={styles.input} value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email (optional)" />
          <textarea style={{ ...styles.input, minHeight: 64, resize: "vertical" }} value={goals} onChange={(e) => setGoals(e.target.value)} placeholder="Goals for therapy, separated by commas" />
        </div>

        {/* Mode picker */}
        <p style={styles.pickLabel}>Choose your session type</p>
        <div style={styles.modeGrid}>
          {MODES.map((m) => (
            <button
              key={m.id}
              onClick={() => setSelected(m.id)}
              style={{
                ...styles.modeCard,
                borderColor: selected === m.id ? m.accent : "rgba(255,255,255,0.08)",
                background:
                  selected === m.id
                    ? `linear-gradient(135deg, ${m.accent}18, ${m.accent}08)`
                    : "rgba(255,255,255,0.02)",
              }}
            >
              <span style={styles.modeIcon}>{m.icon}</span>
              <span
                style={{
                  ...styles.modeLabel,
                  color: selected === m.id ? m.accent : "var(--text-primary)",
                }}
              >
                {m.label}
              </span>
              <span style={styles.modeDesc}>{m.desc}</span>
            </button>
          ))}
        </div>

        <button
          onClick={handleStart}
          style={styles.startBtn}
          disabled={starting}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = "translateY(-2px)";
            e.currentTarget.style.boxShadow = "0 8px 32px rgba(107,158,122,0.35)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = "translateY(0)";
            e.currentTarget.style.boxShadow = "0 4px 20px rgba(107,158,122,0.2)";
          }}
        >
          {starting ? "Saving Profile..." : "Begin Session →"}
        </button>

        <p style={styles.footer}>
          Profiles, session memory, homework, and schedules stay linked across visits
        </p>
      </div>
    </div>
  );
}

const styles = {
  root: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "24px",
    position: "relative",
    overflow: "hidden",
  },
  glow: {
    position: "absolute",
    width: 600,
    height: 600,
    borderRadius: "50%",
    background: "radial-gradient(circle, rgba(107,158,122,0.06) 0%, transparent 70%)",
    top: "50%",
    left: "50%",
    transform: "translate(-50%, -50%)",
    pointerEvents: "none",
  },
  card: {
    width: "100%",
    maxWidth: 560,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 0,
  },
  avatarWrap: {
    position: "relative",
    marginBottom: 20,
  },
  avatar: {
    width: 72,
    height: 72,
    borderRadius: "50%",
    background: "linear-gradient(135deg, #2A3D2E, #1E3028)",
    border: "1.5px solid rgba(107,158,122,0.3)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 30,
    animation: "breathe 4s ease-in-out infinite",
    boxShadow: "0 0 24px rgba(107,158,122,0.15)",
  },
  avatarRing: {
    position: "absolute",
    inset: -6,
    borderRadius: "50%",
    border: "1px solid rgba(107,158,122,0.15)",
    pointerEvents: "none",
  },
  title: {
    fontFamily: "var(--font-display)",
    fontSize: 40,
    fontWeight: 500,
    letterSpacing: "-0.01em",
    color: "var(--text-primary)",
    marginBottom: 10,
  },
  subtitle: {
    fontSize: 15,
    color: "var(--text-secondary)",
    textAlign: "center",
    maxWidth: 380,
    lineHeight: 1.65,
    marginBottom: 24,
  },
  disclaimer: {
    display: "flex",
    alignItems: "flex-start",
    gap: 8,
    background: "rgba(200,148,74,0.07)",
    border: "1px solid rgba(200,148,74,0.2)",
    borderRadius: "var(--radius-md)",
    padding: "10px 14px",
    fontSize: 13,
    color: "#A09070",
    lineHeight: 1.5,
    marginBottom: 28,
    width: "100%",
  },
  pickLabel: {
    fontFamily: "var(--font-display)",
    fontStyle: "italic",
    fontSize: 14,
    color: "var(--text-muted)",
    alignSelf: "flex-start",
    marginBottom: 10,
  },
  profileForm: {
    width: "100%",
    marginBottom: 12,
  },
  input: {
    width: "100%",
    marginBottom: 10,
    padding: "12px 14px",
    borderRadius: "var(--radius-md)",
    border: "1px solid rgba(255,255,255,0.08)",
    background: "rgba(255,255,255,0.03)",
    color: "var(--text-primary)",
    fontSize: 14,
  },
  modeGrid: {
    display: "flex",
    gap: 10,
    width: "100%",
    marginBottom: 24,
  },
  modeCard: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-start",
    gap: 4,
    padding: "16px 14px",
    borderRadius: "var(--radius-md)",
    border: "1.5px solid",
    cursor: "pointer",
    transition: "all 0.2s ease",
    textAlign: "left",
  },
  modeIcon: { fontSize: 22, marginBottom: 2 },
  modeLabel: {
    fontFamily: "var(--font-display)",
    fontSize: 14,
    fontWeight: 500,
  },
  modeDesc: {
    fontSize: 11,
    color: "var(--text-muted)",
    lineHeight: 1.4,
  },
  startBtn: {
    width: "100%",
    padding: "15px",
    borderRadius: "var(--radius-md)",
    border: "none",
    background: "linear-gradient(135deg, #4E8A5E, #3A7050)",
    color: "#fff",
    fontSize: 15,
    fontWeight: 500,
    letterSpacing: "0.02em",
    boxShadow: "0 4px 20px rgba(107,158,122,0.2)",
    transition: "transform 0.15s ease, box-shadow 0.15s ease",
    marginBottom: 14,
  },
  footer: {
    fontSize: 11,
    color: "var(--text-muted)",
    letterSpacing: "0.03em",
  },
};
