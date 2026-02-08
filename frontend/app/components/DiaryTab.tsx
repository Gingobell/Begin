"use client";

import { useState, useEffect, useCallback } from "react";
import { getDiaries, createDiary } from "../lib/api";
import { T } from "../lib/theme";

// ── Types ────────────────────────────────────────────────────────
interface DiaryEntry {
  id: string;
  day?: string;
  weekday?: string;
  time?: string;
  mood?: number;
  mood_label?: string;
  title?: string;
  content: string;
  tags?: string[];
  insight?: string;
  created_at?: string;
}

const MOOD_EMOJIS: Record<number, string> = { 1: "😞", 2: "😕", 3: "😐", 4: "🙂", 5: "😄" };
const MOOD_LABELS: Record<number, string> = { 1: "Awful", 2: "Bad", 3: "Okay", 4: "Good", 5: "Great" };

// ── DiaryTab ─────────────────────────────────────────────────────
export function DiaryTab({ onCountChange }: { onCountChange?: (count: number) => void }) {
  const [diaries, setDiaries] = useState<DiaryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCompose, setShowCompose] = useState(false);
  const [content, setContent] = useState("");
  const [mood, setMood] = useState(3);
  const [submitting, setSubmitting] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const fetchDiaries = useCallback(async () => {
    try {
      const data = await getDiaries();
      setDiaries(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDiaries();
  }, [fetchDiaries]);

  useEffect(() => {
    onCountChange?.(diaries.length);
  }, [diaries.length, onCountChange]);

  const handleSubmit = async () => {
    if (!content.trim()) return;
    setSubmitting(true);
    setError("");
    try {
      await createDiary(content, [`mood_${mood}`]);
      setContent("");
      setMood(3);
      setShowCompose(false);
      await fetchDiaries();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Header bar */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <div>
          <h2 style={{ fontFamily: "'Fraunces',serif", fontSize: 22, fontWeight: 500, color: T.text.primary, margin: 0 }}>
            Diary
          </h2>
          <p style={{ fontSize: 12, color: T.text.quaternary, marginTop: 2 }}>
            {diaries.length} {diaries.length === 1 ? "entry" : "entries"}
          </p>
        </div>
        <button onClick={() => setShowCompose(!showCompose)} style={{
          padding: "8px 20px", borderRadius: 100, border: "none", cursor: "pointer",
          fontSize: 13, fontWeight: 600, fontFamily: "inherit",
          color: showCompose ? T.text.tertiary : "#fff",
          background: showCompose ? "rgba(0,0,0,0.04)" : `linear-gradient(135deg,${T.purple.s},${T.purple.p})`,
          boxShadow: showCompose ? "none" : `0 3px 14px ${T.purple.p}25`,
          transition: "all 0.3s cubic-bezier(0.2,0.8,0.2,1)",
        }}>
          {showCompose ? "Cancel" : "New Entry"}
        </button>
      </div>

      {error && (
        <div style={{ padding: "8px 14px", borderRadius: 12, background: "#fee2e2", fontSize: 12, color: "#dc2626" }}>
          {error}
        </div>
      )}

      {/* Compose card */}
      {showCompose && (
        <div className="animate-fade-up" style={{
          padding: "20px 22px", borderRadius: 22,
          background: "rgba(255,255,255,0.65)", border: "1px solid rgba(255,255,255,0.5)",
          backdropFilter: "blur(20px)", WebkitBackdropFilter: "blur(20px)",
          boxShadow: "0 4px 16px rgba(0,0,0,0.03)",
        }}>
          {/* Mood selector */}
          <div style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 14 }}>
            <span style={{ fontSize: 12, color: T.text.tertiary, marginRight: 4 }}>Mood:</span>
            {[1, 2, 3, 4, 5].map(m => (
              <button key={m} onClick={() => setMood(m)} style={{
                width: 36, height: 36, borderRadius: "50%", border: "none", cursor: "pointer",
                fontSize: 18, display: "flex", alignItems: "center", justifyContent: "center",
                background: mood === m ? `${T.purple.airy}` : "transparent",
                boxShadow: mood === m ? `0 0 0 2px ${T.purple.p}40` : "none",
                opacity: mood === m ? 1 : 0.4, transition: "all 0.2s",
                transform: mood === m ? "scale(1.1)" : "scale(1)",
              }}>
                {MOOD_EMOJIS[m]}
              </button>
            ))}
            <span style={{ fontSize: 11, color: T.text.quaternary, marginLeft: 6 }}>{MOOD_LABELS[mood]}</span>
          </div>

          {/* Textarea */}
          <textarea
            value={content}
            onChange={e => setContent(e.target.value)}
            placeholder="What happened today? Write down your thoughts..."
            rows={5}
            style={{
              width: "100%", padding: "14px 16px", borderRadius: 16,
              border: "1px solid rgba(0,0,0,0.05)", background: "rgba(255,255,255,0.5)",
              fontSize: 13.5, fontFamily: "inherit", color: T.text.primary,
              resize: "none", outline: "none", lineHeight: 1.7,
              transition: "border-color 0.2s",
            }}
          />

          {/* Actions */}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 12 }}>
            <button onClick={() => { setShowCompose(false); setContent(""); }} style={{
              padding: "9px 20px", borderRadius: 12, border: "none", cursor: "pointer",
              fontSize: 13, fontFamily: "inherit", fontWeight: 500,
              background: "rgba(0,0,0,0.04)", color: T.text.tertiary,
            }}>Cancel</button>
            <button onClick={handleSubmit} disabled={submitting || !content.trim()} style={{
              padding: "9px 24px", borderRadius: 12, border: "none", cursor: "pointer",
              fontSize: 13, fontFamily: "inherit", fontWeight: 600, color: "#fff",
              background: `linear-gradient(135deg,${T.purple.s},${T.purple.p})`,
              opacity: (submitting || !content.trim()) ? 0.5 : 1,
              transition: "opacity 0.2s",
            }}>
              {submitting ? "Saving..." : "Save"}
            </button>
          </div>
        </div>
      )}

      {/* Diary grid */}
      <div style={{ flex: 1, overflowY: "auto", padding: "0 0 40px" }}>
        {loading ? (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="shimmer-block" style={{ height: 120, borderRadius: 20 }} />
            ))}
          </div>
        ) : diaries.length === 0 ? (
          <div style={{
            display: "flex", flexDirection: "column", alignItems: "center",
            justifyContent: "center", gap: 12, paddingTop: 80,
          }}>
            <div style={{
              width: 64, height: 64, borderRadius: "50%",
              background: T.purple.airy, display: "flex", alignItems: "center",
              justifyContent: "center", fontSize: 28,
            }}>📝</div>
            <p style={{ fontSize: 13, color: T.text.tertiary }}>No entries yet. Write your first one.</p>
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            {diaries.map(d => (
              <div key={d.id} onClick={() => setExpandedId(d.id)} style={{
                padding: "18px 20px", borderRadius: 20, cursor: "pointer",
                background: "rgba(255,255,255,0.6)", border: "1px solid rgba(255,255,255,0.5)",
                backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)",
                boxShadow: "0 2px 12px rgba(0,0,0,0.02)",
                transition: "all 0.3s cubic-bezier(0.2,0.8,0.2,1)",
                display: "flex", flexDirection: "column", gap: 8,
                minHeight: 110,
              }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.transform = "translateY(-2px)"; (e.currentTarget as HTMLElement).style.boxShadow = "0 6px 20px rgba(0,0,0,0.05)"; }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.transform = "translateY(0)"; (e.currentTarget as HTMLElement).style.boxShadow = "0 2px 12px rgba(0,0,0,0.02)"; }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span style={{ fontSize: 22 }}>{d.mood ? (MOOD_EMOJIS[d.mood] || "😐") : "📝"}</span>
                  <span style={{ fontSize: 10, color: T.text.quaternary }}>
                    {d.weekday && d.day ? `${d.weekday} ${d.day}` : ""}
                  </span>
                </div>
                <p style={{
                  fontSize: 13.5, fontWeight: 500, color: T.text.primary, lineHeight: 1.4, margin: 0,
                  overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical",
                } as any}>
                  {d.title || d.content.slice(0, 60)}
                </p>
                {d.tags && d.tags.length > 0 && (
                  <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginTop: "auto" }}>
                    {d.tags.slice(0, 2).map((tag, i) => (
                      <span key={i} style={{
                        padding: "2px 8px", borderRadius: 100, fontSize: 9, fontWeight: 500,
                        background: T.purple.airy, color: T.purple.p,
                      }}>{tag}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Detail modal */}
      {expandedId && (() => {
        const d = diaries.find(x => x.id === expandedId);
        if (!d) return null;
        return (
          <div style={{
            position: "fixed", inset: 0, zIndex: 200, background: "rgba(0,0,0,0.10)",
            backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)",
            display: "flex", alignItems: "center", justifyContent: "center", padding: 24,
          }} onClick={e => { if (e.target === e.currentTarget) setExpandedId(null); }}>
            <div className="animate-fade-up" style={{
              background: "rgba(255,255,255,0.92)", border: "1px solid rgba(255,255,255,0.6)",
              borderRadius: 26, maxWidth: 520, width: "100%", maxHeight: "80vh",
              overflow: "auto", padding: "28px 30px",
              boxShadow: "0 12px 40px rgba(0,0,0,0.08)",
            }}>
              {/* Modal header */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontSize: 26 }}>{d.mood ? (MOOD_EMOJIS[d.mood] || "😐") : "📝"}</span>
                  <div>
                    <p style={{ fontFamily: "'Fraunces',serif", fontSize: 18, fontWeight: 500, color: T.text.primary, margin: 0 }}>
                      {d.title || "Diary Entry"}
                    </p>
                    <p style={{ fontSize: 11, color: T.text.quaternary, marginTop: 3 }}>
                      {d.weekday && d.day ? `${d.weekday} ${d.day}` : ""}
                      {d.time ? ` · ${d.time}` : ""}
                      {d.mood_label ? ` · ${d.mood_label}` : ""}
                    </p>
                  </div>
                </div>
                <button onClick={() => setExpandedId(null)} style={{
                  width: 30, height: 30, borderRadius: 10, border: "none", cursor: "pointer",
                  background: "rgba(0,0,0,0.04)", fontSize: 13, color: T.text.tertiary,
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>✕</button>
              </div>

              {/* Tags */}
              {d.tags && d.tags.length > 0 && (
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 14 }}>
                  {d.tags.map((tag, i) => (
                    <span key={i} style={{
                      padding: "3px 12px", borderRadius: 100, fontSize: 11, fontWeight: 500,
                      background: T.purple.airy, color: T.purple.p,
                    }}>{tag}</span>
                  ))}
                </div>
              )}

              {/* Content */}
              <p style={{ fontSize: 14, color: T.text.secondary, lineHeight: 1.8, whiteSpace: "pre-wrap", marginBottom: 0 }}>
                {d.content}
              </p>

              {/* AI Insight with blue left border */}
              {d.insight && (
                <div style={{
                  marginTop: 18, padding: "14px 18px", borderRadius: 16,
                  background: T.blue.airy,
                  borderLeft: `3px solid ${T.blue.p}`,
                }}>
                  <p style={{ fontSize: 11, fontWeight: 700, color: T.blue.p, marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                    ✨ AI Insight
                  </p>
                  <p style={{ fontSize: 12.5, color: T.text.secondary, lineHeight: 1.7, margin: 0 }}>
                    {d.insight}
                  </p>
                </div>
              )}
            </div>
          </div>
        );
      })()}
    </div>
  );
}
