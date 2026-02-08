"use client";

import { useState, useCallback } from "react";
import { CopilotKit } from "@copilotkit/react-core";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { LoginPage } from "./components/LoginPage";
import { FortuneTab } from "./components/FortuneTab";
import { DiaryTab } from "./components/DiaryTab";
import { ChatOverlay } from "./components/ChatOverlay";
import { CelestialPanel } from "./components/CelestialPanel";

// ── Theme config (mirrors web2.html T object) ────────────────────
export const T = {
  cream: "#FDFBF8",
  coral: { p: "#FF6B4A", s: "#FF8A6A", soft: "#FFB89A", airy: "#FFF5F0", cream: "#FFFBFA" },
  blue: { p: "#5C8BFF", s: "#7AA3FF", soft: "#A8C4FF", airy: "#E6F0FF" },
  purple: { p: "#8F6BF7", s: "#9B7DF9", soft: "#D4C5FF", airy: "#F0ECFF" },
  honey: { p: "#FFD75A", s: "#FFE073", soft: "#FFEEB0", airy: "#FFFBF0" },
  career: { p: "#7DD3FC", s: "#9BDFFD", soft: "#C0EBFE", airy: "#EAF8FF", cream: "#F5FAFF" },
  love: { p: "#FFB8D0", s: "#FFCBDD", soft: "#FFE0EB", airy: "#FFF6F9", cream: "#FFF8FA" },
  wealth: { p: "#F2D94D", s: "#F7E36B", soft: "#FAEEB0", airy: "#FDF9E6", cream: "#FFFCF0" },
  study: { p: "#7DDFBD", s: "#9BE8CF", soft: "#C0F0E0", airy: "#E8FBF5", cream: "#F5FCF8" },
  social: { p: "#B8A4FF", s: "#CBBAFE", soft: "#E0D4FF", airy: "#F4F1FF", cream: "#F9F7FF" },
  text: { primary: "#1E1E1E", secondary: "#4B4B4B", tertiary: "#6F6F6F", quaternary: "#999999" },
};

export type ThemeColor = { p: string; s: string; soft: string; airy: string; cream?: string };

export const navColors: Record<string, { light: string; dark: string; text: string }> = {
  overall: { light: "#FF8A6A", dark: "#FF6B4A", text: "#fff" },
  career:  { light: "#9BDFFD", dark: "#7DD3FC", text: "#1A5A7A" },
  love:    { light: "#FFCBDD", dark: "#FFB8D0", text: "#8A4A5A" },
  wealth:  { light: "#F7E36B", dark: "#F2D94D", text: "#5A4A10" },
  study:   { light: "#9BE8CF", dark: "#7DDFBD", text: "#2A5A4A" },
  social:  { light: "#CBBAFE", dark: "#B8A4FF", text: "#4A3A6A" },
};

export const categories = [
  { key: "overall", label: "Overall", icon: "☀️", theme: T.coral, desc: "Your day at a glance" },
  { key: "career", label: "Career", icon: "💼", theme: T.career, desc: "Work & ambition" },
  { key: "love", label: "Love", icon: "💕", theme: T.love, desc: "Heart & connection" },
  { key: "wealth", label: "Wealth", icon: "💰", theme: T.wealth, desc: "Money & abundance" },
  { key: "study", label: "Study", icon: "📚", theme: T.study, desc: "Growth & learning" },
  { key: "social", label: "Social", icon: "👥", theme: T.social, desc: "Friends & community" },
];

export const suggestedQuestions: Record<string, string[]> = {
  overall: ["Is today good for big decisions?", "What should I focus on?", "Should I start something new?", "How to make the most of today?", "What's my energy peak?"],
  career: ["Should I bring up the promotion?", "Best time for presentations?", "When to schedule the meeting?", "Take on more responsibility?", "How to impress my boss?"],
  love: ["Should I reach out first?", "Good day for the big talk?", "How to deepen the connection?", "Give them space today?", "Is romance in the air?"],
  wealth: ["Good day for investments?", "Should I make the purchase?", "When does financial luck peak?", "Budget meeting approach?", "Side hustle energy today?"],
  study: ["Best study time today?", "Start the new course now?", "How to improve focus?", "Good day for creative work?", "Exam prep strategy?"],
  social: ["Attend the event tonight?", "Good day for networking?", "Handle this conflict how?", "Who to reconnect with?", "Party or stay in?"],
};

