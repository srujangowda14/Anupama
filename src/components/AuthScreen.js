import React, { useState } from "react";
import { supabase } from "../utils/supabase";
import { useIsMobile } from "../hooks/useIsMobile";

export default function AuthScreen() {
  const isMobile = useIsMobile();
  const [mode, setMode] = useState("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    setLoading(true);
    setError(null);
    try {
      const action = mode === "signup"
        ? supabase.auth.signUp({ email, password })
        : supabase.auth.signInWithPassword({ email, password });
      const { error: authError } = await action;
      if (authError) throw authError;
    } catch (err) {
      setError(err.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  const signInWithGoogle = async () => {
    const redirectTo = window.location.origin;
    const { error: authError } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo },
    });
    if (authError) setError(authError.message);
  };

  return (
    <div style={{ ...styles.root, alignItems: isMobile ? "flex-start" : "center", padding: isMobile ? 16 : 24 }}>
      <div style={{ ...styles.card, maxWidth: isMobile ? "100%" : 440, padding: isMobile ? 22 : 28, marginTop: isMobile ? 18 : 0 }}>
        <div style={styles.logo}>🌿</div>
        <h1 style={{ ...styles.title, fontSize: isMobile ? 30 : 34 }}>Anupama</h1>
        <p style={styles.subtitle}>A CBT-focused support companion with account-based continuity.</p>

        <div style={styles.toggle}>
          {["signin", "signup"].map((value) => (
            <button
              key={value}
              onClick={() => setMode(value)}
              style={{
                ...styles.toggleBtn,
                background: mode === value ? "rgba(107,158,122,0.18)" : "transparent",
                color: mode === value ? "#6B9E7A" : "var(--text-muted)",
              }}
            >
              {value === "signin" ? "Sign In" : "Create Account"}
            </button>
          ))}
        </div>

        <input style={styles.input} placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <input style={styles.input} type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} />

        <button onClick={submit} style={styles.primaryBtn} disabled={loading}>
          {loading ? "Please wait..." : mode === "signin" ? "Sign In" : "Create Account"}
        </button>

        <button onClick={signInWithGoogle} style={styles.googleBtn}>
          Continue with Google
        </button>

        {error && <p style={styles.error}>{error}</p>}
        <p style={styles.caption}>Passwords are handled securely by Supabase Auth and are never stored by the app itself.</p>
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
    padding: 24,
  },
  card: {
    width: "100%",
    maxWidth: 440,
    padding: 28,
    borderRadius: 22,
    border: "1px solid var(--border-subtle)",
    background: "linear-gradient(180deg, rgba(30,32,25,0.95), rgba(18,20,17,0.95))",
    boxShadow: "var(--shadow-soft)",
  },
  logo: { fontSize: 28, marginBottom: 12 },
  title: { fontFamily: "var(--font-display)", fontSize: 34, marginBottom: 8 },
  subtitle: { fontSize: 14, color: "var(--text-secondary)", marginBottom: 18, lineHeight: 1.6 },
  toggle: { display: "flex", gap: 6, marginBottom: 16, background: "rgba(255,255,255,0.03)", borderRadius: 10, padding: 4 },
  toggleBtn: { flex: 1, border: "none", borderRadius: 8, padding: "10px 0", fontSize: 13 },
  input: {
    width: "100%",
    marginBottom: 10,
    padding: "13px 14px",
    borderRadius: 12,
    border: "1px solid var(--border-subtle)",
    background: "rgba(255,255,255,0.03)",
    color: "var(--text-primary)",
    fontSize: 14,
  },
  primaryBtn: {
    width: "100%",
    padding: "12px 14px",
    borderRadius: 12,
    border: "none",
    background: "linear-gradient(135deg, #4E8A5E, #3A7050)",
    color: "#fff",
    fontSize: 14,
    marginTop: 4,
  },
  googleBtn: {
    width: "100%",
    padding: "12px 14px",
    borderRadius: 12,
    border: "1px solid var(--border-subtle)",
    background: "rgba(255,255,255,0.03)",
    color: "var(--text-primary)",
    fontSize: 14,
    marginTop: 10,
  },
  error: { fontSize: 12, color: "#C87A7A", marginTop: 10 },
  caption: { fontSize: 11, color: "var(--text-muted)", marginTop: 12, lineHeight: 1.5 },
};
