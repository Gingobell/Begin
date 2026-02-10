"use client";

import { useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { useTranslation } from "../i18n";

const T = {
  cream: "#FDFBF8",
  coral: { p: "#FF6B4A", s: "#FF8A6A", soft: "#FFB89A", airy: "#FFF5F0" },
  purple: { soft: "#D4C5FF" },
  text: { primary: "#1E1E1E", secondary: "#4B4B4B", tertiary: "#6F6F6F", quaternary: "#999999" },
};

export function LoginPage() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [birthday, setBirthday] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { t } = useTranslation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, password, fullName || undefined, birthday || undefined);
      }
    } catch (err: any) {
      setError(err.message || t("auth.somethingWentWrong"));
    } finally {
      setLoading(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    width: "100%", padding: "12px 16px", borderRadius: 14, border: "1px solid rgba(0,0,0,0.06)",
    background: "rgba(255,255,255,0.5)", fontSize: 14, fontFamily: "inherit",
    color: T.text.primary, outline: "none", transition: "border-color 0.2s, box-shadow 0.2s",
  };

  return (
    <div style={{
      position: "fixed", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
      background: T.cream, overflow: "hidden",
    }}>
      {/* Background orbs */}
      <div style={{ position: "absolute", inset: 0, pointerEvents: "none", zIndex: 0 }}>
        <div style={{
          position: "absolute", width: 400, height: 400, borderRadius: "50%",
          background: T.coral.soft, opacity: 0.35, filter: "blur(100px)",
          top: "-10%", left: "-5%", animation: "orbDrift 28s ease-in-out infinite",
        }} />
        <div style={{
          position: "absolute", width: 350, height: 350, borderRadius: "50%",
          background: T.purple.soft, opacity: 0.3, filter: "blur(90px)",
          bottom: "-8%", right: "-3%", animation: "orbDrift 24s ease-in-out -6s infinite",
        }} />
        <div style={{
          position: "absolute", width: 250, height: 250, borderRadius: "50%",
          background: T.coral.airy, opacity: 0.5, filter: "blur(80px)",
          top: "20%", right: "15%", animation: "orbFloat 20s ease-in-out -3s infinite",
        }} />
      </div>

      {/* Glass card */}
      <div style={{
        position: "relative", zIndex: 1, width: "100%", maxWidth: 400, margin: "0 24px",
        background: "rgba(255,255,255,0.72)", border: "1px solid rgba(255,255,255,0.6)",
        borderRadius: 28, padding: "40px 32px", backdropFilter: "blur(40px)",
        WebkitBackdropFilter: "blur(40px)",
        boxShadow: "0 8px 32px rgba(0,0,0,0.04), inset 0 1px 0 rgba(255,255,255,0.6)",
      }}>
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
          <img src="/logo.png" alt="Begin" style={{ width: 38, height: 38, borderRadius: 12 }} />
          <span style={{ fontFamily: "'Fraunces',serif", fontSize: 22, fontWeight: 500, color: T.text.primary }}>
            Begin
          </span>
        </div>
        <p style={{ fontSize: 13, color: T.text.quaternary, marginBottom: 28 }}>
          {t("auth.tagline")}
        </p>

        {/* Mode tabs */}
        <div style={{
          display: "flex", gap: 2, background: "rgba(0,0,0,0.03)", borderRadius: 14, padding: 3, marginBottom: 24,
        }}>
          {(["login", "register"] as const).map(m => {
            const active = mode === m;
            return (
              <button key={m} onClick={() => { setMode(m); setError(""); }} style={{
                flex: 1, padding: "9px 0", borderRadius: 11, border: "none", cursor: "pointer",
                fontSize: 13, fontWeight: active ? 600 : 500, fontFamily: "inherit",
                color: active ? T.text.primary : T.text.tertiary,
                background: active ? "rgba(255,255,255,0.92)" : "transparent",
                boxShadow: active ? "0 1px 8px rgba(0,0,0,0.04)" : "none",
                transition: "all 0.3s cubic-bezier(0.2,0.8,0.2,1)",
              }}>
                {m === "login" ? t("auth.signIn") : t("auth.signUp")}
              </button>
            );
          })}
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {mode === "register" && (
            <input
              type="text" placeholder={t("auth.namePlaceholder")} value={fullName}
              onChange={e => setFullName(e.target.value)} style={inputStyle}
            />
          )}
          <input
            type="email" placeholder={t("auth.emailPlaceholder")} value={email}
            onChange={e => setEmail(e.target.value)} required style={inputStyle}
          />
          <input
            type="password" placeholder={t("auth.passwordPlaceholder")} value={password}
            onChange={e => setPassword(e.target.value)} required minLength={6} style={inputStyle}
          />
          {mode === "register" && (
            <input
              type="date" placeholder={t("auth.birthday")} value={birthday}
              onChange={e => setBirthday(e.target.value)} style={inputStyle}
            />
          )}

          {error && (
            <p style={{ fontSize: 12, color: "#ef4444", padding: "0 4px" }}>{error}</p>
          )}

          <button type="submit" disabled={loading} style={{
            width: "100%", padding: "13px 0", borderRadius: 16, border: "none", cursor: "pointer",
            fontSize: 14, fontWeight: 600, fontFamily: "inherit", color: "#fff", marginTop: 4,
            background: `linear-gradient(135deg,${T.coral.s},${T.coral.p})`,
            boxShadow: `0 4px 16px ${T.coral.p}30`,
            opacity: loading ? 0.7 : 1, transition: "opacity 0.2s, transform 0.15s",
          }}>
            {loading ? "..." : mode === "login" ? t("auth.signIn") : t("auth.createAccount")}
          </button>
        </form>
      </div>
    </div>
  );
}
