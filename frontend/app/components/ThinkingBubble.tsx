"use client";

import { useState } from "react";
import { Streamdown } from "streamdown";

interface ThinkingBubbleProps {
  content: string;
  isActive: boolean;
}

export function ThinkingBubble({ content, isActive }: ThinkingBubbleProps) {
  const [expanded, setExpanded] = useState(false);

  if (!content) return null;

  return (
    <div className="animate-chip-enter my-1">
      <div
        className={`
          relative overflow-hidden rounded-2xl
          transition-all duration-500 ease-out
          ${isActive
            ? "border border-amber-300/60 bg-amber-50/70"
            : "border border-amber-200/40 bg-amber-50/50"
          }
        `}
      >
        {isActive && (
          <div className="absolute inset-0 shimmer-block pointer-events-none" />
        )}

        {/* Header — always visible, clickable to toggle */}
        <button
          onClick={() => setExpanded((v) => !v)}
          className="relative flex items-center gap-2.5 px-3 py-2 w-full text-left"
        >
          {/* Icon */}
          <div
            className={`
              flex-shrink-0 flex items-center justify-center
              w-6 h-6 rounded-full
              transition-all duration-500
              ${isActive
                ? "bg-amber-400/15 text-amber-600"
                : "bg-amber-500/10 text-amber-500"
              }
            `}
          >
            {isActive ? (
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none" className="thinking-pulse">
                <circle cx="8" cy="8" r="3" fill="currentColor" opacity="0.3" />
                <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.2" strokeDasharray="4 3" />
              </svg>
            ) : (
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.3" />
                <circle cx="8" cy="8" r="2.5" fill="currentColor" opacity="0.25" />
                <path d="M8 2v2M8 12v2M2 8h2M12 8h2" stroke="currentColor" strokeWidth="1" strokeLinecap="round" />
              </svg>
            )}
          </div>

          {/* Label */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5">
              <span
                className="text-[12px] font-medium"
                style={{ color: isActive ? "#d97706" : "#b45309" }}
              >
                {isActive ? "思考中" : "思考过程"}
              </span>

              {isActive && (
                <span className="flex gap-0.5">
                  {[0, 1, 2].map((i) => (
                    <span
                      key={i}
                      className="pulse-dot inline-block w-0.5 h-0.5 rounded-full bg-amber-400"
                    />
                  ))}
                </span>
              )}
            </div>

            {!expanded && (
              <div className="text-[11px] mt-0.5 truncate prose prose-sm max-w-none" style={{ color: "#8c7e6f" }}>
                <Streamdown>{content.slice(0, 60) + (content.length > 60 ? "..." : "")}</Streamdown>
              </div>
            )}
          </div>

          {/* Expand/collapse chevron */}
          <div className="flex-shrink-0">
            <svg
              width="12"
              height="12"
              viewBox="0 0 14 14"
              fill="none"
              className={`transition-transform duration-300 ${expanded ? "rotate-180" : ""}`}
            >
              <path
                d="M3.5 5.25L7 8.75L10.5 5.25"
                stroke="#8c7e6f"
                strokeWidth="1.3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
        </button>

        {/* Expanded content */}
        {expanded && (
          <div className="relative px-3 pb-2 pt-0">
            <div className="border-t border-amber-200/40 pt-2">
              <div className="thinking-content text-[11px] leading-relaxed break-words prose prose-sm max-w-none" style={{ color: "#5c5347" }}>
                <Streamdown>{content}</Streamdown>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
