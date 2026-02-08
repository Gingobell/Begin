"use client";

import { useState, useEffect, useCallback } from "react";
import { getFortuneStatus, getDailyFortune } from "../lib/api";
import { T, ThemeColor, categories, navColors } from "../lib/theme";

// ── Types ────────────────────────────────────────────────────────
interface BatteryDomain {
  status?: string;
  suggestion?: string;
}

interface BatteryFortune {
  overall?: {
    daily_management?: string;
    today_actions?: string;
    power_drain?: string;
    surge_protection?: string;
    recharge?: string;
  };
  career?: BatteryDomain;
  wealth?: BatteryDomain;
  love?: BatteryDomain;
  social?: BatteryDomain;
  study?: BatteryDomain;
  scores?: Record<string, number>;
  low_power_mode?: boolean;
  fast_charge_domain?: string;
  power_drain_domain?: string;
}

interface FortuneData {
  bazi_analysis?: any;
  tarot_reading?: any;
  battery_fortune?: BatteryFortune;
  from_cache?: boolean;
}

interface FortuneTabProps {
  onThemeChange: (theme: ThemeColor) => void;
  onRevealChange?: (revealed: boolean) => void;
  onActiveCatChange?: (cat: string) => void;
  headerSlot?: React.ReactNode;
}

// ── ScoreRing (SVG arc with gradient + glow) ────────────────────
function ScoreRing({ score, size = 54, stroke = 5, color, glowColor }: {
  score: number; size?: number; color: string; stroke?: number; glowColor?: string;
}) {
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, score));
  const offset = circ - (pct / 100) * circ;
  const gradId = `ring-grad-${color.replace(/[^a-zA-Z0-9]/g, "")}`;
  const glow = glowColor || color;
  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)", filter: `drop-shadow(0 0 6px ${glow}40)` }}>
        <defs>
          <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={color} stopOpacity="0.6" />
            <stop offset="100%" stopColor={color} />
          </linearGradient>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none"
          stroke="rgba(0,0,0,0.04)" strokeWidth={stroke} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none"
          stroke={`url(#${gradId})`} strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={circ} strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 1s cubic-bezier(0.4,0,0.2,1)" }} />
      </svg>
      <div style={{
        position: "absolute", inset: 0, display: "flex", alignItems: "center",
        justifyContent: "center", fontSize: size > 60 ? 16 : 14, fontWeight: 600,
        fontFamily: "'Fraunces',serif", color,
      }}>{pct}</div>
    </div>
  );
}

// ── CategorySidebar ──────────────────────────────────────────────
function CategorySidebar({ active, onChange }: {
  active: string; onChange: (key: string) => void;
}) {
  return (
    <div style={{
      width: 84, flexShrink: 0, display: "flex", flexDirection: "column",
      alignItems: "center", gap: 4, padding: "20px 0",
      background: "rgba(253,251,248,0.55)", backdropFilter: "blur(20px)",
      WebkitBackdropFilter: "blur(20px)",
      borderRight: "1px solid rgba(0,0,0,0.03)",
      position: "sticky", top: 0, alignSelf: "flex-start", height: "100%",
      overflowY: "auto",
    }}>
      {categories.map(c => {
        const isActive = c.key === active;
        const nav = navColors[c.key as keyof typeof navColors] || navColors.overall;
        return (
          <button key={c.key} onClick={() => onChange(c.key)} style={{
            width: 60, height: 60, borderRadius: 18, border: "none", cursor: "pointer",
            display: "flex", flexDirection: "column", alignItems: "center",
            justifyContent: "center", gap: 3, fontSize: 20,
            background: isActive
              ? `linear-gradient(135deg, ${nav.light}, ${nav.dark})`
              : "transparent",
            color: isActive ? nav.text : T.text.quaternary,
            boxShadow: isActive ? `0 4px 16px ${nav.dark}30` : "none",
            transition: "all 0.35s cubic-bezier(0.2,0.8,0.2,1)",
            transform: isActive ? "scale(1.08)" : "scale(1)",
          }}>
            <span style={{ filter: isActive ? "brightness(1.1)" : "none" }}>{c.icon}</span>
            <span style={{
              fontSize: 9, fontWeight: isActive ? 700 : 500,
              color: isActive ? nav.text : T.text.quaternary,
              transition: "color 0.3s",
            }}>{c.label}</span>
          </button>
        );
      })}
    </div>
  );
}

