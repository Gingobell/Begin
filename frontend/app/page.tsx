"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { T } from "./lib/theme";

// ── Fade-in on scroll ────────────────────────────────────────────
function useFadeIn() {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) { setVisible(true); obs.disconnect(); } },
      { threshold: 0.15 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  return { ref, style: { opacity: visible ? 1 : 0, transform: visible ? "translateY(0)" : "translateY(24px)", transition: "opacity 0.8s ease, transform 0.8s ease" } as React.CSSProperties };
}

// ── Nav ──────────────────────────────────────────────────────────
function Nav({ onGetStarted }: { onGetStarted: () => void }) {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const h = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", h, { passive: true });
    return () => window.removeEventListener("scroll", h);
  }, []);

  return (
    <nav style={{
      position: "fixed", top: 0, left: 0, width: "100%", zIndex: 100,
      padding: "16px 0", transition: "all 0.4s ease",
      ...(scrolled ? {
        background: "rgba(253,251,248,0.85)", backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)", borderBottom: "1px solid rgba(255,255,255,0.5)",
        boxShadow: "0 2px 20px rgba(0,0,0,0.04)",
      } : {}),
    }}>
      <div style={{ maxWidth: 1080, margin: "0 auto", padding: "0 32px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontFamily: "'Fraunces',serif", fontSize: 24, fontWeight: 600, color: T.text.primary }}>
          Begin
        </span>
        <div style={{ display: "flex", gap: 36, alignItems: "center" }}>
          <a href="#different" style={{ fontSize: 14, fontWeight: 500, color: T.text.secondary, textDecoration: "none" }}>Why Begin</a>
          <a href="#action" style={{ fontSize: 14, fontWeight: 500, color: T.text.secondary, textDecoration: "none" }}>See it work</a>
          <a href="#engine" style={{ fontSize: 14, fontWeight: 500, color: T.text.secondary, textDecoration: "none" }}>How it works</a>
          <button onClick={onGetStarted} style={{
            display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8,
            padding: "10px 24px", border: "none", borderRadius: 20,
            fontFamily: "'DM Sans',sans-serif", fontSize: 13, fontWeight: 600,
            letterSpacing: "0.02em", cursor: "pointer",
            background: `linear-gradient(to right,${T.coral.s},${T.coral.p})`,
            color: "white", boxShadow: "0 8px 24px rgba(255,107,74,0.24)",
            transition: "all 0.3s cubic-bezier(0.34,1.56,0.64,1)",
          }}>Get Started</button>
        </div>
      </div>
    </nav>
  );
}

// ── Orb Background ───────────────────────────────────────────────
function OrbBackground() {
  return (
    <div style={{ position: "fixed", top: 0, left: 0, width: "100%", height: "100%", pointerEvents: "none", zIndex: 0, overflow: "hidden" }}>
      {[
        { w: 400, h: 400, bg: "rgba(255,107,74,0.35)", top: -120, left: -80, dur: "22s" },
        { w: 300, h: 300, bg: "rgba(255,138,106,0.28)", top: -60, right: -60, dur: "18s", delay: "-4s" },
        { w: 350, h: 350, bg: "rgba(255,184,154,0.22)", bottom: "30%", left: "10%", dur: "25s", delay: "-8s" },
        { w: 320, h: 320, bg: "rgba(92,139,255,0.30)", top: "55%", right: -50, dur: "24s", delay: "-6s" },
        { w: 250, h: 250, bg: "rgba(122,163,255,0.20)", bottom: "5%", left: -40, dur: "20s", delay: "-10s" },
        { w: 280, h: 280, bg: "rgba(255,215,90,0.22)", top: "40%", left: "50%", dur: "26s", delay: "-12s" },
        { w: 200, h: 200, bg: "rgba(143,107,247,0.18)", bottom: "20%", right: "15%", dur: "19s", delay: "-3s" },
      ].map((o, i) => (
        <div key={i} style={{
          position: "absolute", borderRadius: "50%", filter: "blur(80px)", willChange: "transform",
          width: o.w, height: o.h, background: o.bg,
          top: o.top, left: o.left, right: o.right, bottom: o.bottom,
          animation: `orbFloat ${o.dur} ease-in-out ${o.delay || "0s"} infinite`,
        } as React.CSSProperties} />
      ))}
    </div>
  );
}

