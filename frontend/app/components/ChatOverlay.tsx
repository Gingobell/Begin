"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useCopilotAction, useCoAgentStateRender } from "@copilotkit/react-core";
import { useCopilotChat } from "@copilotkit/react-core";
import { CopilotChat, type InputProps } from "@copilotkit/react-ui";
import { TextMessage, MessageRole } from "@copilotkit/runtime-client-gql";
import { DiarySearchChip } from "./DiarySearchChip";
import { BaziChip } from "./BaziChip";
import { TarotChip } from "./TarotChip";
import { ThinkingBubble } from "./ThinkingBubble";

function ChatInput({ inProgress, onSend }: InputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || inProgress) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  }, [value, inProgress, onSend]);

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  };

  return (
    <div style={{
      display: "flex", alignItems: "flex-end", gap: 6,
      padding: "10px 14px 14px",
    }}>
      <div style={{
        flex: 1, display: "flex", alignItems: "flex-end", gap: 8,
        background: "rgba(255,255,255,0.6)", backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
        border: "1px solid rgba(0,0,0,0.06)", borderRadius: 22,
        padding: "8px 12px",
        transition: "border-color .2s, box-shadow .2s",
      }}>
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleInput}
          onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
          placeholder="Ask something..."
          disabled={inProgress}
          rows={1}
          style={{
            flex: 1, border: "none", outline: "none", background: "transparent",
            resize: "none", fontSize: 13.5, lineHeight: "1.5",
            fontFamily: "'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif",
            color: "#1E1E1E", padding: "2px 0", maxHeight: 120,
            scrollbarWidth: "none", msOverflowStyle: "none",
          }}
        />
        {/* Voice button */}
        <button
          type="button"
          style={{
            width: 28, height: 28, flexShrink: 0, border: "none", background: "transparent",
            cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
            color: inProgress ? "#ccc" : "#999", transition: "color .15s",
          }}
          title="Voice input"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="9" y="1" width="6" height="12" rx="3" />
            <path d="M5 10a7 7 0 0 0 14 0" />
            <line x1="12" y1="17" x2="12" y2="22" />
          </svg>
        </button>
        {/* Send button */}
        <button
          type="button"
          onClick={handleSend}
          disabled={!value.trim() || inProgress}
          style={{
            width: 28, height: 28, flexShrink: 0, border: "none", borderRadius: 14,
            cursor: value.trim() && !inProgress ? "pointer" : "default",
            background: value.trim() && !inProgress ? "linear-gradient(135deg, #FF8A6A, #FF6B4A)" : "rgba(0,0,0,0.06)",
            color: value.trim() && !inProgress ? "#fff" : "#ccc",
            display: "flex", alignItems: "center", justifyContent: "center",
            transition: "all .2s",
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="19" x2="12" y2="5" />
            <polyline points="5 12 12 5 19 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}

interface ChatOverlayProps {
  open: boolean;
  onClose: () => void;
  theme: { p: string; s: string; soft: string; airy: string };
  initialQuestion?: string | null;
}

export function ChatOverlay({ open, onClose, theme, initialQuestion }: ChatOverlayProps) {
  const { appendMessage } = useCopilotChat();
  const sentRef = useRef<string | null>(null);

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

  // Render thinking process from agent state
  useCoAgentStateRender({
    name: "fortune_diary",
    render: ({ status, state }) => {
      const thinking = (state as Record<string, unknown>)?.thinking_buffer as string | undefined;
      if (!thinking) return null;
      return <ThinkingBubble content={thinking} isActive={status === "inProgress"} />;
    },
  });

  // Directly send initial question as a message
  useEffect(() => {
    if (initialQuestion && open && sentRef.current !== initialQuestion) {
      sentRef.current = initialQuestion;
      appendMessage(new TextMessage({ role: MessageRole.User, content: initialQuestion }));
    }
  }, [initialQuestion, open, appendMessage]);

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
      <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
        <CopilotChat
          className="copilot-chat-inner"
          Input={ChatInput}
          labels={{
            title: "",
            initial: "Ask me about your fortune, diary entries, or anything on your mind.",
          }}
        />
      </div>
    </div>
  );
}
