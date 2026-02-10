"use client";

import { useState } from "react";
import { T, ThemeColor } from "../lib/theme";
import { useTranslation } from "../i18n";

// ── Default accent: orange/coral (overall fortune theme) ─────────
const P = T.coral;

interface CelestialPanelProps {
  onClose: () => void;
  theme?: ThemeColor;
  fortune: any;
}

// ── Pillar Pill ──────────────────────────────────────────────────
function PillarPill({ label, stem, branch }: { label: string; stem: string; branch: string }) {
  return (
    <div style={{
      flex: 1, display: "flex", flexDirection: "column", alignItems: "center",
      padding: "12px 6px", borderRadius: 14,
      background: `linear-gradient(180deg, ${P.airy}, ${P.soft}20)`,
    }}>
      <div style={{ fontSize: 11, color: T.text.quaternary, fontWeight: 500, marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: 700, color: T.text.primary, lineHeight: 1.2 }}>
        {stem}{branch}
      </div>
    </div>
  );
}

// ── Section with collapse toggle ─────────────────────────────────
function CollapsibleCard({ title, icon, children, defaultOpen = true }: {
  title: string; icon: React.ReactNode; children: React.ReactNode; defaultOpen?: boolean;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{
      background: "rgba(255,255,255,0.85)", borderRadius: 16, padding: 0,
      border: "1px solid rgba(0,0,0,0.05)", marginBottom: 14,
      boxShadow: "0 2px 12px rgba(0,0,0,0.03)",
      overflow: "hidden",
    }}>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", gap: 8,
        padding: "16px 18px 12px",
      }}>
        <div style={{
          width: 28, height: 28, borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center",
          background: `linear-gradient(135deg, ${P.soft}60, ${P.airy})`,
          fontSize: 14,
        }}>{icon}</div>
        <span style={{ fontSize: 15, fontWeight: 600, color: T.text.primary }}>{title}</span>
      </div>

      {/* Body */}
      {open && (
        <div style={{ padding: "0 18px 6px" }}>
          {children}
        </div>
      )}

      {/* Collapse toggle */}
      <div
        onClick={() => setOpen(!open)}
        style={{
          textAlign: "center", padding: "10px 0", cursor: "pointer",
          borderTop: "1px solid rgba(0,0,0,0.04)",
          fontSize: 12, color: T.text.quaternary, fontWeight: 500,
          userSelect: "none",
        }}
      >
        {open ? t("celestial.collapse") + " \u2227" : t("celestial.expand") + " \u2228"}
      </div>
    </div>
  );
}

// ── Influence Section ────────────────────────────────────────────
function InfluenceSection({ title, relation, analysis }: {
  title: string; relation?: string; analysis?: string;
}) {
  if (!relation) return null;
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
        <div style={{ width: 6, height: 6, borderRadius: "50%", background: P.p, flexShrink: 0 }} />
        <span style={{ fontSize: 13, fontWeight: 600, color: T.text.primary }}>{title}</span>
        <span style={{
          fontSize: 11, fontWeight: 600, color: P.p,
          background: `${P.soft}50`, padding: "2px 10px", borderRadius: 20,
        }}>{relation}</span>
      </div>
      {analysis && (
        <div style={{ fontSize: 12.5, color: T.text.secondary, lineHeight: 1.7, paddingLeft: 14 }}>
          {analysis}
        </div>
      )}
    </div>
  );
}

