"use client";

import { useCopilotAction } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import { DiarySearchChip } from "./components/DiarySearchChip";

export default function Home() {
  // ── Register tool-call renderer for search_diaries ──────────────
  // "available: disabled" means this action can NOT be triggered from
  // the frontend — it only exists to render the card when the backend
  // agent calls the tool.
  useCopilotAction({
    name: "search_diaries",
    available: "disabled",
    parameters: [
      {
        name: "query",
        type: "string",
        description: "搜索关键词",
        required: true,
      },
      {
        name: "max_results",
        type: "number",
        description: "最大返回数量",
        required: false,
      },
    ],
    render: ({ status, args }) => {
      return (
        <DiarySearchChip
          query={args?.query as string | undefined}
          maxResults={args?.max_results as number | undefined}
          status={status}
        />
      );
    },
  });

  return (
    <div className="chat-shell">
      {/* Header */}
      <header className="chat-header">
        <div className="flex items-center gap-2.5">
          <div className="header-mark" />
          <h1 className="text-[15px] font-semibold tracking-tight" style={{ fontFamily: "'Noto Serif SC', serif" }}>
            Begin
          </h1>
        </div>
        <span className="text-[12px]" style={{ color: "var(--color-text-secondary)" }}>
          你的日记伙伴
        </span>
      </header>

      {/* Chat — CopilotChat handles messages, streaming, input */}
      <div className="chat-body">
        <CopilotChat
          className="copilot-chat-inner"
          labels={{
            title: "",
            initial: "👋 有什么想聊的？可以问我关于你的日记、今天的运势，或者随便聊聊。",
            placeholder: "写点什么吧...",
          }}
        />
      </div>
    </div>
  );
}