export const candyColors: Record<string, { light: string; dark: string; shadow: string; text: string }> = {
  overall: { light: "#FF8A6A", dark: "#FF6B4A", shadow: "#FF6B4A", text: "#fff" },
  career:  { light: "#9BDFFD", dark: "#7DD3FC", shadow: "#7DD3FC", text: "#1A5A7A" },
  love:    { light: "#FFCBDD", dark: "#FFB8D0", shadow: "#E8A0B8", text: "#5A3A4A" },
  wealth:  { light: "#F7E36B", dark: "#F2D94D", shadow: "#E8C24A", text: "#5A4A20" },
  study:   { light: "#9BE8CF", dark: "#7DDFBD", shadow: "#6AC8A8", text: "#2A4A3A" },
  social:  { light: "#CBBAFE", dark: "#B8A4FF", shadow: "#A090E8", text: "#3A3050" },
  diary:   { light: "#7AA3FF", dark: "#5C8BFF", shadow: "#5C8BFF", text: "#fff" },
  purple:  { light: "#8F6BF7", dark: "#7A55E8", shadow: "#7A55E8", text: "#fff" },
  honey:   { light: "#FFE073", dark: "#FFD75A", shadow: "#E8C24A", text: "#5A4A20" },
};

type Tab = "fortune" | "diary";