// ── Main Panel ───────────────────────────────────────────────────
export function CelestialPanel({ onClose, fortune }: CelestialPanelProps) {
  const { t, locale } = useTranslation();
  const bazi = fortune?.bazi_analysis;
  const tarot = fortune?.tarot_reading;

  const todayStr = new Date().toLocaleDateString(locale, {
    year: "numeric", month: "2-digit", day: "2-digit", weekday: "long",
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", position: "relative", background: `linear-gradient(180deg, ${P.airy} 0%, ${T.cream} 40%)` }}>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", padding: "16px 18px 10px", flexShrink: 0,
      }}>
        <button onClick={onClose} style={{
          width: 32, height: 32, borderRadius: 10, border: "none", cursor: "pointer",
          background: "rgba(0,0,0,0.04)", fontSize: 16, color: T.text.tertiary,
          display: "flex", alignItems: "center", justifyContent: "center", marginRight: 10,
        }}>&lsaquo;</button>
        <div style={{ flex: 1, textAlign: "center" }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: T.text.primary }}>{t("celestial.title")}</div>
          <div style={{ fontSize: 11, color: T.text.quaternary, marginTop: 2 }}>{todayStr}</div>
        </div>
        <div style={{ width: 32 }} />
      </div>

      {/* Body */}
      <div style={{ flex: 1, overflowY: "auto", padding: "8px 16px 32px" }}>
        {!bazi ? (
          <div style={{
            background: "rgba(255,255,255,0.7)", borderRadius: 16, padding: "32px 20px",
            border: "1px solid rgba(0,0,0,0.05)", textAlign: "center",
          }}>
            <p style={{ fontSize: 13, color: T.text.secondary, lineHeight: 1.7, margin: 0 }}>
              {t("celestial.noData")}
            </p>
          </div>
        ) : (
          <>
            {/* ── Card 1: 八字分析 ── */}
            <CollapsibleCard title={t("celestial.baziAnalysis")} icon={<span style={{ fontSize: 14 }}>&#x23F0;</span>}>
              {/* Pillar pills row */}
              <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
                <PillarPill label={t("celestial.dayMaster")} stem={bazi.day_master || ""} branch="" />
                <PillarPill
                  label={t("celestial.flowYear")}
                  stem={bazi.flow_year?.stem || ""}
                  branch={bazi.flow_year?.branch || ""}
                />
                <PillarPill
                  label={t("celestial.flowMonth")}
                  stem={bazi.flow_month?.stem || ""}
                  branch={bazi.flow_month?.branch || ""}
                />
                <PillarPill
                  label={t("celestial.flowDay")}
                  stem={(bazi.flow_day || bazi.daily_pillar)?.stem || ""}
                  branch={(bazi.flow_day || bazi.daily_pillar)?.branch || ""}
                />
              </div>

              {/* Stem influence */}
              <InfluenceSection
                title={t("celestial.stemInfluence")}
                relation={bazi.stem_influence?.relation}
                analysis={bazi.stem_influence?.analysis}
              />

              {/* Branch influence */}
              <InfluenceSection
                title={t("celestial.branchInfluence")}
                relation={bazi.branch_influence?.relation}
                analysis={bazi.branch_influence?.analysis}
              />

              {/* Energy phase & body strength */}
              {(bazi.energy_phase || bazi.body_strength) && (
                <>
                  <div style={{ height: 1, background: "rgba(0,0,0,0.05)", margin: "4px 0 12px" }} />
                  <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                    {bazi.energy_phase && (
                      <div style={{
                        flex: 1, textAlign: "center", padding: "10px 8px", borderRadius: 12,
                        background: `${P.airy}`,
                      }}>
                        <div style={{ fontSize: 10, color: T.text.quaternary, marginBottom: 4 }}>{t("celestial.energyPhase")}</div>
                        <div style={{ fontSize: 14, fontWeight: 700, color: P.p }}>{bazi.energy_phase}</div>
                      </div>
                    )}
                    {bazi.body_strength && (
                      <div style={{
                        flex: 1, textAlign: "center", padding: "10px 8px", borderRadius: 12,
                        background: `${P.airy}`,
                      }}>
                        <div style={{ fontSize: 10, color: T.text.quaternary, marginBottom: 4 }}>{t("celestial.bodyStrength")}</div>
                        <div style={{ fontSize: 14, fontWeight: 700, color: P.p }}>{bazi.body_strength}</div>
                      </div>
                    )}
                  </div>
                </>
              )}
            </CollapsibleCard>

            {/* ── Card 2: 塔罗启示 ── */}
            {tarot && (
              <CollapsibleCard title={t("celestial.tarotReading")} icon={<span style={{ fontSize: 14 }}>&#x1F0CF;</span>}>
                {/* Tarot card image */}
                {tarot.image_key && (
                  <div style={{ display: "flex", justifyContent: "center", marginBottom: 14 }}>
                    <div style={{
                      width: 140, height: 240, borderRadius: 12, overflow: "hidden",
                      boxShadow: "0 8px 24px rgba(0,0,0,0.12), 0 2px 8px rgba(0,0,0,0.08)",
                      transform: tarot.orientation === "reversed" ? "rotate(180deg)" : "none",
                    }}>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={`/imgs/${tarot.image_key}.jpg`}
                        alt={tarot.card?.card_name || "Tarot"}
                        style={{ width: "100%", height: "100%", objectFit: "cover" }}
                      />
                    </div>
                  </div>
                )}

                {/* Orientation badge */}
                <div style={{ textAlign: "center", marginBottom: 8 }}>
                  <span style={{
                    fontSize: 11, fontWeight: 600, color: P.p,
                    background: `${P.soft}50`, padding: "3px 14px", borderRadius: 20,
                  }}>
                    {tarot.orientation === "upright" ? t("celestial.upright") : t("celestial.reversed")}
                  </span>
                </div>

                {/* Card name */}
                <div style={{ textAlign: "center", marginBottom: 4 }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: T.text.primary }}>
                    {tarot.card?.card_name}
                  </div>
                  {tarot.card?.card_name_en && (
                    <div style={{ fontSize: 12, color: P.p, fontWeight: 500, marginTop: 2 }}>
                      {tarot.orientation === "upright" ? t("celestial.upright") : t("celestial.reversed")}
                    </div>
                  )}
                </div>

                {/* Description */}
                {tarot.card?.description && (
                  <div style={{
                    background: `${P.airy}`, borderRadius: 12, padding: "12px 14px",
                    margin: "12px 0", textAlign: "center",
                  }}>
                    <p style={{ fontSize: 12.5, color: T.text.secondary, lineHeight: 1.7, margin: 0 }}>
                      {tarot.card.description}
                    </p>
                  </div>
                )}

                {/* Meaning */}
                {(tarot.card?.meaning_up || tarot.card?.meaning_down) && (
                  <div style={{
                    background: "rgba(255,255,255,0.6)", borderRadius: 12, padding: "12px 14px",
                    marginBottom: 12, textAlign: "center",
                  }}>
                    <p style={{ fontSize: 12.5, color: T.text.secondary, lineHeight: 1.7, margin: 0 }}>
                      {tarot.orientation === "upright" ? tarot.card.meaning_up : tarot.card.meaning_down}
                    </p>
                  </div>
                )}

                {/* Keyword tags */}
                {tarot.card?.keywords && tarot.card.keywords.length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center", marginBottom: 8 }}>
                    {tarot.card.keywords.map((kw: string, i: number) => (
                      <span key={i} style={{
                        fontSize: 11, fontWeight: 500, color: P.p,
                        border: `1px solid ${P.soft}`,
                        padding: "4px 12px", borderRadius: 20,
                        background: "rgba(255,255,255,0.6)",
                      }}>{kw}</span>
                    ))}
                  </div>
                )}
              </CollapsibleCard>
            )}
          </>
        )}
      </div>
    </div>
  );
}
