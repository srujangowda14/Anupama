import React, { useState } from "react";
import ChatScreen from "./ChatScreen";
import { CarePlanPanel, ProfilePanel, SummaryPanel } from "./SidebarPanels";
import { api } from "../utils/api";

const PAGES = [
  { id: "chat", label: "Chat" },
  { id: "profile", label: "Profile" },
  { id: "sessions", label: "Sessions" },
  { id: "homework", label: "Homework" },
];

export default function AppShell({ profile, mode, onModeChange, onProfileUpdate }) {
  const [page, setPage] = useState("chat");

  return (
    <div style={styles.root}>
      <aside style={styles.sidebar}>
        <div style={styles.brand}>
          <div style={styles.brandAvatar}>🌿</div>
          <div>
            <div style={styles.brandName}>Anupama</div>
            <div style={styles.brandMeta}>{profile?.name || "Your account"}</div>
          </div>
        </div>

        <div style={styles.nav}>
          {PAGES.map((item) => (
            <button
              key={item.id}
              onClick={() => setPage(item.id)}
              style={{
                ...styles.navBtn,
                background: page === item.id ? "rgba(107,158,122,0.14)" : "transparent",
                color: page === item.id ? "#6B9E7A" : "var(--text-secondary)",
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      </aside>

      <main style={styles.main}>
        {page === "chat" && (
          <ChatScreen mode={mode} onModeChange={onModeChange} profile={profile} />
        )}
        {page === "profile" && (
          <ProfilePage profile={profile} onProfileUpdate={onProfileUpdate} />
        )}
        {page === "sessions" && (
          <SessionsPage profile={profile} />
        )}
        {page === "homework" && (
          <HomeworkPage profile={profile} />
        )}
      </main>
    </div>
  );
}

function PageCard({ title, subtitle, children }) {
  return (
    <div style={styles.pageWrap}>
      <div style={styles.pageHeader}>
        <div style={styles.pageTitle}>{title}</div>
        {subtitle && <div style={styles.pageSubtitle}>{subtitle}</div>}
      </div>
      <div style={styles.pageBody}>{children}</div>
    </div>
  );
}

function ProfilePage({ profile, onProfileUpdate }) {
  return (
    <PageCard
      title="Profile"
      subtitle="Manage personal details, therapy goals, and account settings."
    >
      <ProfilePanel profile={profile} onProfileUpdate={onProfileUpdate} />
    </PageCard>
  );
}

function SessionsPage({ profile }) {
  const [dashboard, setDashboard] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const [mode, setMode] = React.useState(profile?.preferred_mode || "cbt");
  const [date, setDate] = React.useState("");
  const [time, setTime] = React.useState("");

  const refresh = React.useCallback(async () => {
    if (!profile?.id) return;
    setLoading(true);
    try {
      const data = await api.getDashboard(profile.id);
      setDashboard(data);
    } finally {
      setLoading(false);
    }
  }, [profile?.id]);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  const schedule = async () => {
    if (!profile?.id || !date || !time) return;
    const startAt = new Date(`${date}T${time}`).toISOString();
    const endAt = new Date(new Date(startAt).getTime() + 30 * 60 * 1000).toISOString();
    await api.scheduleSession(profile.id, {
      title: `${mode === "cbt" ? "CBT" : mode === "support" ? "Support" : "Intake"} follow-up`,
      description: "Follow-up session scheduled in Anupama",
      start_at: startAt,
      end_at: endAt,
      timezone: profile.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
    });
    refresh();
  };

  return (
    <PageCard
      title="Sessions"
      subtitle="Review past sessions, understand treatment phase, and schedule follow-ups."
    >
      <button onClick={refresh} style={styles.refreshBtn}>
        {loading ? "Refreshing..." : "Refresh"}
      </button>

      {dashboard?.treatment_plan && (
        <div style={styles.infoCard}>
          <div style={styles.infoTitle}>Treatment Plan</div>
          <div style={styles.infoText}>Phase: {dashboard.treatment_plan.phase.replace(/_/g, " ")}</div>
          <div style={styles.infoText}>
            Sessions: {dashboard.treatment_plan.completed_sessions} / {dashboard.treatment_plan.target_sessions}
          </div>
          <div style={styles.infoText}>{dashboard.treatment_plan.guidance}</div>
        </div>
      )}

      <div style={styles.section}>
        <div style={styles.sectionTitle}>Schedule next session</div>
        <div style={styles.grid}>
          <select style={styles.input} value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="support">Support Buddy</option>
            <option value="cbt">CBT Coach</option>
            <option value="intake">Intake Assistant</option>
          </select>
          <input style={styles.input} type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          <input style={styles.input} type="time" value={time} onChange={(e) => setTime(e.target.value)} />
        </div>
        <button onClick={schedule} style={styles.primaryBtn}>Create calendar event</button>
      </div>

      <div style={styles.section}>
        <div style={styles.sectionTitle}>Past sessions</div>
        {(dashboard?.recent_sessions || []).map((item) => (
          <div key={item.id} style={styles.listItem}>
            <div>
              <div style={styles.itemTitle}>{item.title || `${item.mode} session`}</div>
              <div style={styles.itemSub}>{new Date(item.created_at).toLocaleString()}</div>
            </div>
            <div style={styles.itemMode}>{item.mode}</div>
          </div>
        ))}
      </div>

      <div style={styles.section}>
        <div style={styles.sectionTitle}>Upcoming sessions</div>
        {(dashboard?.upcoming_sessions || []).map((item) => (
          <a key={item.id} href={item.calendar_url} target="_blank" rel="noreferrer" style={styles.listItem}>
            <div>
              <div style={styles.itemTitle}>{item.title}</div>
              <div style={styles.itemSub}>{new Date(item.start_at).toLocaleString()}</div>
            </div>
            <div style={{ color: "#6B9E7A", fontSize: 12 }}>Open</div>
          </a>
        ))}
      </div>
    </PageCard>
  );
}

function HomeworkPage({ profile }) {
  const [dashboard, setDashboard] = React.useState(null);
  const [loading, setLoading] = React.useState(false);

  const refresh = React.useCallback(async () => {
    if (!profile?.id) return;
    setLoading(true);
    try {
      const data = await api.getDashboard(profile.id);
      setDashboard(data);
    } finally {
      setLoading(false);
    }
  }, [profile?.id]);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  const update = async (item, status) => {
    await api.updateHomework(item.id, { status, reflection: item.reflection || null });
    refresh();
  };

  return (
    <PageCard
      title="Homework"
      subtitle="Track assignments between sessions and close the loop at the next CBT visit."
    >
      <button onClick={refresh} style={styles.refreshBtn}>
        {loading ? "Refreshing..." : "Refresh"}
      </button>
      {(dashboard?.all_homework || []).map((item) => (
        <div key={item.id} style={styles.homeworkCard}>
          <div style={styles.itemTitle}>{item.title}</div>
          <div style={styles.itemSub}>{item.instructions}</div>
          <div style={styles.homeworkMeta}>Status: {item.status}</div>
          <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
            <button onClick={() => update(item, "in_progress")} style={styles.secondaryBtn}>In Progress</button>
            <button onClick={() => update(item, "completed")} style={styles.primaryBtn}>Mark Complete</button>
          </div>
        </div>
      ))}
      {dashboard?.pending_homework?.length === 0 && (dashboard?.all_homework || []).length === 0 && (
        <div style={styles.emptyState}>No homework yet. CBT homework begins after the first intake-style session.</div>
      )}
      {dashboard?.treatment_plan?.should_plan_ending && (
        <div style={styles.infoCard}>
          <div style={styles.infoTitle}>Treatment wrap-up signal</div>
          <div style={styles.infoText}>
            Your care plan is entering a consolidation or termination review phase. The next sessions should focus on reviewing gains, relapse prevention, and how to maintain progress.
          </div>
        </div>
      )}
      {profile?.id && <CarePlanPanel profileId={profile.id} latestHomework={dashboard?.pending_homework?.[0]} previousSummary={dashboard?.recent_sessions?.[1]?.summary} />}
    </PageCard>
  );
}

const styles = {
  root: {
    display: "flex",
    minHeight: "100vh",
    background: "var(--bg-deep)",
  },
  sidebar: {
    width: 240,
    borderRight: "1px solid var(--border-subtle)",
    background: "var(--bg-surface)",
    padding: 20,
  },
  brand: {
    display: "flex",
    gap: 10,
    alignItems: "center",
    marginBottom: 24,
  },
  brandAvatar: {
    width: 40,
    height: 40,
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "linear-gradient(135deg, #2A3D2E, #1E3028)",
    border: "1px solid rgba(107,158,122,0.3)",
  },
  brandName: {
    fontFamily: "var(--font-display)",
    fontSize: 18,
  },
  brandMeta: {
    fontSize: 12,
    color: "#6B9E7A",
  },
  nav: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  navBtn: {
    width: "100%",
    textAlign: "left",
    border: "none",
    borderRadius: 10,
    padding: "10px 12px",
    fontSize: 13,
  },
  main: {
    flex: 1,
    minWidth: 0,
  },
  pageWrap: {
    padding: 28,
  },
  pageHeader: {
    marginBottom: 18,
  },
  pageTitle: {
    fontFamily: "var(--font-display)",
    fontSize: 28,
    color: "var(--text-primary)",
  },
  pageSubtitle: {
    fontSize: 13,
    color: "var(--text-secondary)",
    marginTop: 4,
    lineHeight: 1.6,
  },
  pageBody: {
    maxWidth: 860,
  },
  section: {
    marginTop: 18,
  },
  sectionTitle: {
    fontFamily: "var(--font-display)",
    fontSize: 15,
    marginBottom: 10,
    color: "var(--text-primary)",
  },
  infoCard: {
    padding: 14,
    borderRadius: 12,
    background: "rgba(123,127,212,0.1)",
    border: "1px solid rgba(123,127,212,0.18)",
    marginBottom: 16,
  },
  infoTitle: {
    fontSize: 13,
    color: "#C8CAF7",
    marginBottom: 6,
  },
  infoText: {
    fontSize: 12,
    color: "var(--text-secondary)",
    lineHeight: 1.6,
  },
  refreshBtn: {
    border: "1px solid var(--border-mid)",
    background: "rgba(255,255,255,0.04)",
    color: "var(--text-secondary)",
    borderRadius: 10,
    padding: "9px 12px",
    fontSize: 12,
    marginBottom: 12,
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
    gap: 8,
  },
  input: {
    width: "100%",
    padding: "10px 12px",
    borderRadius: 10,
    border: "1px solid var(--border-subtle)",
    background: "rgba(255,255,255,0.03)",
    color: "var(--text-primary)",
    fontSize: 13,
  },
  listItem: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
    padding: "12px 14px",
    borderRadius: 12,
    border: "1px solid var(--border-subtle)",
    background: "rgba(255,255,255,0.02)",
    marginBottom: 8,
    color: "inherit",
    textDecoration: "none",
  },
  itemTitle: {
    fontSize: 13,
    color: "var(--text-primary)",
  },
  itemSub: {
    fontSize: 12,
    color: "var(--text-secondary)",
    marginTop: 4,
    lineHeight: 1.5,
  },
  itemMode: {
    fontSize: 12,
    color: "#6B9E7A",
    textTransform: "capitalize",
  },
  homeworkCard: {
    padding: 14,
    borderRadius: 12,
    border: "1px solid var(--border-subtle)",
    background: "rgba(255,255,255,0.02)",
    marginBottom: 10,
  },
  homeworkMeta: {
    fontSize: 11,
    color: "#C8944A",
    marginTop: 8,
  },
  primaryBtn: {
    border: "none",
    background: "linear-gradient(135deg, #4E8A5E, #3A7050)",
    color: "#fff",
    borderRadius: 10,
    padding: "10px 12px",
    fontSize: 12,
  },
  secondaryBtn: {
    border: "1px solid var(--border-mid)",
    background: "rgba(255,255,255,0.04)",
    color: "var(--text-secondary)",
    borderRadius: 10,
    padding: "10px 12px",
    fontSize: 12,
  },
  emptyState: {
    padding: 16,
    borderRadius: 12,
    border: "1px dashed var(--border-mid)",
    color: "var(--text-secondary)",
    fontSize: 12,
    lineHeight: 1.6,
  },
};