// ── TarotDraw (5-card fan + flip animation) ──────────────────────
function TarotDraw({ tarot, theme, onGenerate, generating }: {
  tarot: any; theme: ThemeColor; onGenerate: () => void; generating: boolean;
}) {
  const [revealed, setRevealed] = useState(false);
  const [flippedCards, setFlippedCards] = useState<number[]>([]);

  useEffect(() => {
    if (tarot?.card) {
      const t = setTimeout(() => setRevealed(true), 400);
      return () => clearTimeout(t);
    } else {
      setRevealed(false);
      setFlippedCards([]);
    }
  }, [tarot]);

  // Auto-flip cards sequentially after reveal
  useEffect(() => {
    if (revealed && flippedCards.length < 5) {
      const t = setTimeout(() => {
        setFlippedCards(prev => [...prev, prev.length]);
      }, 300 + flippedCards.length * 200);
      return () => clearTimeout(t);
    }
  }, [revealed, flippedCards.length]);

  const fanAngles = [-24, -12, 0, 12, 24];
  const fanOffsets = [-8, -3, 0, -3, -8];

  if (!tarot?.card) {
    // Not generated — show the diffuse sphere CTA with 5-card fan
    return (
      <div style={{
        display: "flex", flexDirection: "column", alignItems: "center",
        justifyContent: "center", padding: "36px 0 28px", gap: 24,
      }}>
        {/* 5-card fan (face down) */}
        <div style={{ position: "relative", width: 260, height: 180, display: "flex", alignItems: "center", justifyContent: "center" }}>
          {fanAngles.map((angle, i) => (
            <div key={i} style={{
              position: "absolute",
              width: 72, height: 108, borderRadius: 12,
              background: `linear-gradient(135deg, ${theme.soft}, ${theme.p}90)`,
              border: `1px solid ${theme.p}30`,
              boxShadow: `0 4px 16px ${theme.p}20`,
              transform: `rotate(${angle}deg) translateY(${fanOffsets[i]}px)`,
              transformOrigin: "center bottom",
              transition: "all 0.5s cubic-bezier(0.2,0.8,0.2,1)",
              display: "flex", alignItems: "center", justifyContent: "center",
              zIndex: 5 - Math.abs(i - 2),
            }}>
              <span style={{ fontSize: 24, opacity: 0.6 }}>✦</span>
            </div>
          ))}
        </div>
        <div style={{ textAlign: "center" }}>
          <p style={{ fontFamily: "'Fraunces',serif", fontSize: 18, fontWeight: 500, color: T.text.primary, marginBottom: 6 }}>
            Today&apos;s Fortune
          </p>
          <p style={{ fontSize: 13, color: T.text.tertiary }}>
            Tap to reveal your daily reading
          </p>
        </div>
        <button onClick={onGenerate} disabled={generating} style={{
          padding: "12px 36px", borderRadius: 100, border: "none", cursor: "pointer",
          fontSize: 14, fontWeight: 600, fontFamily: "inherit", color: "#fff",
          background: `linear-gradient(135deg,${theme.s},${theme.p})`,
          boxShadow: `0 4px 20px ${theme.p}30`,
          opacity: generating ? 0.7 : 1, transition: "all 0.2s",
        }}>
          {generating ? (
            <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className="pulse-dot" style={{ width: 5, height: 5, borderRadius: "50%", background: "#fff" }} />
              <span className="pulse-dot" style={{ width: 5, height: 5, borderRadius: "50%", background: "#fff" }} />
              <span className="pulse-dot" style={{ width: 5, height: 5, borderRadius: "50%", background: "#fff" }} />
            </span>
          ) : "Reveal Fortune"}
        </button>
      </div>
    );
  }

  // Revealed tarot card with fan flip
  const card = tarot.card;
  const isUpright = tarot.orientation === "upright";
  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center",
      padding: "28px 0 20px", gap: 16,
    }}>
      {/* 5-card fan (flipping) */}
      <div style={{ position: "relative", width: 280, height: 180, display: "flex", alignItems: "center", justifyContent: "center" }}>
        {fanAngles.map((angle, i) => {
          const isFlipped = flippedCards.includes(i);
          const isCenter = i === 2;
          return (
            <div key={i} style={{
              position: "absolute",
              width: isCenter ? 80 : 72, height: isCenter ? 116 : 108,
              borderRadius: 12,
              transform: `rotate(${angle}deg) translateY(${fanOffsets[i]}px) ${isFlipped ? "rotateY(180deg)" : ""}`,
              transformOrigin: "center bottom",
              transition: "all 0.6s cubic-bezier(0.2,0.8,0.2,1)",
              transformStyle: "preserve-3d",
              zIndex: isCenter ? 10 : 5 - Math.abs(i - 2),
              perspective: 600,
            }}>
              {/* Back face */}
              <div style={{
                position: "absolute", inset: 0, borderRadius: 12,
                background: `linear-gradient(135deg, ${theme.soft}, ${theme.p}90)`,
                border: `1px solid ${theme.p}30`,
                boxShadow: `0 4px 16px ${theme.p}20`,
                backfaceVisibility: "hidden",
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                <span style={{ fontSize: 24, opacity: 0.6 }}>✦</span>
              </div>
              {/* Front face */}
              <div style={{
                position: "absolute", inset: 0, borderRadius: 12,
                background: `linear-gradient(135deg, rgba(255,255,255,0.95), ${theme.airy})`,
                border: `1px solid ${theme.soft}60`,
                boxShadow: isCenter ? `0 8px 28px ${theme.p}25` : `0 4px 16px ${theme.p}15`,
                backfaceVisibility: "hidden",
                transform: "rotateY(180deg)",
                display: "flex", alignItems: "center", justifyContent: "center",
                flexDirection: "column", gap: 2, padding: 6,
              }}>
                <span style={{ fontSize: isCenter ? 28 : 20 }}>🎴</span>
                {isCenter && (
                  <span style={{ fontSize: 8, fontWeight: 600, color: theme.p, textAlign: "center", lineHeight: 1.2 }}>
                    {card.card_name?.split(" ").slice(0, 2).join(" ")}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div style={{
        textAlign: "center",
        opacity: revealed ? 1 : 0, transform: revealed ? "translateY(0)" : "translateY(12px)",
        transition: "all 0.8s cubic-bezier(0.2,0.8,0.2,1)",
      }}>
        <p style={{ fontFamily: "'Fraunces',serif", fontSize: 20, fontWeight: 500, color: T.text.primary }}>
          {card.card_name}
        </p>
        <span style={{
          display: "inline-block", marginTop: 6, padding: "3px 12px", borderRadius: 100,
          fontSize: 11, fontWeight: 600,
          background: isUpright ? "#dcfce7" : "#fee2e2",
          color: isUpright ? "#16a34a" : "#dc2626",
        }}>
          {isUpright ? "Upright" : "Reversed"}
        </span>
        <p style={{ fontSize: 13, color: T.text.tertiary, marginTop: 8, maxWidth: 320, lineHeight: 1.6, margin: "8px auto 0" }}>
          {isUpright ? card.meaning_up : card.meaning_down}
        </p>
      </div>
    </div>
  );
}

// ── FullFortuneCard (single category card — matches web2.html) ────
function FullFortuneCard({ cat, score, summary, insights, theme }: {
  cat: { key: string; label: string; icon: string; desc: string };
  score: number;
  summary: string;
  insights: { t: string; x: string }[];
  theme: ThemeColor;
}) {
  return (
    <div style={{
      borderRadius: 24, overflow: "hidden",
      background: "rgba(255,255,255,0.72)",
      backdropFilter: "blur(24px)", WebkitBackdropFilter: "blur(24px)",
      border: "none",
      boxShadow: `0 2px 4px rgba(0,0,0,0.03), 0 8px 24px rgba(0,0,0,0.06), 0 16px 48px ${theme.p}0A, inset 0 1px 0 rgba(255,255,255,0.6)`,
      transition: "box-shadow 0.4s ease, background 0.6s ease",
    }}>
      <div style={{ padding: "26px 26px 20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div style={{
              width: 50, height: 50, borderRadius: 18,
              background: `${theme.soft}45`,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 26,
            }}>{cat.icon}</div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 600, color: T.text.primary }}>{cat.label}</div>
              <div style={{ fontSize: 12, color: T.text.quaternary, marginTop: 2 }}>{cat.desc}</div>
            </div>
          </div>
          <ScoreRing score={score} color={theme.p} size={64} glowColor={theme.p} />
        </div>
        <p style={{ fontSize: 15, lineHeight: 1.85, color: T.text.secondary, margin: 0 }}>{summary}</p>
      </div>

      <div style={{ padding: "0 14px 14px", display: "flex", flexDirection: "column", gap: 10 }}>
        {insights.map((c, i) => (
          <div key={i} style={{
            padding: "18px 20px", borderRadius: 20,
            background: `linear-gradient(135deg, ${theme.airy}, ${theme.soft}22)`,
            boxShadow: "inset 0 1px 0 rgba(255,255,255,0.5)",
          }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: theme.p, marginBottom: 8 }}>
              {c.t}
            </div>
            <div style={{ fontSize: 14, lineHeight: 1.8, color: T.text.secondary }}>{c.x}</div>
          </div>
        ))}
      </div>
    </div>
  );
}


// ── FortuneTab (main export) ─────────────────────────────────────
export function FortuneTab({ onThemeChange, onRevealChange, onActiveCatChange, headerSlot }: FortuneTabProps) {
  const [fortune, setFortune] = useState<FortuneData | null>(null);
  const [isGenerated, setIsGenerated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [activeCat, setActiveCat] = useState("overall");

  const today = new Date().toISOString().slice(0, 10);
  const currentCat = categories.find(c => c.key === activeCat) || categories[0];
  const theme = currentCat.theme;

  useEffect(() => {
    onThemeChange(theme);
  }, [theme, onThemeChange]);

  useEffect(() => {
    onRevealChange?.(isGenerated);
  }, [isGenerated, onRevealChange]);

  useEffect(() => {
    onActiveCatChange?.(activeCat);
  }, [activeCat, onActiveCatChange]);

  // IntersectionObserver: scroll tracking for active category
  useEffect(() => {
    if (!isGenerated) return;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && entry.intersectionRatio > 0.5) {
            const catKey = entry.target.id.replace("card-", "");
            setActiveCat(catKey);
          }
        });
      },
      { threshold: [0.5], rootMargin: "-20% 0px -20% 0px" }
    );
    categories.forEach(c => {
      const el = document.getElementById(`card-${c.key}`);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, [isGenerated]);

  const checkStatus = useCallback(async () => {
    try {
      const s = await getFortuneStatus(today);
      setIsGenerated(s.is_generated);
      if (s.is_generated) {
        const data = await getDailyFortune(today);
        setFortune(data);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [today]);

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  const handleGenerate = async () => {
    setGenerating(true);
    setError("");
    try {
      const data = await getDailyFortune(today);
      setFortune(data);
      setIsGenerated(true);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setGenerating(false);
    }
  };

  const bat = fortune?.battery_fortune;
  const tarot = fortune?.tarot_reading;

  // Build per-category card data from battery_fortune
  const buildCardData = (catKey: string) => {
    if (!bat) return null;
    const scores = bat.scores || {};
    if (catKey === "overall") {
      const o = bat.overall;
      if (!o) return null;
      return {
        score: scores["overall"] || Math.round(Object.values(scores).reduce((a, b) => a + b, 0) / (Object.values(scores).length || 1)),
        summary: o.daily_management || "",
        insights: [
          o.today_actions ? { t: "Today's Action", x: o.today_actions } : null,
          o.power_drain ? { t: "Power Drain", x: o.power_drain } : null,
          o.surge_protection ? { t: "Surge Protection", x: o.surge_protection } : null,
          o.recharge ? { t: "Recharge", x: o.recharge } : null,
        ].filter(Boolean) as { t: string; x: string }[],
      };
    }
    const domain = bat[catKey as keyof BatteryFortune] as BatteryDomain | undefined;
    if (!domain) return null;
    return {
      score: scores[catKey] || 0,
      summary: domain.status || "",
      insights: [
        domain.suggestion ? { t: "Suggestion", x: domain.suggestion } : null,
      ].filter(Boolean) as { t: string; x: string }[],
    };
  };

  if (loading) {
    return (
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ display: "flex", gap: 6 }}>
          <span className="pulse-dot" style={{ width: 6, height: 6, borderRadius: "50%", background: T.coral.p }} />
          <span className="pulse-dot" style={{ width: 6, height: 6, borderRadius: "50%", background: T.coral.p }} />
          <span className="pulse-dot" style={{ width: 6, height: 6, borderRadius: "50%", background: T.coral.p }} />
        </div>
      </div>
    );
  }

  return (
    <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
      {/* CategorySidebar — only after reveal */}
      {isGenerated && (
        <CategorySidebar active={activeCat} onChange={(key) => {
          setActiveCat(key);
          document.getElementById(`card-${key}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
        }} />
      )}

      <div className="fortune-scroll" style={{
        flex: 1, overflowY: "auto", padding: "20px 32px 40px",
      }}>
        {headerSlot}

        {error && (
          <div style={{
            padding: "10px 16px", borderRadius: 14, background: "#fee2e2",
            fontSize: 12, color: "#dc2626", marginBottom: 16,
          }}>{error}</div>
        )}

        <TarotDraw tarot={isGenerated ? tarot : null} theme={theme} onGenerate={handleGenerate} generating={generating} />

        {isGenerated && bat && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20, marginTop: 8 }}>
            {categories.map(cat => {
              const data = buildCardData(cat.key);
              if (!data) return null;
              return (
                <div key={cat.key} id={`card-${cat.key}`} style={{ scrollMarginTop: 20 }}>
                  <FullFortuneCard
                    cat={cat}
                    score={data.score}
                    summary={data.summary}
                    insights={data.insights}
                    theme={cat.theme}
                  />
                </div>
              );
            })}

            <div style={{ textAlign: "center", padding: "4px 0 8px" }}>
              <span style={{ fontSize: 12, color: T.text.quaternary }}>The more you write, the smarter your fortune gets</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