// ── TopNav ───────────────────────────────────────────────────────
function TopNav({ tab, onTab, onProfile, theme }: {
  tab: Tab;
  onTab: (t: Tab) => void;
  onProfile: () => void;
  theme: ThemeColor;
}) {
  return (
    <div style={{
      height: 56, flexShrink: 0, display: "flex", alignItems: "center",
      justifyContent: "space-between", padding: "0 28px",
      background: "rgba(253,251,248,0.75)", backdropFilter: "blur(24px)",
      WebkitBackdropFilter: "blur(24px)", borderBottom: "1px solid rgba(0,0,0,0.025)",
      zIndex: 40, position: "relative",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <img src="/logo.png" alt="Begin" style={{ width: 34, height: 34, borderRadius: 11 }} />
        <span style={{ fontFamily: "'Fraunces',serif", fontSize: 18, fontWeight: 500, color: T.text.primary }}>Begin</span>
      </div>
      <div style={{ display: "flex", gap: 2, background: "rgba(0,0,0,0.03)", borderRadius: 14, padding: 3 }}>
        {([{ key: "fortune" as Tab, label: "Fortune", icon: "✨" }, { key: "diary" as Tab, label: "Diary", icon: "📝" }]).map(t => {
          const a = t.key === tab;
          return (
            <button key={t.key} onClick={() => onTab(t.key)} style={{
              padding: "8px 24px", borderRadius: 11, border: "none", cursor: "pointer",
              fontSize: 13, fontWeight: a ? 600 : 500, fontFamily: "inherit",
              display: "flex", alignItems: "center", gap: 6,
              transition: "all 0.3s cubic-bezier(0.2,0.8,0.2,1)",
              color: a ? T.text.primary : T.text.tertiary,
              background: a ? "rgba(255,255,255,0.92)" : "transparent",
              boxShadow: a ? "0 1px 8px rgba(0,0,0,0.04)" : "none",
            }}>
              <span style={{ fontSize: 13 }}>{t.icon}</span> {t.label}
            </button>
          );
        })}
      </div>
      <button onClick={onProfile} style={{
        width: 34, height: 34, borderRadius: 12, border: "none", cursor: "pointer",
        background: `linear-gradient(135deg,${theme.airy},${theme.soft}50)`,
        fontSize: 15, display: "flex", alignItems: "center", justifyContent: "center",
        boxShadow: "0 1px 6px rgba(0,0,0,0.03)",
      }}>👤</button>
    </div>
  );
}

// ── ProfileModal ─────────────────────────────────────────────────
function ProfileModal({ onClose, user, onLogout, diaryCount }: {
  onClose: () => void;
  user: { email: string; full_name?: string };
  onLogout: () => void;
  diaryCount?: number;
}) {
  const stats: [string, string | number, string][] = [
    ["📝", diaryCount ?? 0, "Entries"],
    ["🔥", "15", "Streak"],
    ["🎯", "82%", "Match"],
  ];
  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 300, background: "rgba(0,0,0,0.12)",
      backdropFilter: "blur(16px)", display: "flex", alignItems: "center",
      justifyContent: "center", padding: 24,
    }} onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={{
        background: "rgba(255,255,255,0.88)", border: "1px solid rgba(255,255,255,0.5)",
        borderRadius: 28, maxWidth: 380, width: "100%", padding: 32,
        boxShadow: "0 6px 12px rgba(0,0,0,0.05)",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 24 }}>
          <h2 style={{ fontFamily: "'Fraunces',serif", fontSize: 20, fontWeight: 500, margin: 0 }}>Profile</h2>
          <button onClick={onClose} style={{
            background: "rgba(0,0,0,0.04)", border: "none", width: 30, height: 30,
            borderRadius: 10, fontSize: 14, cursor: "pointer", color: T.text.tertiary,
          }}>✕</button>
        </div>
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <div style={{
            width: 60, height: 60, borderRadius: "50%", margin: "0 auto 12px",
            background: `linear-gradient(135deg,${T.coral.soft},${T.purple.soft})`,
            display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24,
          }}>👤</div>
          <div style={{ fontFamily: "'Fraunces',serif", fontSize: 18, fontWeight: 500 }}>
            {user.full_name || "User"}
          </div>
          <div style={{ fontSize: 12, color: T.text.quaternary, marginTop: 3 }}>{user.email}</div>
        </div>
        {/* BaZi card */}
        <div style={{
          background: T.coral.airy, borderRadius: 16, padding: 14, marginBottom: 14,
          border: `1px solid ${T.coral.soft}25`,
        }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: T.coral.p, marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            ☯️ BaZi
          </div>
          <div style={{ fontSize: 12.5, color: T.text.secondary, lineHeight: 1.55 }}>
            Day Master: 丙 Fire · Born: 1995-06-15
          </div>
        </div>
        {/* Stats grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, marginBottom: 16 }}>
          {stats.map(([ic, v, l]) => (
            <div key={l} style={{
              background: "rgba(255,255,255,0.45)", borderRadius: 14, padding: "12px 6px",
              textAlign: "center", border: "1px solid rgba(255,255,255,0.5)",
            }}>
              <div style={{ fontSize: 17, marginBottom: 2 }}>{ic}</div>
              <div style={{ fontWeight: 700, fontSize: 16, fontFamily: "'Fraunces',serif" }}>{v}</div>
              <div style={{ fontSize: 10, color: T.text.quaternary }}>{l}</div>
            </div>
          ))}
        </div>
        <button onClick={() => { onLogout(); onClose(); }} style={{
          width: "100%", padding: "12px 0", borderRadius: 16, border: "none",
          cursor: "pointer", fontSize: 14, fontWeight: 500, fontFamily: "inherit",
          background: "rgba(0,0,0,0.04)", color: T.text.tertiary,
          transition: "all 0.2s",
        }}>Sign Out</button>
      </div>
    </div>
  );
}

// ── OrbBackground ────────────────────────────────────────────────
function OrbBackground({ theme, tab }: { theme: ThemeColor; tab: Tab }) {
  const orbTheme = tab === "diary" ? T.purple : theme;
  return (
    <div style={{ position: "fixed", inset: 0, pointerEvents: "none", zIndex: 0, overflow: "hidden", background: T.cream }}>
      <div style={{
        position: "absolute", width: 480, height: 480, borderRadius: "50%",
        background: orbTheme.soft, opacity: 0.4, filter: "blur(100px)",
        top: "-12%", left: "-8%", animation: "orbDrift 28s ease-in-out infinite",
        transition: "background 1.2s ease, opacity 1.2s ease",
      }} />
      <div style={{
        position: "absolute", width: 340, height: 340, borderRadius: "50%",
        background: orbTheme.airy, opacity: 0.55, filter: "blur(80px)",
        top: "2%", left: "10%", animation: "orbDrift 24s ease-in-out -4s infinite",
        transition: "background 1.2s ease, opacity 1.2s ease",
      }} />
      <div style={{
        position: "absolute", width: 460, height: 460, borderRadius: "50%",
        background: orbTheme.s, opacity: 0.5, filter: "blur(90px)",
        bottom: "-10%", right: "-6%", animation: "orbDrift 30s ease-in-out -10s infinite",
        transition: "background 1.2s ease, opacity 1.2s ease",
      }} />
      <div style={{
        position: "absolute", width: 380, height: 380, borderRadius: "50%",
        background: orbTheme.airy, opacity: 0.65, filter: "blur(100px)",
        bottom: "5%", right: "8%", animation: "orbDrift 22s ease-in-out -7s infinite",
        transition: "background 1.2s ease, opacity 1.2s ease",
      }} />
      {tab === "diary" && (
        <div style={{
          position: "absolute", width: 200, height: 200, borderRadius: "50%",
          background: "rgba(143,107,247,0.18)", filter: "blur(80px)",
          bottom: "20%", right: "15%", animation: "orbFloat 19s ease-in-out 3s infinite",
          transition: "opacity 1.2s ease",
        }} />
      )}
    </div>
  );
}

// ── BreathBlobs (right-side Quick Ask panel) ─────────────────────
function BreathBlobs({ theme, onBubbleClick, activeCat }: { theme: ThemeColor; onBubbleClick: (q: string) => void; activeCat: string }) {
  const [customQ, setCustomQ] = useState("");
  const questions = suggestedQuestions[activeCat] || suggestedQuestions.overall;
  const radii = ["26px 18px 24px 16px","18px 26px 16px 24px","24px 16px 26px 18px","16px 24px 18px 26px","22px 18px 26px 16px"];

  const handleCustomSend = () => {
    const q = customQ.trim();
    if (!q) return;
    onBubbleClick(q);
    setCustomQ("");
  };

  return (
    <div style={{ width: 320, height: "100%", flexShrink: 0, position: "relative", display: "flex", flexDirection: "column", alignItems: "stretch", justifyContent: "flex-start", padding: "144px 16px 18px", overflow: "hidden" }}>
      {/* Background glow orbs */}
      <div style={{ position: "absolute", top: "8%", left: "10%", width: 160, height: 160, borderRadius: "50%", background: `${theme.soft}25`, filter: "blur(50px)", animation: "blobGlow 8s ease-in-out infinite", pointerEvents: "none" }} />
      <div style={{ position: "absolute", bottom: "12%", right: "5%", width: 130, height: 130, borderRadius: "50%", background: `${theme.soft}20`, filter: "blur(45px)", animation: "blobGlow 10s ease-in-out 3s infinite", pointerEvents: "none" }} />

      {/* Quick Ask title */}
      <div style={{ paddingBottom: 10, zIndex: 2, flexShrink: 0 }}>
        <div style={{ fontSize: 18, fontWeight: 600, fontFamily: "'Fraunces',serif", color: T.text.primary, marginBottom: 12 }}>
          Quick Ask
        </div>
        <div style={{ fontSize: 13, color: T.text.quaternary, lineHeight: 1.45 }}>
          Ask about today
        </div>
      </div>

      {/* Custom input */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16, zIndex: 2, flexShrink: 0 }}>
        <input
          value={customQ}
          onChange={e => setCustomQ(e.target.value)}
          onKeyDown={e => e.key === "Enter" && handleCustomSend()}
          placeholder="What's on your mind?"
          style={{
            flex: 1, padding: "10px 14px", borderRadius: 16,
            border: `1px solid ${theme.soft}40`,
            background: "rgba(255,255,255,0.65)",
            backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)",
            fontSize: 12.5, color: T.text.secondary, outline: "none",
            fontFamily: "inherit",
            boxShadow: "inset 0 1px 0 rgba(255,255,255,0.7)",
            transition: "border-color 0.25s, box-shadow 0.25s",
          }}
          onFocus={e => { e.currentTarget.style.borderColor = `${theme.p}50`; e.currentTarget.style.boxShadow = `inset 0 1px 0 rgba(255,255,255,0.7), 0 0 0 3px ${theme.p}10`; }}
          onBlur={e => { e.currentTarget.style.borderColor = `${theme.soft}40`; e.currentTarget.style.boxShadow = "inset 0 1px 0 rgba(255,255,255,0.7)"; }}
        />
        <button onClick={handleCustomSend} style={{
          width: 36, height: 36, borderRadius: 14, border: "none", cursor: "pointer", flexShrink: 0,
          background: customQ.trim() ? `linear-gradient(135deg, ${theme.soft}80, ${theme.p}40)` : "rgba(255,255,255,0.5)",
          color: customQ.trim() ? theme.p : T.text.quaternary,
          fontSize: 14, fontWeight: 600,
          display: "flex", alignItems: "center", justifyContent: "center",
          transition: "all 0.25s ease",
          boxShadow: customQ.trim() ? `0 2px 8px ${theme.p}15` : "none",
        }}>&#8593;</button>
      </div>

      {/* Divider */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 18, zIndex: 2, flexShrink: 0 }}>
        <div style={{ flex: 1, height: 1, background: `${theme.soft}30` }} />
        <span style={{ fontSize: 10, fontWeight: 600, color: T.text.quaternary, letterSpacing: "0.08em", textTransform: "uppercase" }}>Or tap a thought</span>
        <div style={{ flex: 1, height: 1, background: `${theme.soft}30` }} />
      </div>

      {/* Breathing bubbles */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10, zIndex: 2, flexShrink: 0 }}>
        {questions.slice(0, 5).map((q, i) => (
          <div key={i} onClick={() => onBubbleClick(q)} style={{
            padding: "11px 16px",
            borderRadius: radii[i],
            background: "linear-gradient(145deg, rgba(255,255,255,0.92), rgba(255,255,255,0.85))",
            backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)",
            boxShadow: `0 1px 0 0 rgba(255,255,255,0.8) inset, 0 -1px 1px 0 ${theme.p}12 inset, 0 4px 14px ${theme.p}18, 0 1px 3px rgba(0,0,0,0.05)`,
            border: `1px solid ${theme.soft}28`,
            cursor: "pointer",
            animation: `blobBreathe ${3 + i * 0.4}s ease-in-out ${i * 0.3}s infinite`,
            transition: "all 0.3s cubic-bezier(0.2,0.8,0.2,1)",
            width: "fit-content", maxWidth: 240,
            alignSelf: i % 2 === 0 ? "flex-start" : "flex-end",
            zIndex: 3,
            fontSize: 12.5, lineHeight: 1.55, color: T.text.secondary, fontFamily: "inherit",
          }}
            onMouseEnter={e => {
              e.currentTarget.style.transform = "scale(1.05) translateY(-2px)";
              e.currentTarget.style.boxShadow = `0 1px 0 0 rgba(255,255,255,0.9) inset, 0 -1px 2px 0 ${theme.p}20 inset, 0 8px 28px ${theme.p}28, 0 2px 6px rgba(0,0,0,0.08)`;
              e.currentTarget.style.animationPlayState = "paused";
            }}
            onMouseLeave={e => {
              e.currentTarget.style.transform = "";
              e.currentTarget.style.boxShadow = `0 1px 0 0 rgba(255,255,255,0.8) inset, 0 -1px 1px 0 ${theme.p}12 inset, 0 4px 14px ${theme.p}18, 0 1px 3px rgba(0,0,0,0.05)`;
              e.currentTarget.style.animationPlayState = "running";
            }}
          >
            <span style={{ color: theme.p, marginRight: 7, fontWeight: 600 }}>&rarr;</span>{q}
          </div>
        ))}
      </div>
      <style>{`
        @keyframes blobBreathe{0%,100%{transform:scale(1) translateY(0)}50%{transform:scale(1.018) translateY(-3px)}}
        @keyframes blobGlow{0%,100%{opacity:1;transform:scale(1)}50%{opacity:0.5;transform:scale(1.12)}}
      `}</style>
    </div>
  );
}

