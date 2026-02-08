"use client";

import { T, ThemeColor } from "../lib/theme";

interface CelestialPanelProps {
  onClose: () => void;
  theme: ThemeColor;
  fortune: any;
}

export function CelestialPanel({ onClose, theme, fortune }: CelestialPanelProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", position: "relative" }}>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "16px 20px 12px", flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{
            width: 8, height: 8, borderRadius: "50%",
            background: `linear-gradient(135deg,${theme.s},${theme.p})`,
          }} />
          <span style={{
            fontFamily: "'Fraunces',serif", fontSize: 15, fontWeight: 500,
            color: T.text.primary,
          }}>Today&apos;s Celestial</span>
        </div>
        <button onClick={onClose} style={{
          width: 28, height: 28, borderRadius: 9, border: "none", cursor: "pointer",
          background: "rgba(0,0,0,0.04)", fontSize: 12, color: T.text.tertiary,
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>✕</button>
      </div>

      {/* Body */}
      <div style={{ flex: 1, overflowY: "auto", padding: "8px 20px 32px" }}>
        {/* BaZi section */}
        <div style={{
          background: "rgba(255,255,255,0.6)", borderRadius: 20, padding: "18px 20px",
          border: "1px solid rgba(255,255,255,0.5)", marginBottom: 14,
          boxShadow: "0 2px 12px rgba(0,0,0,0.02)",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
            <span style={{ fontSize: 15 }}>☯️</span>
            <span style={{ fontFamily: "'Fraunces',serif", fontSize: 14, fontWeight: 500, color: T.text.primary }}>
              BaZi Analysis
            </span>
          </div>
          <p style={{ fontSize: 12.5, color: T.text.secondary, lineHeight: 1.7 }}>
            {fortune?.bazi_analysis?.summary || "Your BaZi analysis will appear here after generating your fortune."}
          </p>
        </div>

        {/* Tarot section */}
        <div style={{
          background: "rgba(255,255,255,0.6)", borderRadius: 20, padding: "18px 20px",
          border: "1px solid rgba(255,255,255,0.5)", marginBottom: 14,
          boxShadow: "0 2px 12px rgba(0,0,0,0.02)",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
            <span style={{ fontSize: 15 }}>🎴</span>
            <span style={{ fontFamily: "'Fraunces',serif", fontSize: 14, fontWeight: 500, color: T.text.primary }}>
              Tarot Reading
            </span>
          </div>
          <p style={{ fontSize: 12.5, color: T.text.secondary, lineHeight: 1.7 }}>
            {fortune?.tarot_reading?.interpretation || "Your tarot reading will appear here after generating your fortune."}
          </p>
        </div>

        {/* Energy tips */}
        <div style={{
          background: `${theme.airy}`, borderRadius: 20, padding: "18px 20px",
          border: `1px solid ${theme.soft}40`,
          boxShadow: "0 2px 12px rgba(0,0,0,0.02)",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
            <span style={{ fontSize: 15 }}>✨</span>
            <span style={{ fontFamily: "'Fraunces',serif", fontSize: 14, fontWeight: 500, color: theme.p }}>
              Energy Tips
            </span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
              <span style={{ fontSize: 12, flexShrink: 0 }}>⚡</span>
              <span style={{ fontSize: 12, color: T.text.secondary, lineHeight: 1.6 }}>
                Peak energy hours: 10am - 12pm
              </span>
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
              <span style={{ fontSize: 12, flexShrink: 0 }}>🔋</span>
              <span style={{ fontSize: 12, color: T.text.secondary, lineHeight: 1.6 }}>
                Recharge with a short walk in nature
              </span>
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
              <span style={{ fontSize: 12, flexShrink: 0 }}>🛡️</span>
              <span style={{ fontSize: 12, color: T.text.secondary, lineHeight: 1.6 }}>
                Avoid major financial decisions after 3pm
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
