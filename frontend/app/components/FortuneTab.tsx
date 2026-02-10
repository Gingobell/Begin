"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { getFortuneStatus, getDailyFortune } from "../lib/api";
import { T, ThemeColor, categories, navColors, iconSize } from "../lib/theme";
import { useTranslation } from "../i18n";

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
  language?: string;
  onThemeChange: (theme: ThemeColor) => void;
  onRevealChange?: (revealed: boolean) => void;
  onActiveCatChange?: (cat: string) => void;
  onFortuneChange?: (data: FortuneData | null) => void;
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
  const { t } = useTranslation();
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
            <img src={c.icon} alt={t(`nav.${c.key}`)} style={{ width: iconSize.nav, height: iconSize.nav, filter: isActive ? "brightness(1.1)" : "none" }} />
            <span style={{
              fontSize: 9, fontWeight: isActive ? 700 : 500,
              color: isActive ? nav.text : T.text.quaternary,
              transition: "color 0.3s",
            }}>{t(`nav.${c.key}`)}</span>
          </button>
        );
      })}
    </div>
  );
}

// ── Floating particles for mystical atmosphere ───────────────────
function MysticalParticles({ theme }: { theme: ThemeColor }) {
  const particles = Array.from({ length: 12 }, (_, i) => ({
    id: i,
    x: Math.random() * 100,
    y: Math.random() * 100,
    size: 2 + Math.random() * 3,
    dur: 3 + Math.random() * 4,
    delay: Math.random() * 3,
  }));
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", pointerEvents: "none" }}>
      {particles.map(p => (
        <motion.div
          key={p.id}
          style={{
            position: "absolute", left: `${p.x}%`, top: `${p.y}%`,
            width: p.size, height: p.size, borderRadius: "50%",
            background: `radial-gradient(circle, ${theme.soft}, ${theme.p}40)`,
          }}
          animate={{ y: [0, -20, 0], opacity: [0.2, 0.7, 0.2] }}
          transition={{ duration: p.dur, delay: p.delay, repeat: Infinity, ease: "easeInOut" }}
        />
      ))}
    </div>
  );
}

// ── Spring config for card flip ──────────────────────────────────
const flipSpring = { type: "spring" as const, stiffness: 300, damping: 40 };