// ── AppShell ─────────────────────────────────────────────────────
function AppShell() {
  const { user, loading, logout } = useAuth();
  const [tab, setTab] = useState<Tab>("fortune");
  const [profileOpen, setProfileOpen] = useState(false);
  const [activeCatTheme, setActiveCatTheme] = useState<ThemeColor>(T.coral);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatQuestion, setChatQuestion] = useState<string | null>(null);
  const [activeCat, setActiveCat] = useState("overall");
  const [celestialOpen, setCelestialOpen] = useState(false);
  const [diaryChatOpen, setDiaryChatOpen] = useState(false);
  const [fortuneRevealed, setFortuneRevealed] = useState(false);
  const [diaryCount, setDiaryCount] = useState(0);

  const orbTheme = tab === "diary" ? T.purple : activeCatTheme;
  const today = new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });

  const handleCloseChat = useCallback(() => {
    setChatOpen(false);
    setChatQuestion(null);
  }, []);

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", background: T.cream }}>
        <img src="/logo.png" alt="Begin" style={{ width: 34, height: 34, borderRadius: 11 }} />
      </div>
    );
  }

  if (!user) return <LoginPage />;

  const candyGlassBtn = (accent: ThemeColor, active = false) => ({
    padding: "12px 22px", borderRadius: 16, cursor: "pointer" as const,
    border: `1px solid ${accent.soft}78`,
    background: active
      ? `linear-gradient(135deg, rgba(255,255,255,0.94), ${accent.airy})`
      : "linear-gradient(135deg, rgba(255,255,255,0.90), rgba(255,255,255,0.76))",
    color: accent.p, fontSize: 14, fontWeight: 700, fontFamily: "inherit",
    display: "flex" as const, alignItems: "center" as const, gap: 8,
    backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)",
    boxShadow: active
      ? `0 12px 28px ${accent.p}2E, inset 0 1px 0 rgba(255,255,255,0.95), inset 0 -1px 0 ${accent.soft}44`
      : `0 8px 20px rgba(0,0,0,0.05), 0 0 0 1px ${accent.soft}24, inset 0 1px 0 rgba(255,255,255,0.92), inset 0 -1px 0 rgba(255,255,255,0.64)`,
    transition: "all 0.35s cubic-bezier(0.2,0.8,0.2,1)",
  });

  return (
    <CopilotKit runtimeUrl="/api/copilotkit" agent="fortune_diary" properties={{ user_id: user.id }}>
      <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
        <OrbBackground theme={activeCatTheme} tab={tab} />
        <TopNav tab={tab} onTab={setTab} onProfile={() => setProfileOpen(true)} theme={activeCatTheme} />

        <div style={{ flex: 1, display: "flex", overflow: "hidden", position: "relative", zIndex: 1 }}>
          {tab === "fortune" && (
            <FortuneTab
              onThemeChange={setActiveCatTheme}
              onRevealChange={setFortuneRevealed}
              onActiveCatChange={setActiveCat}
              headerSlot={
                <div style={{ marginBottom: 22, display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
                  <div>
                    <div style={{ fontSize: 12.5, color: T.text.quaternary, fontWeight: 500, marginBottom: 4 }}>{today}</div>
                    <h1 style={{ fontFamily: "'Fraunces',serif", fontSize: 26, fontWeight: 500, margin: 0 }}>
                      Good morning ☀️
                    </h1>
                  </div>
                  {fortuneRevealed && (
                    <button
                      onClick={() => { setCelestialOpen(!celestialOpen); if (chatOpen) { setChatOpen(false); setChatQuestion(null); } }}
                      style={candyGlassBtn(activeCatTheme, celestialOpen)}
                    >
                      <span style={{ fontSize: 16, filter: `drop-shadow(0 2px 4px ${activeCatTheme.p}30)` }}>✨</span> Today&apos;s Celestial
                    </button>
                  )}
                </div>
              }
            />
          )}

          {tab === "diary" && (
            <div style={{ flex: 1, overflow: "auto" }}>
              <div style={{ maxWidth: 720, margin: "0 auto", padding: "28px 36px 48px" }}>
                <div style={{ marginBottom: 22, display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
                  <div>
                    <div style={{ fontSize: 12.5, color: T.text.quaternary, fontWeight: 500, marginBottom: 4 }}>{today}</div>
                    <h1 style={{ fontFamily: "'Fraunces',serif", fontSize: 26, fontWeight: 500, margin: 0, lineHeight: 1.3 }}>
                      The more you write,<br />the smarter your fortune gets
                    </h1>
                  </div>
                  <button
                    onClick={() => setDiaryChatOpen(true)}
                    style={candyGlassBtn(orbTheme, diaryChatOpen)}
                  >
                    <span style={{ fontSize: 16, filter: `drop-shadow(0 2px 4px ${orbTheme.p}30)` }}>💬</span>
                    <span>Chat to Journal</span>
                  </button>
                </div>
                <div style={{ margin: "10px 0 24px" }}>
                  <div style={{ height: 1, borderRadius: 1, background: "linear-gradient(90deg, rgba(0,0,0,0), rgba(0,0,0,0.14) 18%, rgba(0,0,0,0.14) 82%, rgba(0,0,0,0))" }} />
                </div>
                <DiaryTab onCountChange={setDiaryCount} />
              </div>
            </div>
          )}

          {/* Right panels for fortune tab */}
          {tab === "fortune" && fortuneRevealed && (
            <>
              {/* BreathBlobs — visible when no panel is open */}
              {!chatOpen && !celestialOpen && (
                <BreathBlobs theme={activeCatTheme} activeCat={activeCat} onBubbleClick={(q: string) => {
                  setChatQuestion(q);
                  setChatOpen(true);
                }} />
              )}
              {/* Chat overlay panel */}
              <div style={{
                width: chatOpen ? 420 : 0, opacity: chatOpen ? 1 : 0,
                overflow: "hidden", flexShrink: 0,
                transition: "all 0.5s cubic-bezier(0.2,0.8,0.2,1)",
                background: chatOpen ? `linear-gradient(180deg,${activeCatTheme.airy}AA,rgba(253,251,248,0.9))` : "transparent",
                display: "flex", flexDirection: "column",
              }}>
                {chatOpen && (
                  <ChatOverlay open={chatOpen} onClose={handleCloseChat} theme={activeCatTheme} initialQuestion={chatQuestion} />
                )}
              </div>

              {/* Celestial panel */}
              <div style={{
                width: celestialOpen ? 400 : 0, opacity: celestialOpen ? 1 : 0,
                overflow: "hidden", flexShrink: 0,
                transition: "all 0.5s cubic-bezier(0.2,0.8,0.2,1)",
                borderLeft: celestialOpen ? "1px solid rgba(0,0,0,0.04)" : "none",
                background: celestialOpen ? `linear-gradient(180deg, ${activeCatTheme.airy}AA, rgba(253,251,248,0.92))` : "transparent",
                display: "flex", flexDirection: "column",
              }}>
                {celestialOpen && (
                  <CelestialPanel onClose={() => setCelestialOpen(false)} theme={activeCatTheme} fortune={null} />
                )}
              </div>
            </>
          )}

          {/* Diary chat panel */}
          {tab === "diary" && (
            <div style={{
              width: diaryChatOpen ? 420 : 0, opacity: diaryChatOpen ? 1 : 0,
              overflow: "hidden", flexShrink: 0,
              transition: "all 0.5s cubic-bezier(0.2,0.8,0.2,1)",
              borderLeft: diaryChatOpen ? "1px solid rgba(0,0,0,0.04)" : "none",
              background: diaryChatOpen ? `linear-gradient(180deg, ${orbTheme.airy}AA, rgba(253,251,248,0.9))` : "transparent",
              display: "flex", flexDirection: "column",
            }}>
              {diaryChatOpen && (
                <ChatOverlay open={diaryChatOpen} onClose={() => setDiaryChatOpen(false)} theme={orbTheme} />
              )}
            </div>
          )}
        </div>

        {profileOpen && (
          <ProfileModal onClose={() => setProfileOpen(false)} user={user} onLogout={logout} diaryCount={diaryCount} />
        )}
      </div>
    </CopilotKit>
  );
}

// ── Page ─────────────────────────────────────────────────────────
export default function Home() {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  );
}