// ── Section wrapper ──────────────────────────────────────────────
function Section({ id, children, style }: { id?: string; children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <section id={id} style={{
      minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
      position: "relative", overflow: "hidden", scrollSnapAlign: "start", ...style,
    }}>
      <div style={{ maxWidth: 1080, margin: "0 auto", padding: "0 32px", width: "100%", position: "relative", zIndex: 1 }}>
        {children}
      </div>
    </section>
  );
}

// ── Hero ─────────────────────────────────────────────────────────
function Hero({ onGetStarted }: { onGetStarted: () => void }) {
  return (
    <Section>
      <div style={{ textAlign: "center", maxWidth: 760, margin: "0 auto" }}>
        <h1 style={{
          fontFamily: "'Fraunces',serif", fontSize: "clamp(40px,5.2vw,68px)",
          fontWeight: 500, lineHeight: 1.12, letterSpacing: "-0.02em",
          color: T.text.primary, marginBottom: 20,
          animation: "fadeSlideUp 0.8s ease 0.1s both",
        }}>
          Begin<br />
          <em style={{
            fontStyle: "italic",
            background: `linear-gradient(135deg,${T.coral.p},${T.purple.p})`,
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
          }}>Your Personal Daily<br />Fortune Forecast</em>
        </h1>
        <p style={{
          fontSize: 18, lineHeight: 1.7, color: T.text.secondary,
          marginBottom: 36, maxWidth: 500, marginLeft: "auto", marginRight: "auto",
          animation: "fadeSlideUp 0.8s ease 0.2s both",
        }}>
          Check today&apos;s energy rhythm, just like checking weather
        </p>
        <div style={{
          display: "flex", gap: 16, alignItems: "center", justifyContent: "center",
          animation: "fadeSlideUp 0.8s ease 0.3s both",
        }}>
          <button onClick={onGetStarted} style={{
            display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8,
            padding: "14px 36px", border: "none", borderRadius: 20,
            fontFamily: "'DM Sans',sans-serif", fontSize: 15, fontWeight: 600,
            letterSpacing: "0.02em", cursor: "pointer",
            background: `linear-gradient(to right,${T.coral.s},${T.coral.p})`,
            color: "white", boxShadow: "0 8px 24px rgba(255,107,74,0.24)",
            transition: "all 0.3s cubic-bezier(0.34,1.56,0.64,1)",
          }}>Log In / Sign Up</button>
          <button onClick={() => document.getElementById("different")?.scrollIntoView({ behavior: "smooth" })} style={{
            display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8,
            padding: "12px 28px", background: "rgba(255,255,255,0.78)",
            border: "1.5px solid rgba(255,107,74,0.2)", borderRadius: 100,
            fontFamily: "'DM Sans',sans-serif", fontSize: 14, fontWeight: 500,
            color: T.coral.p, cursor: "pointer",
            transition: "all 0.3s ease", boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
          }}>Learn More &darr;</button>
        </div>
      </div>
    </Section>
  );
}

// ── Why Different ────────────────────────────────────────────────
function WhyDifferent() {
  const f1 = useFadeIn();
  const f2 = useFadeIn();
  const f3 = useFadeIn();

  const cardBase: React.CSSProperties = {
    borderRadius: 22, padding: "32px 28px", display: "flex", flexDirection: "column",
    transition: "transform 0.5s ease, box-shadow 0.5s ease",
  };

  return (
    <Section id="different" style={{ textAlign: "center" }}>
      <div ref={f1.ref} style={f1.style}>
        <div style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 13, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", color: T.coral.p, marginBottom: 12 }}>
          A different kind of forecast
        </div>
        <h2 style={{ fontFamily: "'Fraunces',serif", fontSize: "clamp(28px,3.5vw,44px)", fontWeight: 500, lineHeight: 1.2, letterSpacing: "-0.02em", marginBottom: 16 }}>
          Why is Begin different?
        </h2>
      </div>

      <div ref={f2.ref} style={{ ...f2.style, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, maxWidth: 760, margin: "0 auto 36px" }}>
        <div style={{ ...cardBase, background: "rgba(240,240,238,0.55)", border: "1px solid rgba(0,0,0,0.05)" }}>
          <div style={{ color: T.text.quaternary, fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 14 }}>Other Apps</div>
          <div style={{ fontSize: 17, color: T.text.tertiary, lineHeight: 1.55, fontFamily: "'Fraunces',serif", fontWeight: 400 }}>
            &ldquo;Good day to travel. Financial energy neutral. Be cautious with decisions.&rdquo;
          </div>
        </div>
        <div style={{
          ...cardBase,
          background: "rgba(255,255,255,0.82)", border: "1.5px solid rgba(255,107,74,0.15)",
          backdropFilter: "blur(20px)", boxShadow: "0 12px 40px rgba(255,107,74,0.08)",
        }}>
          <div style={{ color: T.coral.p, fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 14 }}>Begin</div>
          <div style={{ fontSize: 17, color: T.text.primary, lineHeight: 1.55, fontFamily: "'Fraunces',serif", fontWeight: 400 }}>
            &ldquo;That pitch you&apos;re nervous about? <strong style={{ color: T.coral.p, fontWeight: 600 }}>Your energy says direct words hit today.</strong> Go for it.&rdquo;
          </div>
        </div>
      </div>

      <div ref={f3.ref} style={f3.style}>
        <div style={{ fontFamily: "'Fraunces',serif", fontSize: 16, fontStyle: "italic", color: T.text.tertiary, textAlign: "center", lineHeight: 1.6, maxWidth: 460, margin: "0 auto" }}>
          Other apps read a chart. Begin reads <em style={{ color: T.coral.p, fontWeight: 500 }}>you</em>.
        </div>
      </div>
    </Section>
  );
}

