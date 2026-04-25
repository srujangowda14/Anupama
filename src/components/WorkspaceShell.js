import React, { useCallback, useEffect, useMemo, useState } from "react";
import ChatScreen from "./ChatScreen";
import { api } from "../utils/api";
import { supabase } from "../utils/supabase";

const NAV_ITEMS = [
  { id: "chat", label: "Chat" },
  { id: "profile", label: "Profile" },
  { id: "sessions", label: "Sessions" },
  { id: "homework", label: "Homework" },
];

const MODE_OPTIONS = [
  { id: "support", label: "Support Buddy", icon: "🌿" },
  { id: "cbt", label: "CBT Coach", icon: "🧠" },
  { id: "intake", label: "Intake Assistant", icon: "📋" },
];

function pageFromHash() {
  const raw = window.location.hash.replace("#", "");
  return NAV_ITEMS.some((item) => item.id === raw) ? raw : "chat";
}

export default function WorkspaceShell({ profile, session, onProfileUpdate }) {
  const [page, setPage] = useState(pageFromHash());
  const [mode, setMode] = useState(profile?.preferred_mode || "support");
  const [chatSeed, setChatSeed] = useState(0);
  const [dashboard, setDashboard] = useState(null);
  const [loadingDashboard, setLoadingDashboard] = useState(false);

  useEffect(() => {
    setMode(profile?.preferred_mode || "support");
  }, [profile?.preferred_mode]);

  useEffect(() => {
    if (!window.location.hash) {
      window.location.hash = "chat";
    }
    const handleHashChange = () => setPage(pageFromHash());
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  const refreshDashboard = useCallback(async () => {
    if (!profile?.id) return;
    setLoadingDashboard(true);
    try {
      const data = await api.getDashboard(profile.id);
      setDashboard(data);
      if (data.profile) {
        onProfileUpdate(data.profile);
      }
    } finally {
      setLoadingDashboard(false);
    }
  }, [profile?.id, onProfileUpdate]);

  useEffect(() => {
    refreshDashboard();
  }, [refreshDashboard]);

  const goTo = (nextPage) => {
    window.location.hash = nextPage;
    setPage(nextPage);
  };

  const startSession = (nextMode) => {
    setMode(nextMode);
    setChatSeed((value) => value + 1);
    goTo("chat");
  };

  const welcomeSummary = useMemo(() => {
    const sessions = dashboard?.recent_sessions || [];
    const withSummary = sessions.filter((item) => item.summary);
    return withSummary.length ? withSummary[withSummary.length - 1].summary : null;
  }, [dashboard]);

  return (
    <div style={styles.root}>
      <aside style={styles.sidebar}>
        <div style={styles.brandBlock}>
          <div style={styles.logo}>🌿</div>
          <div>
            <div style={styles.brandTitle}>Anupama</div>
            <div style={styles.brandSub}>{profile?.name || session?.user?.email || "Your account"}</div>
          </div>
        </div>

        <div style={styles.navList}>
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              onClick={() => goTo(item.id)}
              style={{
                ...styles.navButton,
                background: page === item.id ? "rgba(107,158,122,0.16)" : "transparent",
                color: page === item.id ? "#6B9E7A" : "var(--text-secondary)",
              }}
            >
              {item.label}
            </button>
          ))}
        </div>

        <div style={styles.sidebarCard}>
          <div style={styles.sidebarLabel}>Treatment phase</div>
          <div style={styles.phaseTitle}>{dashboard?.treatment_plan?.phase_title || "Getting started"}</div>
          <p style={styles.sidebarText}>
            {dashboard?.treatment_plan?.guidance || "Once a few sessions are complete, Anupama will help structure the work and plan how treatment eventually winds down."}
          </p>
        </div>

        <div style={styles.sidebarCard}>
          <div style={styles.sidebarLabel}>Quick start</div>
          {MODE_OPTIONS.map((option) => (
            <button
              key={option.id}
              onClick={() => startSession(option.id)}
              style={styles.quickModeBtn}
            >
              <span>{option.icon}</span>
              <span>{option.label}</span>
            </button>
          ))}
        </div>

        <a href="tel:988" style={styles.crisisBtn}>
          🆘 988 Crisis Line
        </a>
      </aside>

      <main style={styles.main}>
        <section style={{ ...styles.pageSection, display: page === "chat" ? "flex" : "none" }}>
          <ChatScreen
            key={`${chatSeed}-${mode}`}
            mode={mode}
            profile={profile}
            onSessionActivity={refreshDashboard}
            onOpenPage={goTo}
          />
        </section>

        {page === "profile" && (
          <section style={styles.pageSection}>
            <ProfilePage
              profile={profile}
              accountEmail={session?.user?.email || ""}
              dashboard={dashboard}
              onProfileUpdate={onProfileUpdate}
              onRefresh={refreshDashboard}
            />
          </section>
        )}

        {page === "sessions" && (
          <section style={styles.pageSection}>
            <SessionsPage
              profile={profile}
              dashboard={dashboard}
              loading={loadingDashboard}
              onRefresh={refreshDashboard}
              onStartSession={startSession}
            />
          </section>
        )}

        {page === "homework" && (
          <section style={styles.pageSection}>
            <HomeworkPage
              dashboard={dashboard}
              onRefresh={refreshDashboard}
              onOpenSessions={() => goTo("sessions")}
            />
          </section>
        )}

        {page === "profile" && welcomeSummary && (
          <div style={styles.floatingNote}>
            <div style={styles.sidebarLabel}>What Anupama understands so far</div>
            <p style={styles.sidebarText}>{welcomeSummary}</p>
          </div>
        )}
      </main>
    </div>
  );
}

