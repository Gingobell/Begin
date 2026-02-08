"use client";

import { useEffect, useRef } from "react";
import { useCopilotAction } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import { DiarySearchChip } from "./DiarySearchChip";
import { BaziChip } from "./BaziChip";
import { TarotChip } from "./TarotChip";

interface ChatOverlayProps {
  open: boolean;
  onClose: () => void;
  theme: { p: string; s: string; soft: string; airy: string };
  initialQuestion?: string | null;
}

export function ChatOverlay({ open, onClose, theme, initialQuestion }: ChatOverlayProps) {
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  // Register tool-call renderer for search_diaries
  useCopilotAction({
    name: "search_diaries",
    available: "disabled",
    parameters: [
      { name: "query", type: "string", description: "Search keyword", required: true },
      { name: "max_results", type: "number", description: "Max results", required: false },
    ],
    render: ({ status, args }) => (
      <DiarySearchChip
        query={args?.query as string | undefined}
        maxResults={args?.max_results as number | undefined}
        status={status}
      />
    ),
  });

  // Register tool-call renderer for query_bazi_info
  useCopilotAction({
    name: "query_bazi_info",
    available: "disabled",
    parameters: [],
    render: ({ status }) => <BaziChip status={status} />,
  });

  // Register tool-call renderer for query_tarot_info
  useCopilotAction({
    name: "query_tarot_info",
    available: "disabled",
    parameters: [],
    render: ({ status }) => <TarotChip status={status} />,
  });

  // Auto-fill initial question into the input
  useEffect(() => {
    if (initialQuestion && open) {
      // Small delay to let CopilotChat mount
      const timer = setTimeout(() => {
        const textarea = document.querySelector('.copilotKitInput textarea') as HTMLTextAreaElement | null;
        if (textarea) {
          const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
            window.HTMLTextAreaElement.prototype, 'value'
          )?.set;
          nativeInputValueSetter?.call(textarea, initialQuestion);
          textarea.dispatchEvent(new Event('input', { bubbles: true }));
          textarea.focus();
        }
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [initialQuestion, open]);

  if (!open) return null;

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
            color: "#1E1E1E",
          }}>Quick Ask</span>
        </div>
        <button onClick={onClose} style={{
          width: 28, height: 28, borderRadius: 9, border: "none", cursor: "pointer",
          background: "rgba(0,0,0,0.04)", fontSize: 12, color: "#6F6F6F",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>✕</button>
      </div>

      {/* Chat body */}
      <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        <CopilotChat
          className="copilot-chat-inner"
          labels={{
            title: "",
            initial: "Ask me about your fortune, diary entries, or anything on your mind.",
            placeholder: "Ask something...",
          }}
        />
      </div>
    </div>
  );
}