// ── See it in Action ─────────────────────────────────────────────
function SeeItInAction() {
  const f1 = useFadeIn();
  const f2 = useFadeIn();

  const timelineNodes = [
    { time: "Last night · 10 PM", icon: "🌙", title: "You wrote", text: "\"Asking boss for a raise tomorrow. Uncertain about timing...\"" },
    { time: "Morning · 7:30 AM", icon: "☀️", title: "Begin says", text: "Communication ★★★★★", sub: "Honesty is your edge today. The energy favors bold moves — trust your gut." },
    { time: "Evening · 7 PM", icon: "✨", title: "You wrote back", text: "\"Got it! 😊 Felt so confident. Best decision.\"" },
  ];

  return (
    <Section id="action" style={{ textAlign: "center" }}>
      <div ref={f1.ref} style={{ ...f1.style, marginBottom: 32 }}>
        <div style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 13, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", color: T.coral.p, marginBottom: 12 }}>
          See it in action
        </div>
        <h2 style={{ fontFamily: "'Fraunces',serif", fontSize: "clamp(28px,3.5vw,44px)", fontWeight: 500, lineHeight: 1.2, letterSpacing: "-0.02em", marginBottom: 16 }}>
          Yesterday, you asked for a raise —<br />and Begin already knew it would work.
        </h2>
      </div>

      <div ref={f2.ref} style={{ ...f2.style, display: "grid", gridTemplateColumns: "1fr auto", gap: 48, alignItems: "center", maxWidth: 820, margin: "0 auto" }}>
        {/* Timeline */}
        <div style={{ position: "relative", paddingLeft: 40 }}>
          <div style={{
            position: "absolute", left: 14, top: 12, bottom: 12, width: 2, borderRadius: 2,
            background: `linear-gradient(to bottom,${T.coral.soft},${T.coral.p},${T.coral.soft})`,
          }} />
          {timelineNodes.map((n, i) => (
            <div key={i} style={{ position: "relative", textAlign: "left", padding: i < timelineNodes.length - 1 ? "8px 0 20px" : "8px 0 0" }}>
              <div style={{
                position: "absolute", left: -32, top: 14, width: 12, height: 12, borderRadius: "50%",
                background: T.coral.p, border: "2.5px solid white",
                boxShadow: `0 0 0 2px ${T.coral.p}, 0 2px 6px rgba(0,0,0,0.1)`,
              }} />
              <div style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6, color: T.coral.p }}>
                {n.icon} {n.time}
              </div>
              <div style={{
                background: "rgba(255,255,255,0.82)", border: "1px solid rgba(255,255,255,0.55)",
                borderRadius: 18, padding: "16px 20px", boxShadow: "0 4px 16px rgba(0,0,0,0.04)",
                fontSize: 14, lineHeight: 1.6, color: T.text.secondary,
              }}>
                <strong style={{ display: "block", fontWeight: 600, color: T.text.primary, marginBottom: 3, fontSize: 14 }}>{n.title}</strong>
                {n.text}
                {n.sub && <><br />{n.sub}</>}
              </div>
            </div>
          ))}
        </div>

        {/* 90 seconds aside */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ fontFamily: "'Fraunces',serif", fontSize: 18, fontWeight: 500, color: T.text.primary, textAlign: "center", marginBottom: 4 }}>
            Just 90 seconds a day
          </div>
          <div style={{ fontSize: 13, color: T.text.tertiary, textAlign: "center" }}>That&apos;s all it takes</div>
          {[
            { icon: "☀️", label: "Morning · 30s", desc: "30 seconds. You'll know.", type: "morning" },
            { icon: "🌙", label: "Evening · 60s", desc: "Tell it tonight. See it tomorrow.", type: "evening" },
          ].map((c) => (
            <div key={c.type} style={{
              display: "flex", alignItems: "center", gap: 14, padding: "16px 24px", borderRadius: 100,
              background: "rgba(255,255,255,0.82)", border: "1px solid rgba(255,255,255,0.55)",
              boxShadow: "0 4px 16px rgba(0,0,0,0.04)", transition: "transform 0.4s ease",
            }}>
              <div style={{
                width: 38, height: 38, borderRadius: "50%", display: "flex", alignItems: "center",
                justifyContent: "center", fontSize: 18, position: "relative",
              }}>{c.icon}</div>
              <div style={{ textAlign: "left" }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: T.text.primary }}>{c.label}</div>
                <div style={{ fontSize: 12, color: T.text.tertiary, marginTop: 1 }}>{c.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Section>
  );
}

// ── The Engine ───────────────────────────────────────────────────
function TheEngine() {
  const f1 = useFadeIn();
  const f2 = useFadeIn();

  const cards = [
    {
      phase: "Day 1 · Meeting you", title: "Your birth chart speaks",
      desc: "BaZi + Tarot give you a baseline forecast — accurate, but still general.",
      quote: "\"Good day for socializing, wealth energy steady.\"",
      color: T.coral.p, soft: T.coral.soft, glow: "rgba(255,138,106,0.35)",
      dotBg: `radial-gradient(circle at 35% 35%, ${T.coral.soft}, ${T.coral.p})`,
      dotShadow: "0 4px 16px rgba(255,107,74,0.25)",
      quoteBg: "rgba(255,107,74,0.06)", quoteBorder: T.coral.soft,
    },
    {
      phase: "Days 2-4 · Learning you", title: "Your diary teaches Begin",
      desc: "Patterns emerge from what you write — goals, worries, rhythm. Forecasts start to feel personal.",
      quote: "\"Tomorrow's pitch — communication energy at its best. You're well-prepared.\"",
      color: T.blue.p, soft: T.blue.soft, glow: "rgba(92,139,255,0.3)",
      dotBg: `radial-gradient(circle at 35% 35%, ${T.blue.soft}, ${T.blue.p})`,
      dotShadow: "0 4px 16px rgba(92,139,255,0.25)",
      quoteBg: "rgba(92,139,255,0.06)", quoteBorder: T.blue.soft,
    },
    {
      phase: "Day 5+ · Knowing you", title: "Your personal oracle",
      desc: "Birth chart + Tarot + full memory of who you are. Every forecast is yours alone.",
      quote: "\"Creative energy is high — push that project you've been mulling over.\"",
      color: T.purple.p, soft: T.purple.soft, glow: "rgba(143,107,247,0.3)",
      dotBg: `radial-gradient(circle at 35% 35%, ${T.purple.soft}, ${T.purple.p})`,
      dotShadow: "0 4px 16px rgba(143,107,247,0.25)",
      quoteBg: "rgba(143,107,247,0.06)", quoteBorder: T.purple.soft,
    },
  ];

  return (
    <Section id="engine" style={{ textAlign: "center" }}>
      <div ref={f1.ref} style={{ ...f1.style, marginBottom: 32 }}>
        <div style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 13, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", color: T.coral.p, marginBottom: 12 }}>
          Day 1 it listens. Day 5 it knows.
        </div>
        <h2 style={{ fontFamily: "'Fraunces',serif", fontSize: "clamp(28px,3.5vw,44px)", fontWeight: 500, lineHeight: 1.2, letterSpacing: "-0.02em", marginBottom: 16 }}>
          What powers your forecast
        </h2>
        <p style={{ fontSize: 16, color: T.text.secondary, maxWidth: 500, margin: "0 auto" }}>
          Ancient patterns. Daily cards. And everything about you.
        </p>
      </div>

      <div ref={f2.ref} style={{ ...f2.style, display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 20, maxWidth: 900, margin: "0 auto" }}>
        {cards.map((c, i) => (
          <div key={i} style={{
            padding: "28px 24px", borderRadius: 24, textAlign: "left",
            background: "rgba(255,255,255,0.82)", border: "1px solid rgba(255,255,255,0.55)",
            backdropFilter: "blur(20px)", boxShadow: "0 6px 24px rgba(0,0,0,0.04)",
            position: "relative", overflow: "hidden",
            transition: "transform 0.5s ease, box-shadow 0.5s ease",
          }}>
            {/* Glow */}
            <div style={{
              position: "absolute", borderRadius: "50%", filter: "blur(50px)", pointerEvents: "none",
              width: 120, height: 120, opacity: 0.35, top: -30, right: -20, background: c.glow,
            }} />
            {/* Dot */}
            <div style={{
              width: 40, height: 40, borderRadius: "50%", marginBottom: 16,
              position: "relative", zIndex: 1, background: c.dotBg, boxShadow: c.dotShadow,
              animation: `dotPulse 4s ease-in-out ${-i * 1.3}s infinite`,
            }} />
            <div style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8, position: "relative", zIndex: 1, color: c.color }}>
              {c.phase}
            </div>
            <div style={{ fontFamily: "'Fraunces',serif", fontSize: 18, fontWeight: 500, color: T.text.primary, marginBottom: 8, position: "relative", zIndex: 1 }}>
              {c.title}
            </div>
            <div style={{ fontSize: 13, lineHeight: 1.6, color: T.text.tertiary, marginBottom: 14, position: "relative", zIndex: 1 }}>
              {c.desc}
            </div>
            <div style={{
              fontSize: 14, lineHeight: 1.55, fontStyle: "italic", color: T.text.secondary,
              padding: "12px 16px", borderRadius: 14, position: "relative", zIndex: 1,
              background: c.quoteBg, borderLeft: `2.5px solid ${c.quoteBorder}`,
            }}>
              {c.quote}
            </div>
          </div>
        ))}
      </div>
    </Section>
  );
}