function ProfilePage({ profile, accountEmail, dashboard, onProfileUpdate, onRefresh }) {
  const [name, setName] = useState(profile?.name || "");
  const [dateOfBirth, setDateOfBirth] = useState(profile?.date_of_birth || "");
  const [gender, setGender] = useState(profile?.gender || "prefer_not_to_say");
  const [sexualOrientation, setSexualOrientation] = useState(profile?.sexual_orientation || "prefer_not_to_say");
  const [location, setLocation] = useState(profile?.location || "");
  const [timezone, setTimezone] = useState(profile?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone);
  const [goals, setGoals] = useState((profile?.goals || []).join(", "));
  const [preferredMode, setPreferredMode] = useState(profile?.preferred_mode || "support");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [showDelete, setShowDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    setName(profile?.name || "");
    setDateOfBirth(profile?.date_of_birth || "");
    setGender(profile?.gender || "prefer_not_to_say");
    setSexualOrientation(profile?.sexual_orientation || "prefer_not_to_say");
    setLocation(profile?.location || "");
    setTimezone(profile?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone);
    setGoals((profile?.goals || []).join(", "));
    setPreferredMode(profile?.preferred_mode || "support");
  }, [profile]);

  const saveProfile = async () => {
    setSaving(true);
    try {
      const result = await api.saveProfile({
        id: profile?.id,
        name: name.trim() || "Anupama user",
        email: accountEmail || profile?.email || null,
        timezone,
        goals: goals.split(",").map((goal) => goal.trim()).filter(Boolean),
        preferred_mode: preferredMode,
        date_of_birth: dateOfBirth || null,
        gender,
        sexual_orientation: sexualOrientation,
        location: location.trim() || null,
      });
      onProfileUpdate(result.profile);
      setSaved(true);
      setTimeout(() => setSaved(false), 1800);
      onRefresh();
    } finally {
      setSaving(false);
    }
  };

  const logout = async () => {
    await supabase.auth.signOut();
  };

  const deleteAccount = async () => {
    setDeleting(true);
    try {
      await api.deleteAccount();
      await supabase.auth.signOut();
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div style={styles.pageContent}>
      <div style={styles.pageHeader}>
        <div>
          <div style={styles.pageEyebrow}>Profile</div>
          <h1 style={styles.pageTitle}>Your care profile</h1>
          <p style={styles.pageDescription}>
            Keep the basics stable here so Anupama can remember who you are, what support you want, and how treatment should be paced over time.
          </p>
        </div>
      </div>

      <div style={styles.twoColGrid}>
        <div style={styles.panel}>
          <div style={styles.sectionTitle}>Account basics</div>
          <div style={styles.formGrid}>
            <label style={styles.labelBlock}>
              <span style={styles.label}>Name</span>
              <input style={styles.input} value={name} onChange={(e) => setName(e.target.value)} />
            </label>
            <label style={styles.labelBlock}>
              <span style={styles.label}>Account email</span>
              <input style={{ ...styles.input, opacity: 0.7 }} value={accountEmail || profile?.email || ""} readOnly />
            </label>
            <label style={styles.labelBlock}>
              <span style={styles.label}>Date of birth</span>
              <input style={styles.input} type="date" value={dateOfBirth} onChange={(e) => setDateOfBirth(e.target.value)} />
            </label>
            <label style={styles.labelBlock}>
              <span style={styles.label}>Location</span>
              <input style={styles.input} value={location} onChange={(e) => setLocation(e.target.value)} />
            </label>
            <label style={styles.labelBlock}>
              <span style={styles.label}>Gender</span>
              <select style={styles.input} value={gender} onChange={(e) => setGender(e.target.value)}>
                <option value="female">Female</option>
                <option value="male">Male</option>
                <option value="nonbinary">Nonbinary</option>
                <option value="questioning">Questioning</option>
                <option value="prefer_not_to_say">Prefer not to say</option>
              </select>
            </label>
            <label style={styles.labelBlock}>
              <span style={styles.label}>Sexual orientation</span>
              <select style={styles.input} value={sexualOrientation} onChange={(e) => setSexualOrientation(e.target.value)}>
                <option value="straight">Straight</option>
                <option value="gay">Gay</option>
                <option value="lesbian">Lesbian</option>
                <option value="bisexual">Bisexual</option>
                <option value="pansexual">Pansexual</option>
                <option value="asexual">Asexual</option>
                <option value="questioning">Questioning</option>
                <option value="prefer_not_to_say">Prefer not to say</option>
              </select>
            </label>
            <label style={styles.labelBlock}>
              <span style={styles.label}>Timezone</span>
              <input style={styles.input} value={timezone} onChange={(e) => setTimezone(e.target.value)} />
            </label>
            <label style={styles.labelBlock}>
              <span style={styles.label}>Preferred mode</span>
              <select style={styles.input} value={preferredMode} onChange={(e) => setPreferredMode(e.target.value)}>
                {MODE_OPTIONS.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <label style={{ ...styles.labelBlock, marginTop: 18 }}>
            <span style={styles.label}>What you want help with</span>
            <textarea
              style={{ ...styles.input, minHeight: 110, resize: "vertical" }}
              value={goals}
              onChange={(e) => setGoals(e.target.value)}
              placeholder="Comma-separated goals, such as managing catastrophizing, coping with school stress, or feeling less stuck after conflict."
            />
          </label>

          <div style={styles.actionRow}>
            <button onClick={saveProfile} style={styles.primaryBtn} disabled={saving}>
              {saving ? "Saving..." : "Save profile"}
            </button>
            {saved && <span style={styles.successNote}>Saved</span>}
          </div>
        </div>

        <div style={styles.panel}>
          <div style={styles.sectionTitle}>Treatment picture</div>
          <div style={styles.metricCard}>
            <div style={styles.metricValue}>{dashboard?.treatment_plan?.completed_sessions || 0}</div>
            <div style={styles.metricLabel}>completed sessions</div>
          </div>
          <p style={styles.panelText}>
            {dashboard?.treatment_plan?.guidance || "Your treatment strategy will update as more sessions are completed."}
          </p>
          <div style={styles.listBlock}>
            {(dashboard?.treatment_plan?.session_strategy || []).map((item) => (
              <div key={item} style={styles.bulletRow}>
                <span style={styles.bulletDot} />
                <span>{item}</span>
              </div>
            ))}
          </div>

          <div style={styles.sectionTitle}>Account actions</div>
          <div style={styles.actionRow}>
            <button onClick={logout} style={styles.secondaryWideBtn}>
              Log out
            </button>
            <button onClick={() => setShowDelete((value) => !value)} style={styles.ghostDangerBtn}>
              {showDelete ? "Never mind" : "Delete account"}
            </button>
          </div>

          {showDelete && (
            <div style={styles.deletePanel}>
              <div style={styles.sectionTitle}>Leave gracefully</div>
              <p style={styles.panelText}>
                If you delete your account, Anupama will remove your profile, saved sessions, homework, schedules, and ongoing treatment memory. This cannot be undone.
              </p>
              <button onClick={deleteAccount} style={styles.dangerBtn} disabled={deleting}>
                {deleting ? "Deleting..." : "Delete my account permanently"}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SessionsPage({ profile, dashboard, loading, onRefresh, onStartSession }) {
  const [title, setTitle] = useState("Follow-up Anupama session");
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [scheduling, setScheduling] = useState(false);

  const createSchedule = async () => {
    if (!profile?.id || !date || !time) return;
    setScheduling(true);
    try {
      const startAt = new Date(`${date}T${time}`).toISOString();
      const endAt = new Date(new Date(startAt).getTime() + 30 * 60 * 1000).toISOString();
      await api.scheduleSession(profile.id, {
        title,
        description: "Follow-up session created from Anupama",
        start_at: startAt,
        end_at: endAt,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      });
      setDate("");
      setTime("");
      onRefresh();
    } finally {
      setScheduling(false);
    }
  };

  return (
    <div style={styles.pageContent}>
      <div style={styles.pageHeader}>
        <div>
          <div style={styles.pageEyebrow}>Sessions</div>
          <h1 style={styles.pageTitle}>Your session arc</h1>
          <p style={styles.pageDescription}>
            CBT works best when sessions have an opening, a focused middle, and a closing action plan. This page keeps track of what has happened, what comes next, and when treatment should start winding down.
          </p>
        </div>
        <button onClick={onRefresh} style={styles.secondaryWideBtn}>
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      <div style={styles.twoColGrid}>
        <div style={styles.panel}>
          <div style={styles.sectionTitle}>Treatment roadmap</div>
          <div style={styles.metricGrid}>
            <div style={styles.metricCard}>
              <div style={styles.metricValue}>{dashboard?.treatment_plan?.completed_sessions || 0}</div>
              <div style={styles.metricLabel}>sessions done</div>
            </div>
            <div style={styles.metricCard}>
              <div style={styles.metricValue}>{dashboard?.treatment_plan?.target_sessions || 0}</div>
              <div style={styles.metricLabel}>target sessions</div>
            </div>
            <div style={styles.metricCard}>
              <div style={styles.metricValue}>{dashboard?.treatment_plan?.estimated_sessions_remaining || 0}</div>
              <div style={styles.metricLabel}>likely remaining</div>
            </div>
          </div>
          <p style={styles.panelText}>{dashboard?.treatment_plan?.guidance}</p>
          <div style={styles.listBlock}>
            {(dashboard?.treatment_plan?.ending_signals || []).map((item) => (
              <div key={item} style={styles.bulletRow}>
                <span style={styles.bulletDot} />
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>

        <div style={styles.panel}>
          <div style={styles.sectionTitle}>Start a new session</div>
          <div style={styles.quickGrid}>
            {MODE_OPTIONS.map((option) => (
              <button key={option.id} onClick={() => onStartSession(option.id)} style={styles.modeCard}>
                <span style={{ fontSize: 22 }}>{option.icon}</span>
                <span style={styles.modeCardTitle}>{option.label}</span>
              </button>
            ))}
          </div>

          <div style={{ ...styles.sectionTitle, marginTop: 22 }}>Schedule your next one</div>
          <label style={styles.labelBlock}>
            <span style={styles.label}>Session title</span>
            <input style={styles.input} value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <div style={styles.formGrid}>
            <label style={styles.labelBlock}>
              <span style={styles.label}>Date</span>
              <input style={styles.input} type="date" value={date} onChange={(e) => setDate(e.target.value)} />
            </label>
            <label style={styles.labelBlock}>
              <span style={styles.label}>Time</span>
              <input style={styles.input} type="time" value={time} onChange={(e) => setTime(e.target.value)} />
            </label>
          </div>
          <button onClick={createSchedule} style={styles.primaryBtn} disabled={scheduling || !date || !time}>
            {scheduling ? "Creating..." : "Add to Google Calendar"}
          </button>
        </div>
      </div>

      <div style={styles.twoColGrid}>
        <div style={styles.panel}>
          <div style={styles.sectionTitle}>Upcoming sessions</div>
          {dashboard?.upcoming_sessions?.length ? (
            dashboard.upcoming_sessions.map((item) => (
              <a key={item.id} href={item.calendar_url} target="_blank" rel="noreferrer" style={styles.sessionCard}>
                <div style={styles.sessionTitle}>{item.title}</div>
                <div style={styles.sessionMeta}>{new Date(item.start_at).toLocaleString()}</div>
              </a>
            ))
          ) : (
            <p style={styles.panelText}>No follow-up is scheduled yet.</p>
          )}
        </div>

        <div style={styles.panel}>
          <div style={styles.sectionTitle}>Session history</div>
          {dashboard?.recent_sessions?.length ? (
            dashboard.recent_sessions.map((item) => (
              <div key={item.id} style={styles.sessionCardStatic}>
                <div style={styles.sessionTitle}>{item.title || `${item.mode} session`}</div>
                <div style={styles.sessionMeta}>
                  {item.mode} · {new Date(item.created_at).toLocaleString()}
                </div>
                {item.summary && <p style={styles.sessionSummary}>{item.summary}</p>}
              </div>
            ))
          ) : (
            <p style={styles.panelText}>No sessions yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}

function HomeworkPage({ dashboard, onRefresh, onOpenSessions }) {
  const homeworkItems = dashboard?.all_homework || [];

  return (
    <div style={styles.pageContent}>
      <div style={styles.pageHeader}>
        <div>
          <div style={styles.pageEyebrow}>Homework</div>
          <h1 style={styles.pageTitle}>Between-session practice</h1>
          <p style={styles.pageDescription}>
            Homework starts after the first session. It is used to carry one focused CBT skill between sessions, then checked near the start of the next one.
          </p>
        </div>
      </div>

      <div style={styles.twoColGrid}>
        <div style={styles.panel}>
          <div style={styles.sectionTitle}>How homework is being used</div>
          <div style={styles.listBlock}>
            {(dashboard?.treatment_plan?.session_strategy || []).map((item) => (
              <div key={item} style={styles.bulletRow}>
                <span style={styles.bulletDot} />
                <span>{item}</span>
              </div>
            ))}
          </div>
          <button onClick={onOpenSessions} style={styles.secondaryWideBtn}>
            Plan next session
          </button>
        </div>

        <div style={styles.panel}>
          <div style={styles.sectionTitle}>Pending homework</div>
          {dashboard?.pending_homework?.length ? (
            dashboard.pending_homework.map((item) => (
              <HomeworkCard key={item.id} item={item} onRefresh={onRefresh} />
            ))
          ) : (
            <p style={styles.panelText}>No homework is currently pending. After the first session, CBT sessions will start assigning a focused exercise at the end of the session.</p>
          )}
        </div>
      </div>

      <div style={styles.panel}>
        <div style={styles.sectionTitle}>All assignments</div>
        {homeworkItems.length ? (
          homeworkItems.map((item) => <HomeworkCard key={item.id} item={item} onRefresh={onRefresh} compact={item.status === "completed"} />)
        ) : (
          <p style={styles.panelText}>No assignments yet.</p>
        )}
      </div>
    </div>
  );
}

function HomeworkCard({ item, onRefresh, compact = false }) {
  const [reflection, setReflection] = useState(item.reflection || "");
  const [saving, setSaving] = useState(false);

  const updateStatus = async (status) => {
    setSaving(true);
    try {
      await api.updateHomework(item.id, { status, reflection: reflection || null });
      onRefresh();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={styles.homeworkCard}>
      <div style={styles.homeworkHeader}>
        <div>
          <div style={styles.sessionTitle}>{item.title}</div>
          <div style={styles.sessionMeta}>
            {item.status.replace("_", " ")}
            {item.due_at ? ` · due ${new Date(item.due_at).toLocaleDateString()}` : ""}
          </div>
        </div>
        <div style={styles.statusPill}>{item.status}</div>
      </div>
      <p style={styles.panelText}>{item.instructions}</p>
      <textarea
        style={{ ...styles.input, minHeight: compact ? 84 : 110, resize: "vertical" }}
        value={reflection}
        onChange={(e) => setReflection(e.target.value)}
        placeholder="What did you notice while doing it? What got in the way?"
      />
      <div style={styles.actionRow}>
        <button onClick={() => updateStatus("in_progress")} style={styles.secondaryWideBtn} disabled={saving}>
          Mark in progress
        </button>
        <button onClick={() => updateStatus("completed")} style={styles.primaryBtn} disabled={saving}>
          {saving ? "Saving..." : "Mark complete"}
        </button>
      </div>
    </div>
  );
}

const styles = {
  root: {
    display: "flex",
    minHeight: "100vh",
    background: "var(--bg-deep)",
  },
  sidebar: {
    width: 280,
    flexShrink: 0,
    borderRight: "1px solid var(--border-subtle)",
    background: "rgba(17,19,16,0.92)",
    padding: 22,
    display: "flex",
    flexDirection: "column",
    gap: 18,
  },
  brandBlock: {
    display: "flex",
    alignItems: "center",
    gap: 12,
  },
  logo: {
    width: 46,
    height: 46,
    borderRadius: "50%",
    background: "linear-gradient(135deg, #2A3D2E, #1E3028)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 19,
    border: "1px solid rgba(107,158,122,0.25)",
  },
  brandTitle: {
    fontFamily: "var(--font-display)",
    fontSize: 20,
    color: "var(--text-primary)",
  },
  brandSub: {
    fontSize: 12,
    color: "var(--text-secondary)",
  },
  navList: {
    display: "grid",
    gap: 8,
  },
  navButton: {
    border: "none",
    textAlign: "left",
    borderRadius: 12,
    padding: "12px 14px",
    fontSize: 14,
    cursor: "pointer",
  },
  sidebarCard: {
    border: "1px solid var(--border-subtle)",
    borderRadius: 18,
    padding: 16,
    background: "rgba(255,255,255,0.02)",
  },
  sidebarLabel: {
    fontSize: 11,
    letterSpacing: "0.14em",
    textTransform: "uppercase",
    color: "var(--text-muted)",
    marginBottom: 8,
  },
  phaseTitle: {
    fontFamily: "var(--font-display)",
    fontSize: 18,
    color: "var(--text-primary)",
    marginBottom: 8,
  },
  sidebarText: {
    fontSize: 12,
    lineHeight: 1.65,
    color: "var(--text-secondary)",
    whiteSpace: "pre-wrap",
  },
  quickModeBtn: {
    width: "100%",
    border: "1px solid var(--border-subtle)",
    background: "rgba(255,255,255,0.03)",
    color: "var(--text-primary)",
    borderRadius: 12,
    padding: "10px 12px",
    fontSize: 12,
    display: "flex",
    gap: 10,
    alignItems: "center",
    cursor: "pointer",
    marginBottom: 8,
  },
  crisisBtn: {
    marginTop: "auto",
    textDecoration: "none",
    textAlign: "center",
    borderRadius: 14,
    padding: "12px 14px",
    background: "rgba(192,64,64,0.12)",
    border: "1px solid rgba(192,64,64,0.24)",
    color: "#E1B4B4",
    fontSize: 13,
  },
  main: {
    flex: 1,
    minWidth: 0,
    minHeight: "100vh",
    position: "relative",
  },
  pageSection: {
    height: "100vh",
    overflowY: "auto",
    flexDirection: "column",
  },
  pageContent: {
    padding: "28px 32px 40px",
  },
  pageHeader: {
    display: "flex",
    justifyContent: "space-between",
    gap: 16,
    alignItems: "flex-start",
    marginBottom: 24,
  },
  pageEyebrow: {
    fontSize: 11,
    letterSpacing: "0.16em",
    textTransform: "uppercase",
    color: "var(--text-muted)",
    marginBottom: 8,
  },
  pageTitle: {
    fontFamily: "var(--font-display)",
    fontSize: 34,
    color: "var(--text-primary)",
    marginBottom: 10,
  },
  pageDescription: {
    maxWidth: 760,
    fontSize: 14,
    color: "var(--text-secondary)",
    lineHeight: 1.7,
  },
  twoColGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
    gap: 18,
    marginBottom: 18,
  },
  panel: {
    border: "1px solid var(--border-subtle)",
    borderRadius: 22,
    padding: 20,
    background: "rgba(255,255,255,0.02)",
  },
  sectionTitle: {
    fontFamily: "var(--font-display)",
    fontSize: 20,
    color: "var(--text-primary)",
    marginBottom: 14,
  },
  formGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
    gap: 14,
  },
  labelBlock: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  label: {
    fontSize: 12,
    color: "var(--text-secondary)",
  },
  input: {
    width: "100%",
    padding: "12px 14px",
    borderRadius: 14,
    border: "1px solid var(--border-subtle)",
    background: "rgba(255,255,255,0.03)",
    color: "var(--text-primary)",
    fontSize: 14,
  },
  primaryBtn: {
    border: "none",
    borderRadius: 14,
    padding: "12px 18px",
    background: "linear-gradient(135deg, #4E8A5E, #3A7050)",
    color: "#fff",
    fontSize: 14,
    cursor: "pointer",
  },
  secondaryWideBtn: {
    border: "1px solid var(--border-subtle)",
    borderRadius: 14,
    padding: "12px 18px",
    background: "rgba(255,255,255,0.03)",
    color: "var(--text-primary)",
    fontSize: 14,
    cursor: "pointer",
  },
  ghostDangerBtn: {
    border: "1px solid rgba(192,64,64,0.24)",
    borderRadius: 14,
    padding: "12px 18px",
    background: "rgba(192,64,64,0.08)",
    color: "#E1B4B4",
    fontSize: 14,
    cursor: "pointer",
  },
  dangerBtn: {
    width: "100%",
    border: "1px solid rgba(192,64,64,0.24)",
    borderRadius: 14,
    padding: "12px 18px",
    background: "linear-gradient(135deg, rgba(140,46,46,0.92), rgba(108,34,34,0.92))",
    color: "#fff",
    fontSize: 14,
    cursor: "pointer",
  },
  deletePanel: {
    marginTop: 16,
    padding: 18,
    borderRadius: 18,
    border: "1px solid rgba(192,64,64,0.22)",
    background: "rgba(192,64,64,0.07)",
  },
  actionRow: {
    display: "flex",
    gap: 12,
    alignItems: "center",
    flexWrap: "wrap",
    marginTop: 16,
  },
  successNote: {
    fontSize: 12,
    color: "#6B9E7A",
  },
  panelText: {
    fontSize: 13,
    color: "var(--text-secondary)",
    lineHeight: 1.7,
  },
  metricGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
    gap: 12,
    marginBottom: 16,
  },
  metricCard: {
    borderRadius: 18,
    border: "1px solid var(--border-subtle)",
    background: "rgba(255,255,255,0.03)",
    padding: 16,
  },
  metricValue: {
    fontFamily: "var(--font-display)",
    fontSize: 28,
    color: "var(--text-primary)",
  },
  metricLabel: {
    fontSize: 11,
    color: "var(--text-muted)",
    marginTop: 6,
    textTransform: "uppercase",
    letterSpacing: "0.1em",
  },
  listBlock: {
    display: "grid",
    gap: 10,
    marginTop: 14,
  },
  bulletRow: {
    display: "flex",
    gap: 10,
    alignItems: "flex-start",
    color: "var(--text-secondary)",
    fontSize: 13,
    lineHeight: 1.6,
  },
  bulletDot: {
    width: 8,
    height: 8,
    borderRadius: "50%",
    background: "#6B9E7A",
    marginTop: 7,
    flexShrink: 0,
  },
  quickGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
    gap: 12,
  },
  modeCard: {
    border: "1px solid var(--border-subtle)",
    borderRadius: 18,
    padding: 18,
    background: "rgba(255,255,255,0.03)",
    color: "var(--text-primary)",
    display: "flex",
    flexDirection: "column",
    gap: 8,
    cursor: "pointer",
    textAlign: "left",
  },
  modeCardTitle: {
    fontSize: 14,
  },
  sessionCard: {
    display: "block",
    textDecoration: "none",
    borderRadius: 16,
    border: "1px solid var(--border-subtle)",
    padding: 16,
    background: "rgba(255,255,255,0.03)",
    marginBottom: 12,
  },
  sessionCardStatic: {
    borderRadius: 16,
    border: "1px solid var(--border-subtle)",
    padding: 16,
    background: "rgba(255,255,255,0.03)",
    marginBottom: 12,
  },
  sessionTitle: {
    fontSize: 15,
    color: "var(--text-primary)",
    marginBottom: 6,
  },
  sessionMeta: {
    fontSize: 11,
    color: "var(--text-muted)",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
  },
  sessionSummary: {
    marginTop: 10,
    fontSize: 12,
    color: "var(--text-secondary)",
    lineHeight: 1.65,
    whiteSpace: "pre-wrap",
  },
  homeworkCard: {
    borderRadius: 18,
    border: "1px solid var(--border-subtle)",
    background: "rgba(255,255,255,0.03)",
    padding: 16,
    marginBottom: 14,
  },
  homeworkHeader: {
    display: "flex",
    justifyContent: "space-between",
    gap: 14,
    alignItems: "flex-start",
    marginBottom: 10,
  },
  statusPill: {
    borderRadius: 999,
    border: "1px solid rgba(107,158,122,0.28)",
    color: "#6B9E7A",
    padding: "4px 10px",
    fontSize: 11,
    textTransform: "capitalize",
    flexShrink: 0,
  },
  floatingNote: {
    position: "absolute",
    right: 24,
    bottom: 24,
    width: 300,
    padding: 16,
    borderRadius: 18,
    border: "1px solid var(--border-subtle)",
    background: "rgba(12,14,12,0.9)",
    boxShadow: "var(--shadow-soft)",
  },
};
