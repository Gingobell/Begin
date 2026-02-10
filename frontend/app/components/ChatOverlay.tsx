"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { createPortal } from "react-dom";
import { useCopilotAction, useCoAgent } from "@copilotkit/react-core";
import { useCopilotChat } from "@copilotkit/react-core";
import { CopilotChat, type InputProps } from "@copilotkit/react-ui";
import { TextMessage, MessageRole } from "@copilotkit/runtime-client-gql";
import { DiarySearchChip } from "./DiarySearchChip";
import { BaziChip } from "./BaziChip";
import { TarotChip } from "./TarotChip";
import { ThinkingBubble } from "./ThinkingBubble";
import { useTranslation } from "../i18n";

function ChatInput({ inProgress, onSend }: InputProps) {
  const { t } = useTranslation();
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
          placeholder={t("chat.askPlaceholder")}
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
          title={t("chat.voiceInput")}
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
  chatType?: "fortune" | "diary";
}

export function ChatOverlay({ open, onClose, theme, initialQuestion, chatType = "fortune" }: ChatOverlayProps) {
  const { t } = useTranslation();
  const { appendMessage, reset } = useCopilotChat();
  const sentRef = useRef<string | null>(null);
  const [cachedThinking, setCachedThinking] = useState("");

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

  // Register tool-call renderer for search_fortune_knowledge
  useCopilotAction({
    name: "search_fortune_knowledge",
    available: "disabled",
    parameters: [
      { name: "query", type: "string", description: "Knowledge search query", required: true },
    ],
    render: ({ status, args }) => (
      <div style={{
        display: "inline-flex", alignItems: "center", gap: 6,
        padding: "4px 10px", borderRadius: 8,
        background: "rgba(139,92,246,0.08)", color: "#7C3AED",
        fontSize: 12, fontWeight: 500,
      }}>
        {status === "executing" ? (
          <span style={{ animation: "pulse 1.5s infinite" }}>{t("chat.searchingKnowledge")}</span>
        ) : (
          <span>{t("chat.knowledge")}: {args?.query as string ?? ""}</span>
        )}
      </div>
    ),
  });

  // Register tool-call renderer for generate_diary
  useCopilotAction({
    name: "generate_diary",
    available: "disabled",
    parameters: [],
    render: ({ status, result }) => {
      let diary: { content?: string; insight?: string } | null = null;
      if (result && typeof result === "string") {
        try { diary = JSON.parse(result); } catch { /* ignore */ }
      }
      return (
        <div style={{
          padding: "12px 14px", borderRadius: 12,
          background: "linear-gradient(135deg, rgba(255,138,106,0.08), rgba(255,107,74,0.06))",
          border: "1px solid rgba(255,138,106,0.15)",
          fontSize: 13,
        }}>
          {status === "executing" ? (
            <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#FF6B4A" }}>
              <span style={{ animation: "pulse 1.5s infinite" }}>{t("chat.generatingDiary")}</span>
            </div>
          ) : diary ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ fontWeight: 600, color: "#FF6B4A", fontSize: 12 }}>{t("chat.diaryGenerated")}</div>
              <div style={{ color: "#333", lineHeight: 1.6 }}>{diary.content}</div>
              {diary.insight && (
                <div style={{
                  marginTop: 4, padding: "8px 10px", borderRadius: 8,
                  background: "rgba(255,255,255,0.6)", fontSize: 12,
                  color: "#666", lineHeight: 1.5, fontStyle: "italic",
                }}>
                  {diary.insight}
                </div>
              )}
            </div>
          ) : (
            <span style={{ color: "#FF6B4A" }}>{t("chat.diarySaved")}</span>
          )}
        </div>
      );
    },
  });

  // Access agent state for real-time thinking updates
  const { state: agentState, running } = useCoAgent<{ thinking_buffer?: string }>({
    name: "fortune_diary",
  });

  // Cache thinking to survive intermediate empty-state snapshots
  const thinking = agentState?.thinking_buffer;
  useEffect(() => {
    if (thinking) {
      setCachedThinking(thinking);
    } else if (!running) {
      setCachedThinking("");
    }
  }, [thinking, running]);

  // Portal target: inject thinking bubble into .copilotKitMessages scroll area
  const [messagesEl, setMessagesEl] = useState<Element | null>(null);
  useEffect(() => {
    if (!open) return;
    const check = () => {
      const el = document.querySelector(".copilotKitMessagesContainer");
      if (el) setMessagesEl(el);
    };
    check();
    // Retry briefly in case CopilotChat hasn't mounted yet
    const t = setInterval(check, 200);
    return () => clearInterval(t);
  }, [open]);

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
          }}>{chatType === "diary" ? t("chat.chatToJournal") : t("chat.quickAsk")}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <button onClick={() => { reset(); sentRef.current = null; setCachedThinking(""); }} title={t("chat.newConversation")} style={{
            width: 28, height: 28, borderRadius: 9, border: "none", cursor: "pointer",
            background: "rgba(0,0,0,0.04)", fontSize: 15, color: "#6F6F6F",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>+</button>
          <button onClick={onClose} style={{
            width: 28, height: 28, borderRadius: 9, border: "none", cursor: "pointer",
            background: "rgba(0,0,0,0.04)", fontSize: 12, color: "#6F6F6F",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>✕</button>
        </div>
      </div>

      {/* Chat body */}
      <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
        <CopilotChat
          className="copilot-chat-inner"
          Input={ChatInput}
          labels={{
            title: "",
            initial: chatType === "diary"
              ? t("chat.diaryInitial")
              : t("chat.fortuneInitial"),
          }}
        />
      </div>

      {/* Portal thinking bubble into the messages scroll area */}
      {messagesEl && cachedThinking && createPortal(
        <ThinkingBubble content={cachedThinking} isActive={running} />,
        messagesEl,
      )}
    </div>
  );
}