// ── CTA ──────────────────────────────────────────────────────────
function CtaSection({ onGetStarted }: { onGetStarted: () => void }) {
  const f = useFadeIn();
  return (
    <Section style={{ textAlign: "center" }}>
      <div ref={f.ref} style={f.style}>
        <h2 style={{ fontFamily: "'Fraunces',serif", fontSize: "clamp(34px,4.5vw,52px)", fontWeight: 500, lineHeight: 1.2, marginBottom: 18 }}>
          The more you write,<br />the wiser it gets.
        </h2>
        <p style={{ fontSize: 17, color: T.text.secondary, marginBottom: 36, maxWidth: 460, marginLeft: "auto", marginRight: "auto", lineHeight: 1.7 }}>
          Record today. Foresee tomorrow.
        </p>
        <button onClick={onGetStarted} style={{
          display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8,
          padding: "18px 48px", border: "none", borderRadius: 20,
          fontFamily: "'DM Sans',sans-serif", fontSize: 17, fontWeight: 600,
          letterSpacing: "0.02em", cursor: "pointer",
          background: `linear-gradient(to right,${T.coral.s},${T.coral.p})`,
          color: "white", boxShadow: "0 8px 24px rgba(255,107,74,0.24)",
          transition: "all 0.3s cubic-bezier(0.34,1.56,0.64,1)",
        }}>Begin</button>
        <div style={{ fontFamily: "'Fraunces',serif", fontSize: 16, fontStyle: "italic", color: T.text.tertiary, marginTop: 40 }}>
          Begin. Know. Grow.
        </div>
      </div>
    </Section>
  );
}

// ── Landing Page ─────────────────────────────────────────────────
export default function LandingPage() {
  const router = useRouter();
  const handleGetStarted = () => router.push("/home");

  return (
    <div style={{ background: T.cream, overflowX: "hidden", overflowY: "auto", height: "100vh", scrollSnapType: "y mandatory", scrollBehavior: "smooth" }}>
      <OrbBackground />
      <Nav onGetStarted={handleGetStarted} />
      <div style={{ position: "relative", zIndex: 1 }}>
        <Hero onGetStarted={handleGetStarted} />
        <WhyDifferent />
        <SeeItInAction />
        <TheEngine />
        <CtaSection onGetStarted={handleGetStarted} />
      </div>

      <style>{`
        @keyframes orbFloat {
          0%,100% { transform: translate(0,0) scale(1); }
          25% { transform: translate(30px,-20px) scale(1.05); }
          50% { transform: translate(-20px,15px) scale(0.95); }
          75% { transform: translate(15px,25px) scale(1.02); }
        }
        @keyframes fadeSlideUp {
          from { opacity: 0; transform: translateY(24px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes dotPulse {
          0%,100% { transform: scale(1); }
          50% { transform: scale(1.06); }
        }
      `}</style>
    </div>
  );
}