// ── TarotDraw (immersive draw-card experience with framer-motion) ─
function TarotDraw({ theme, onGenerate, generating, t }: {
  theme: ThemeColor; onGenerate: () => void; generating: boolean; t: (key: string) => string;
}) {
  const [selected, setSelected] = useState<number | null>(null);
  const [hovered, setHovered] = useState<number | null>(null);
  const CARD_COUNT = 7;
  const fanAngles = [-45, -30, -15, 0, 15, 30, 45];
  const fanOffsets = [-18, -10, -4, 0, -4, -10, -18];

  const handleCardClick = (i: number) => {
    if (selected !== null || generating) return;
    setSelected(i);
    onGenerate();
  };

  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center",
      justifyContent: "center", minHeight: "calc(100vh - 160px)",
      position: "relative", padding: "20px 0",
    }}>
      <MysticalParticles theme={theme} />

      {/* Title area */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        style={{ textAlign: "center", marginBottom: 48, position: "relative", zIndex: 1 }}
      >
        <p style={{
          fontFamily: "'Fraunces',serif", fontSize: 28, fontWeight: 500,
          color: T.text.primary, marginBottom: 8,
          background: `linear-gradient(135deg, ${theme.p}, ${theme.s})`,
          WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
        }}>
          {t("fortune.chooseCard")}
        </p>
        <p style={{ fontSize: 14, color: T.text.tertiary, lineHeight: 1.6 }}>
          {t("fortune.chooseCardHint")}
        </p>
      </motion.div>

      {/* Card spread */}
      <div style={{
        position: "relative", width: "100%", maxWidth: 620,
        height: 380, display: "flex", alignItems: "center", justifyContent: "center",
      }}>
        {fanAngles.map((angle, i) => {
          const isSelected = selected === i;
          const isOther = selected !== null && !isSelected;
          const isHov = hovered === i && selected === null;
          return (
            <motion.div
              key={i}
              onClick={() => handleCardClick(i)}
              onHoverStart={() => selected === null && setHovered(i)}
              onHoverEnd={() => setHovered(null)}
              initial={{ opacity: 0, y: 60, rotate: 0 }}
              animate={{
                opacity: isOther ? 0 : 1,
                y: isSelected ? -20 : isHov ? -18 : 0,
                rotate: isSelected ? 0 : angle,
                scale: isSelected ? 1.15 : isHov ? 1.08 : 1,
                x: isSelected ? 0 : undefined,
              }}
              transition={{
                opacity: { duration: 0.4 },
                y: { type: "spring", stiffness: 200, damping: 25 },
                rotate: { type: "spring", stiffness: 200, damping: 25 },
                scale: { type: "spring", stiffness: 300, damping: 30 },
                default: { delay: i * 0.08 },
              }}
              style={{
                position: "absolute",
                width: 140, height: 210,
                cursor: selected === null && !generating ? "pointer" : "default",
                transformOrigin: "center bottom",
                zIndex: isSelected ? 20 : isHov ? 15 : 7 - Math.abs(i - 3),
                perspective: 1000,
                marginTop: fanOffsets[i],
              }}
            >
              {/* Card container with 3D flip */}
              <div style={{
                width: "100%", height: "100%", position: "relative",
                transformStyle: "preserve-3d",
              }}>
                {/* Back face — frosted glass */}
                <motion.div
                  animate={{ rotateY: isSelected ? -180 : 0 }}
                  transition={flipSpring}
                  style={{
                    position: "absolute", inset: 0, borderRadius: 14,
                    overflow: "hidden", backfaceVisibility: "hidden",
                    background: "rgba(255,255,255,0.55)",
                    backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)",
                    border: "1px solid rgba(255,255,255,0.7)",
                    boxShadow: isHov
                      ? `0 12px 40px ${theme.p}35, 0 0 20px ${theme.soft}50, inset 0 1px 0 rgba(255,255,255,0.8)`
                      : `0 4px 20px rgba(0,0,0,0.08), 0 0 12px ${theme.soft}30, inset 0 1px 0 rgba(255,255,255,0.6)`,
                    transition: "box-shadow 0.3s ease",
                    zIndex: isSelected ? 0 : 1,
                    display: "flex", alignItems: "center", justifyContent: "center",
                  }}
                >
                  <span style={{ fontSize: 24, opacity: 0.25, color: theme.p }}>✦</span>
                  {/* Shimmer overlay on hover */}
                  {isHov && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      style={{
                        position: "absolute", inset: 0,
                        background: `linear-gradient(135deg, transparent 30%, ${theme.soft}40 50%, transparent 70%)`,
                        backgroundSize: "200% 200%",
                        animation: "shimmer 1.5s ease-in-out infinite",
                      }}
                    />
                  )}
                </motion.div>

                {/* Front face (placeholder — actual image shown in reveal phase) */}
                <motion.div
                  initial={{ rotateY: 180 }}
                  animate={{ rotateY: isSelected ? 0 : 180 }}
                  transition={flipSpring}
                  style={{
                    position: "absolute", inset: 0, borderRadius: 14,
                    overflow: "hidden", backfaceVisibility: "hidden",
                    boxShadow: `0 16px 48px ${theme.p}30, 0 0 30px ${theme.soft}40`,
                    zIndex: isSelected ? 1 : 0,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    background: `linear-gradient(160deg, ${theme.airy}, ${theme.soft}60)`,
                  }}
                >
                  {generating ? (
                    <div style={{ display: "flex", gap: 6 }}>
                      <span className="pulse-dot" style={{ width: 6, height: 6, borderRadius: "50%", background: theme.p }} />
                      <span className="pulse-dot" style={{ width: 6, height: 6, borderRadius: "50%", background: theme.p }} />
                      <span className="pulse-dot" style={{ width: 6, height: 6, borderRadius: "50%", background: theme.p }} />
                    </div>
                  ) : (
                    <span style={{ fontSize: 32, color: theme.p, opacity: 0.5 }}>✦</span>
                  )}
                </motion.div>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Bottom hint */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: generating ? 0 : 1 }}
        transition={{ delay: 0.6, duration: 0.5 }}
        style={{
          fontSize: 12, color: T.text.quaternary, marginTop: 40,
          position: "relative", zIndex: 1,
        }}
      >
        {selected !== null ? "" : t("fortune.cardsAwait").replace("{count}", String(CARD_COUNT))}
      </motion.p>

      {/* Generating overlay text */}
      <AnimatePresence>
        {generating && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            style={{
              marginTop: 24, textAlign: "center", position: "relative", zIndex: 1,
            }}
          >
            <p style={{
              fontFamily: "'Fraunces',serif", fontSize: 16, color: theme.p,
              fontWeight: 500,
            }}>
              {t("fortune.readingStars")}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── FullFortuneCard (single category card — matches web2.html) ────
function FullFortuneCard({ cat, score, summary, insights, theme }: {
  cat: { key: string; icon: string; theme: ThemeColor };
  score: number;
  summary: string;
  insights: { t: string; x: string }[];
  theme: ThemeColor;
}) {
  const { t } = useTranslation();
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
              }}><img src={cat.icon} alt={t(`nav.${cat.key}`)} style={{ width: iconSize.card, height: iconSize.card }} /></div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 600, color: T.text.primary }}>{t(`nav.${cat.key}`)}</div>
              <div style={{ fontSize: 12, color: T.text.quaternary, marginTop: 2 }}>{t(`catDesc.${cat.key}`)}</div>
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
export function FortuneTab({ language, onThemeChange, onRevealChange, onActiveCatChange, onFortuneChange, headerSlot }: FortuneTabProps) {
  const { t } = useTranslation();
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

  useEffect(() => {
    onFortuneChange?.(fortune);
  }, [fortune, onFortuneChange]);

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
        const data = await getDailyFortune(today, language);
        setFortune(data);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [today, language]);

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  // Re-fetch with force_regenerate when language changes (skip initial mount)
  const langMountRef = useRef(true);
  useEffect(() => {
    if (langMountRef.current) {
      langMountRef.current = false;
      return;
    }
    if (!isGenerated) return;
    let cancelled = false;
    (async () => {
      setGenerating(true);
      try {
        const data = await getDailyFortune(today, language, true);
        if (!cancelled) {
          setFortune(data);
        }
      } catch (err: any) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setGenerating(false);
      }
    })();
    return () => { cancelled = true; };
  }, [language]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleGenerate = async () => {
    setGenerating(true);
    setError("");
    try {
      const data = await getDailyFortune(today, language);
      setFortune(data);
      setIsGenerated(true);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setGenerating(false);
    }
  };

  const bat = fortune?.battery_fortune;

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
          o.today_actions ? { t: t("fortune.todayAction"), x: o.today_actions } : null,
          o.power_drain ? { t: t("fortune.powerDrain"), x: o.power_drain } : null,
          o.surge_protection ? { t: t("fortune.surgeProtection"), x: o.surge_protection } : null,
          o.recharge ? { t: t("fortune.recharge"), x: o.recharge } : null,
        ].filter(Boolean) as { t: string; x: string }[],
      };
    }
    const domain = bat[catKey as keyof BatteryFortune] as BatteryDomain | undefined;
    if (!domain) return null;
    return {
      score: scores[catKey] || 0,
      summary: domain.status || "",
      insights: [
        domain.suggestion ? { t: t("fortune.suggestion"), x: domain.suggestion } : null,
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

        {!isGenerated && (
          <TarotDraw theme={theme} onGenerate={handleGenerate} generating={generating} t={t} />
        )}

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
              <span style={{ fontSize: 12, color: T.text.quaternary }}>{t("fortune.moreYouWrite")}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
