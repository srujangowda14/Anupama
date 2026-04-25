import React, { useState } from "react";
import { api } from "../utils/api";

// ─── Coping Exercises ────────────────────────────────────────────────────────

const EXERCISES = [
  {
    title: "Box Breathing",
    icon: "🌬️",
    steps: ["Inhale for 4 seconds", "Hold for 4 seconds", "Exhale for 4 seconds", "Hold for 4 seconds"],
  },
  {
    title: "5-4-3-2-1 Grounding",
    icon: "🌱",
    steps: ["Name 5 things you can see", "4 things you can touch", "3 things you can hear", "2 things you can smell", "1 thing you can taste"],
  },
  {
    title: "Progressive Relaxation",
    icon: "✨",
    steps: ["Tense your feet for 5 seconds", "Release completely", "Move up to your calves", "Repeat up your whole body"],
  },
  {
    title: "Thought Record",
    icon: "📝",
    steps: ["What's the situation?", "What's the automatic thought?", "What emotions do you feel?", "What evidence supports/challenges it?", "What's a more balanced view?"],
  },
];

export function CopingPanel() {
  const [open, setOpen] = useState(null);

  return (
    <div>
      <p style={styles.sectionLabel}>Quick exercises</p>
      {EXERCISES.map((ex, i) => (
        <div key={i} style={styles.exerciseCard}>
          <button
            onClick={() => setOpen(open === i ? null : i)}
            style={styles.exerciseHeader}
          >
            <span style={{ fontSize: 16 }}>{ex.icon}</span>
            <span style={{ fontSize: 13, color: "var(--text-primary)", flex: 1, textAlign: "left" }}>
              {ex.title}
            </span>
            <span style={{ fontSize: 10, color: "var(--text-muted)" }}>
              {open === i ? "▲" : "▼"}
            </span>
          </button>
          {open === i && (
            <div style={styles.steps} className="slide-in">
              {ex.steps.map((step, j) => (
                <div key={j} style={styles.step}>
                  <div style={styles.stepNum}>{j + 1}</div>
                  <span style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.5 }}>
                    {step}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ─── Session Summary ─────────────────────────────────────────────────────────

export function SummaryPanel({ sessionId }) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetch = async () => {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getSummary(sessionId);
      setSummary(data.summary);
    } catch (e) {
      setError("Couldn't generate summary. Have a conversation first.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <p style={styles.sectionLabel}>Clinician-ready summary</p>
      <p style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 12, lineHeight: 1.5 }}>
        A structured overview of this session you can share with a therapist.
      </p>

      {!summary && !loading && (
        <button
          onClick={fetch}
          disabled={!sessionId}
          style={{
            ...styles.generateBtn,
            opacity: sessionId ? 1 : 0.4,
            cursor: sessionId ? "pointer" : "not-allowed",
          }}
        >
          {sessionId ? "Generate Summary" : "Start a session first"}
        </button>
      )}

      {loading && (
        <p style={{ fontSize: 12, color: "var(--text-muted)" }}>Generating…</p>
      )}

      {error && (
        <p style={{ fontSize: 12, color: "var(--terracotta)" }}>{error}</p>
      )}

      {summary && (
        <div style={styles.summaryBox} className="fade-up">
          <pre style={styles.summaryText}>{summary}</pre>
          <button onClick={() => setSummary(null)} style={styles.resetBtn}>
            Regenerate
          </button>
        </div>
      )}
    </div>
  );
}

export function ProfilePanel({ profile, onProfileUpdate }) {
  const [name, setName] = useState(profile?.name || "");
  const [email, setEmail] = useState(profile?.email || "");
  const [goals, setGoals] = useState((profile?.goals || []).join(", "));
  const [saved, setSaved] = useState(false);

  const save = async () => {
    const data = await api.saveProfile({
      id: profile?.id || localStorage.getItem("anupama_profile_id"),
      name: name.trim() || "Anupama user",
      email: email.trim() || null,
      timezone: profile?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
      goals: goals.split(",").map((goal) => goal.trim()).filter(Boolean),
      preferred_mode: profile?.preferred_mode || "support",
    });
    localStorage.setItem("anupama_profile_id", data.profile.id);
    onProfileUpdate(data.profile);
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  };

  return (
    <div>
      <p style={styles.sectionLabel}>Your profile</p>
      <input style={styles.input} value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" />
      <input style={styles.input} value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
      <textarea style={{ ...styles.input, minHeight: 68, resize: "vertical" }} value={goals} onChange={(e) => setGoals(e.target.value)} placeholder="Goals, separated by commas" />
      <button onClick={save} style={styles.generateBtn}>Save Profile</button>
      {saved && <p style={{ fontSize: 12, color: "#6B9E7A", marginTop: 8 }}>Saved</p>}
    </div>
  );
}

export function CarePlanPanel({ profileId, latestHomework, previousSummary }) {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(false);
  const [title, setTitle] = useState("Follow-up Anupama session");
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");

  const refresh = async () => {
    if (!profileId) return;
    setLoading(true);
    try {
      const data = await api.getDashboard(profileId);
      setDashboard(data);
    } finally {
      setLoading(false);
    }
  };

  const schedule = async () => {
    if (!profileId || !date || !time) return;
    const startAt = new Date(`${date}T${time}`).toISOString();
    const endAt = new Date(new Date(startAt).getTime() + 30 * 60 * 1000).toISOString();
    await api.scheduleSession(profileId, {
      title,
      description: "Follow-up session created from Anupama",
      start_at: startAt,
      end_at: endAt,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    });
    refresh();
  };

  const completeHomework = async (item) => {
    await api.updateHomework(item.id, { status: "completed", reflection: "Completed in app" });
    refresh();
  };

  return (
    <div>
      <p style={styles.sectionLabel}>Continuity plan</p>
      <button onClick={refresh} style={styles.generateBtn}>{loading ? "Refreshing..." : "Refresh Memory"}</button>

      {previousSummary && (
        <div style={styles.summaryBox}>
          <p style={styles.helperLabel}>Previous session context</p>
          <pre style={styles.summaryText}>{previousSummary}</pre>
        </div>
      )}

      {latestHomework && (
        <div style={styles.exerciseCard}>
          <div style={styles.exerciseHeader}>
            <span style={{ fontSize: 16 }}>📝</span>
            <span style={{ fontSize: 13, color: "var(--text-primary)", flex: 1, textAlign: "left" }}>{latestHomework.title}</span>
          </div>
          <div style={{ padding: "0 12px 12px", fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.5 }}>
            {latestHomework.instructions}
          </div>
        </div>
      )}

      {dashboard?.pending_homework?.length > 0 && (
        <>
          <p style={{ ...styles.sectionLabel, marginTop: 14 }}>Open homework</p>
          {dashboard.pending_homework.slice(0, 3).map((item) => (
            <div key={item.id} style={styles.logRow}>
              <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{item.title}</span>
              <button onClick={() => completeHomework(item)} style={styles.inlineBtn}>Done</button>
            </div>
          ))}
        </>
      )}

      <p style={{ ...styles.sectionLabel, marginTop: 14 }}>Schedule your next session</p>
      <input style={styles.input} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Session title" />
      <input style={styles.input} type="date" value={date} onChange={(e) => setDate(e.target.value)} />
      <input style={styles.input} type="time" value={time} onChange={(e) => setTime(e.target.value)} />
      <button onClick={schedule} style={styles.generateBtn}>Create Calendar Event</button>

      {dashboard?.upcoming_sessions?.length > 0 && (
        <>
          <p style={{ ...styles.sectionLabel, marginTop: 14 }}>Upcoming sessions</p>
          {dashboard.upcoming_sessions.slice(0, 3).map((item) => (
            <a key={item.id} href={item.calendar_url} target="_blank" rel="noreferrer" style={styles.logRow}>
              <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{item.title}</span>
              <span style={{ marginLeft: "auto", fontSize: 11, color: "#6B9E7A" }}>Open</span>
            </a>
          ))}
        </>
      )}
    </div>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────────────

const styles = {
  sectionLabel: {
    fontFamily: "var(--font-display)",
    fontStyle: "italic",
    fontSize: 13,
    color: "var(--text-muted)",
    marginBottom: 10,
  },
  exerciseCard: {
    background: "rgba(255,255,255,0.02)",
    border: "1px solid var(--border-subtle)",
    borderRadius: "var(--radius-sm)",
    marginBottom: 6,
    overflow: "hidden",
  },
  exerciseHeader: {
    width: "100%",
    background: "none",
    border: "none",
    padding: "10px 12px",
    display: "flex",
    alignItems: "center",
    gap: 8,
    cursor: "pointer",
  },
  steps: { padding: "0 12px 12px" },
  step: {
    display: "flex",
    gap: 8,
    alignItems: "flex-start",
    marginBottom: 6,
  },
  stepNum: {
    width: 18,
    height: 18,
    borderRadius: "50%",
    background: "rgba(107,158,122,0.2)",
    color: "#6B9E7A",
    fontSize: 10,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
    marginTop: 1,
  },
  generateBtn: {
    width: "100%",
    padding: "10px",
    borderRadius: "var(--radius-sm)",
    border: "1px solid var(--border-mid)",
    background: "rgba(255,255,255,0.04)",
    color: "var(--text-secondary)",
    fontSize: 13,
    transition: "background 0.15s ease",
  },
  summaryBox: {
    background: "rgba(255,255,255,0.02)",
    border: "1px solid var(--border-subtle)",
    borderRadius: "var(--radius-sm)",
    padding: 12,
  },
  summaryText: {
    fontSize: 11,
    color: "var(--text-secondary)",
    whiteSpace: "pre-wrap",
    lineHeight: 1.7,
    fontFamily: "var(--font-body)",
    marginBottom: 10,
  },
  resetBtn: {
    fontSize: 11,
    color: "var(--text-muted)",
    background: "none",
    border: "none",
    cursor: "pointer",
    padding: 0,
    textDecoration: "underline",
  },
  input: {
    width: "100%",
    marginBottom: 8,
    padding: "9px 10px",
    borderRadius: "var(--radius-sm)",
    border: "1px solid var(--border-subtle)",
    background: "rgba(255,255,255,0.03)",
    color: "var(--text-primary)",
    fontSize: 12,
  },
  helperLabel: {
    fontSize: 11,
    color: "var(--text-muted)",
    marginBottom: 6,
  },
  logRow: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "8px 10px",
    background: "rgba(255,255,255,0.02)",
    borderRadius: "var(--radius-sm)",
    border: "1px solid var(--border-subtle)",
    marginBottom: 6,
  },
  inlineBtn: {
    marginLeft: "auto",
    background: "none",
    border: "none",
    color: "#6B9E7A",
    fontSize: 11,
  },
};
