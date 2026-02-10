"use client";

import { useState } from "react";
import { Streamdown } from "streamdown";
import { useTranslation } from "../i18n";

interface ThinkingBubbleProps {
  content: string;
  isActive: boolean;
}

export function ThinkingBubble({ content, isActive }: ThinkingBubbleProps) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  if (!content) return null;

  return (
    <div className="animate-chip-enter" style={{ padding: "4px 2px", maxWidth: "92%" }}>
      {/* Header row — clickable to toggle */}
      <button
        onClick={() => setExpanded((v) => !v)}
        style={{
          display: "flex", alignItems: "center", gap: 6,
          background: "none", border: "none", cursor: "pointer",
          padding: 0, width: "100%", textAlign: "left",
        }}
      >
        {/* Right arrow that rotates 90° when expanded */}
        <svg
          width="10"
          height="10"
          viewBox="0 0 10 10"
          fill="none"
          style={{
            flexShrink: 0,
            transition: "transform .2s ease",
            transform: expanded ? "rotate(90deg)" : "rotate(0deg)",
          }}
        >
          <path
            d="M3 1.5L7 5L3 8.5"
            stroke="#999"
            strokeWidth="1.3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>

        {/* Label */}
        <span style={{
          fontSize: 12, fontWeight: 500, color: "#999",
          fontFamily: "'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif",
        }}>
          {isActive ? t("thinking.thinking") : t("thinking.thoughtProcess")}
        </span>

        {isActive && (
          <span className="flex gap-0.5" style={{ display: "inline-flex", gap: 2, marginLeft: 2 }}>
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="pulse-dot"
                style={{
                  display: "inline-block", width: 3, height: 3,
                  borderRadius: "50%", background: "#bbb",
                }}
              />
            ))}
          </span>
        )}

        {/* Preview text when collapsed */}
        {!expanded && (
          <span style={{
            fontSize: 11, color: "#bbb", marginLeft: 4,
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
            flex: 1, minWidth: 0,
            fontFamily: "'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif",
          }}>
            {content.slice(0, 50) + (content.length > 50 ? "..." : "")}
          </span>
        )}
      </button>

      {/* Expanded content */}
      {expanded && (
        <div style={{ paddingLeft: 16, paddingTop: 4 }}>
          <div className="thinking-content" style={{
            fontSize: 11, lineHeight: 1.6, color: "#999",
          }}>
            <Streamdown>{content}</Streamdown>
          </div>
        </div>
      )}
    </div>
  );
}
