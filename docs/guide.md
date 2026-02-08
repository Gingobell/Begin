# Gemini 3 Flash Thinking → AG-UI → CopilotKit: Implementation Guide

> For `supa-langgraph-rag-scaffold`. Streams Gemini's thought process through AG-UI events to a CopilotKit React frontend — thinking blocks rendered mid-tool-calls, just like Claude Desktop.

---

## 1. Dependencies

### Backend (`pyproject.toml` additions)

```toml
dependencies = [
    # ... existing deps ...

    # AG-UI Protocol
    "ag-ui-protocol>=0.1.8",
    "ag-ui-langgraph>=0.1.0",

    # Gemini SDK (direct, not langchain wrapper)
    "google-genai>=1.0.0",

    # SSE streaming
    "sse-starlette>=2.0.0",
]
```

### Frontend (new Next.js app or add to existing)

```bash
npm install @copilotkit/react-core @copilotkit/react-ui @copilotkit/runtime @ag-ui/client
```

### Environment (`.env`)

```env
GEMINI_API_KEY=your-key
CHAT_MODEL=gemini-3-flash-preview
# Keep your existing SUPABASE_URL, SUPABASE_KEY, etc.
```

---

## 2. Backend: State Update

### `app/graph/state.py`

Extend your state to carry thinking content for streaming:

```python
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """Agent state — extends existing with thinking support."""
    question: str
    context: str
    messages: list[BaseMessage]
    retry_count: int
    grade: str
    user_id: str
    # NEW: track thinking for AG-UI emission
    thinking_buffer: str          # accumulated thinking text
    current_node: str             # which node is active (for step events)
```

---

## 3. Backend: AG-UI SSE Endpoint

### `app/agui_endpoint.py` — THE CORE FILE

This is the complete endpoint that:
- Runs your existing LangGraph workflow
- Calls Gemini 3 Flash with `include_thoughts=True`
- Emits AG-UI Thinking events interleaved with tool calls and text

```python
"""
AG-UI SSE Endpoint — Gemini 3 Flash Thinking + LangGraph RAG
=============================================================
Bridges Gemini's part.thought → AG-UI ThinkingTextMessageContentEvent
"""
from __future__ import annotations

import uuid
import json
import logging
import traceback
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from google import genai
from google.genai import types as genai_types

from ag_ui.core import (
    RunAgentInput,
    EventType,
    RunStartedEvent,
    RunFinishedEvent,
    RunErrorEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    ToolCallStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    StepStartedEvent,
    StepFinishedEvent,
)
from ag_ui.core.events import (
    ThinkingStartEvent,
    ThinkingTextMessageStartEvent,
    ThinkingTextMessageContentEvent,
    ThinkingTextMessageEndEvent,
    ThinkingEndEvent,
)
from ag_ui.encoder import EventEncoder

from app.config import config
from app.graph.workflow import app as langgraph_app
from app.services.supabase_ops import supabase_ops
from app.core.gemini_embeddings import GeminiEmbeddings

logger = logging.getLogger(__name__)

# ── Gemini client (direct SDK, NOT langchain wrapper) ──
gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)

# ── Embeddings (reuse existing) ──
_emb = GeminiEmbeddings(
    model=config.EMBEDDING_MODEL,
    output_dimensionality=config.EMBEDDING_DIM,
)


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

class ThinkingStateTracker:
    """
    Tracks thinking/answer phase transitions.
    Prevents duplicate Start/End events (the #1 source of AG-UI errors).
    """
    def __init__(self, encoder: EventEncoder):
        self.encoder = encoder
        self.in_thinking = False
        self.in_answer = False
        self.thinking_msg_id = str(uuid.uuid4())
        self.answer_msg_id = str(uuid.uuid4())

    def open_thinking(self) -> list[str]:
        """Open thinking phase. Close answer if open. Returns encoded events."""
        events = []
        if self.in_answer:
            events.extend(self.close_answer())
        if not self.in_thinking:
            self.thinking_msg_id = str(uuid.uuid4())
            events.append(self.encoder.encode(ThinkingStartEvent(
                type=EventType.THINKING_START,
            )))
            events.append(self.encoder.encode(ThinkingTextMessageStartEvent(
                type=EventType.THINKING_TEXT_MESSAGE_START,
                message_id=self.thinking_msg_id,
            )))
            self.in_thinking = True
        return events

    def emit_thinking(self, delta: str) -> list[str]:
        """Emit thinking content. MUST filter empty strings before calling."""
        if not delta:  # guard against empty delta (causes ValidationError)
            return []
        events = self.open_thinking()
        events.append(self.encoder.encode(ThinkingTextMessageContentEvent(
            type=EventType.THINKING_TEXT_MESSAGE_CONTENT,
            message_id=self.thinking_msg_id,
            delta=delta,
        )))
        return events

    def close_thinking(self) -> list[str]:
        """Close thinking phase."""
        events = []
        if self.in_thinking:
            events.append(self.encoder.encode(ThinkingTextMessageEndEvent(
                type=EventType.THINKING_TEXT_MESSAGE_END,
                message_id=self.thinking_msg_id,
            )))
            events.append(self.encoder.encode(ThinkingEndEvent(
                type=EventType.THINKING_END,
            )))
            self.in_thinking = False
        return events

    def open_answer(self) -> list[str]:
        """Open answer phase. Close thinking if open."""
        events = []
        if self.in_thinking:
            events.extend(self.close_thinking())
        if not self.in_answer:
            self.answer_msg_id = str(uuid.uuid4())
            events.append(self.encoder.encode(TextMessageStartEvent(
                type=EventType.TEXT_MESSAGE_START,
                message_id=self.answer_msg_id,
                role="assistant",
            )))
            self.in_answer = True
        return events

    def emit_answer(self, delta: str) -> list[str]:
        """Emit answer content."""
        if not delta:
            return []
        events = self.open_answer()
        events.append(self.encoder.encode(TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id=self.answer_msg_id,
            delta=delta,
        )))
        return events

    def close_answer(self) -> list[str]:
        """Close answer phase."""
        events = []
        if self.in_answer:
            events.append(self.encoder.encode(TextMessageEndEvent(
                type=EventType.TEXT_MESSAGE_END,
                message_id=self.answer_msg_id,
            )))
            self.in_answer = False
        return events

    def close_all(self) -> list[str]:
        """Close whatever is open. Call at the end."""
        events = []
        events.extend(self.close_thinking())
        events.extend(self.close_answer())
        return events


def gemini_stream_with_thinking(
    prompt: str,
    system_instruction: str | None = None,
    thinking_level: str = "high",
):
    """
    Call Gemini 3 Flash with thinking enabled, yield (is_thought, text) tuples.

    thinking_level: "minimal" | "low" | "medium" | "high"
    """
    gen_config = genai_types.GenerateContentConfig(
        thinking_config=genai_types.ThinkingConfig(
            include_thoughts=True,
            thinking_level=thinking_level,
        ),
        system_instruction=system_instruction,
    )

    for chunk in gemini_client.models.generate_content_stream(
        model=config.CHAT_MODEL,  # "gemini-3-flash-preview"
        contents=prompt,
        config=gen_config,
    ):
        if not chunk.candidates:
            continue
        for part in chunk.candidates[0].content.parts:
            if not part.text:
                continue
            yield (bool(part.thought), part.text)


# ═══════════════════════════════════════════════════════════
# RAG PIPELINE WITH THINKING
# ═══════════════════════════════════════════════════════════

async def rag_with_thinking(
    question: str,
    encoder: EventEncoder,
    tracker: ThinkingStateTracker,
) -> AsyncGenerator[str, None]:
    """
    Full RAG pipeline emitting AG-UI events with thinking.

    Flow:
      1. ThinkingStart → "Planning retrieval..."
      2. StepStart("retrieve") → retrieve → StepEnd
      3. ThinkingStart → "Evaluating relevance..."
      4. StepStart("grade") → grade → StepEnd
      5. (optional) StepStart("rewrite") → rewrite → back to 2
      6. ThinkingStart → "Synthesizing answer..."
      7. TextMessageStart → final answer stream → TextMessageEnd
    """

    # ── Step 1: Retrieval ──
    yield encoder.encode(StepStartedEvent(
        type=EventType.STEP_STARTED,
        step_name="retrieve",
    ))

    # Thinking: plan retrieval
    for ev in tracker.emit_thinking(f"Searching knowledge base for: \"{question}\"..."):
        yield ev

    vec = _emb.embed_query(question)
    results = supabase_ops.retrieve_context_mesh(question, vec)
    context = "\n\n".join([r.get("content", "") for r in results])

    yield encoder.encode(StepFinishedEvent(
        type=EventType.STEP_FINISHED,
        step_name="retrieve",
    ))

    # ── Step 2: Grade with thinking ──
    yield encoder.encode(StepStartedEvent(
        type=EventType.STEP_STARTED,
        step_name="grade",
    ))

    for ev in tracker.emit_thinking(f"Retrieved {len(results)} documents. Evaluating relevance..."):
        yield ev

    grade_prompt = (
        f"Does this context help answer the question? Reply ONLY 'yes' or 'no'.\n\n"
        f"Context: {context[:2000]}\n\nQuestion: {question}"
    )
    grade_result = ""
    for is_thought, text in gemini_stream_with_thinking(grade_prompt, thinking_level="low"):
        if is_thought:
            for ev in tracker.emit_thinking(text):
                yield ev
        else:
            grade_result += text

    is_relevant = "yes" in grade_result.lower()

    yield encoder.encode(StepFinishedEvent(
        type=EventType.STEP_FINISHED,
        step_name="grade",
    ))

    # ── Step 3: Rewrite loop (if needed) ──
    retry_count = 0
    max_retries = config.MAX_RETRY

    while not is_relevant and retry_count < max_retries:
        retry_count += 1

        yield encoder.encode(StepStartedEvent(
            type=EventType.STEP_STARTED,
            step_name=f"rewrite_{retry_count}",
        ))

        for ev in tracker.emit_thinking(
            f"Context not relevant enough. Rewriting query (attempt {retry_count}/{max_retries})..."
        ):
            yield ev

        rewrite_prompt = f"Rewrite this search query for better results: {question}"
        new_question = ""
        for is_thought, text in gemini_stream_with_thinking(rewrite_prompt, thinking_level="low"):
            if is_thought:
                for ev in tracker.emit_thinking(text):
                    yield ev
            else:
                new_question += text

        question = new_question.strip()

        yield encoder.encode(StepFinishedEvent(
            type=EventType.STEP_FINISHED,
            step_name=f"rewrite_{retry_count}",
        ))

        # Re-retrieve
        yield encoder.encode(StepStartedEvent(
            type=EventType.STEP_STARTED,
            step_name=f"retrieve_{retry_count + 1}",
        ))

        for ev in tracker.emit_thinking(f"Re-searching with: \"{question}\"..."):
            yield ev

        vec = _emb.embed_query(question)
        results = supabase_ops.retrieve_context_mesh(question, vec)
        context = "\n\n".join([r.get("content", "") for r in results])

        yield encoder.encode(StepFinishedEvent(
            type=EventType.STEP_FINISHED,
            step_name=f"retrieve_{retry_count + 1}",
        ))

        # Re-grade
        grade_result = ""
        for is_thought, text in gemini_stream_with_thinking(
            f"Does this context help? 'yes' or 'no'.\nContext: {context[:2000]}\nQuestion: {question}",
            thinking_level="minimal",
        ):
            if not is_thought:
                grade_result += text

        is_relevant = "yes" in grade_result.lower()

    # ── Step 4: Generate final answer with full thinking ──
    yield encoder.encode(StepStartedEvent(
        type=EventType.STEP_STARTED,
        step_name="generate",
    ))

    gen_prompt = (
        f"Answer based on context. If context doesn't help, say so.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}"
    )

    system = (
        "You are a knowledgeable RAG assistant. Answer precisely based on "
        "the provided context. Cite specific parts of the context when possible."
    )

    for is_thought, text in gemini_stream_with_thinking(
        gen_prompt,
        system_instruction=system,
        thinking_level="high",
    ):
        if is_thought:
            for ev in tracker.emit_thinking(text):
                yield ev
        else:
            for ev in tracker.emit_answer(text):
                yield ev

    yield encoder.encode(StepFinishedEvent(
        type=EventType.STEP_FINISHED,
        step_name="generate",
    ))


# ═══════════════════════════════════════════════════════════
# FASTAPI ENDPOINT
# ═══════════════════════════════════════════════════════════

def register_agui_endpoint(app: FastAPI):
    """Register the AG-UI SSE endpoint on an existing FastAPI app."""

    @app.post("/agui")
    async def agui_handler(input_data: RunAgentInput):
        async def event_generator():
            encoder = EventEncoder()
            tracker = ThinkingStateTracker(encoder)

            # ── Run Started ──
            yield encoder.encode(RunStartedEvent(
                type=EventType.RUN_STARTED,
                thread_id=input_data.thread_id,
                run_id=input_data.run_id,
            ))

            try:
                # Extract user question from AG-UI messages
                user_messages = [
                    m for m in input_data.messages if m.role == "user"
                ]
                if not user_messages:
                    for ev in tracker.emit_answer("No question provided."):
                        yield ev
                else:
                    question = user_messages[-1].content
                    if isinstance(question, list):
                        # Handle multimodal content
                        question = " ".join(
                            p.text for p in question
                            if hasattr(p, "text") and p.text
                        )

                    # Run RAG pipeline with thinking
                    async for event in rag_with_thinking(
                        question=question,
                        encoder=encoder,
                        tracker=tracker,
                    ):
                        yield event

            except Exception as e:
                logger.error(f"Agent error: {e}\n{traceback.format_exc()}")

                # Close any open phases
                for ev in tracker.close_all():
                    yield ev

                # Emit error
                yield encoder.encode(RunErrorEvent(
                    type=EventType.RUN_ERROR,
                    message=str(e),
                ))
                return

            # ── Cleanup & Run Finished ──
            for ev in tracker.close_all():
                yield ev

            yield encoder.encode(RunFinishedEvent(
                type=EventType.RUN_FINISHED,
                thread_id=input_data.thread_id,
                run_id=input_data.run_id,
            ))

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # nginx: don't buffer SSE
            },
        )
```

---

## 4. Backend: Register Endpoint

### `app/main.py` — add two lines

```python
# ... existing imports and routes ...

# ── AG-UI endpoint (add near bottom, before __main__) ──
from app.agui_endpoint import register_agui_endpoint
register_agui_endpoint(app)
```

That's it. Your existing `/chat`, `/search`, `/ingest` routes stay untouched.

---

## 5. Frontend: Next.js + CopilotKit

### `app/api/copilotkit/route.ts`

```typescript
import { CopilotRuntime, HttpAgent } from "@copilotkit/runtime";
import { NextRequest } from "next/server";

export async function POST(req: NextRequest) {
  const agent = new HttpAgent({
    url: process.env.AGENT_URL || "http://localhost:8000/agui",
  });

  const runtime = new CopilotRuntime({ agents: [agent] });
  return runtime.response(req);
}
```

### `app/layout.tsx`

```tsx
import { CopilotKit } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <CopilotKit runtimeUrl="/api/copilotkit">
          {children}
        </CopilotKit>
      </body>
    </html>
  );
}
```

### `app/page.tsx` — Chat with Thinking Display

```tsx
"use client";

import { CopilotChat } from "@copilotkit/react-ui";

export default function Home() {
  return (
    <div className="h-screen flex flex-col">
      <header className="p-4 border-b bg-white">
        <h1 className="text-xl font-semibold">RAG Agent</h1>
      </header>
      <main className="flex-1 overflow-hidden">
        <CopilotChat
          className="h-full"
          labels={{
            title: "RAG Assistant",
            initial: "Ask me anything about your knowledge base.",
          }}
        />
      </main>
    </div>
  );
}
```

> **CopilotChat auto-renders ThinkingTextMessageContentEvent as a collapsible thinking block.** If it doesn't in your version, see Section 7 (Custom Thinking UI).

---

## 6. CORS

Add to `app/main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 7. Custom Thinking UI (if CopilotChat doesn't render it)

If `<CopilotChat>` doesn't show thinking blocks, use `useCoAgent` + custom rendering:

### `components/ThinkingMessage.tsx`

```tsx
"use client";

import { useState } from "react";

interface ThinkingMessageProps {
  content: string;
  isActive: boolean;
}

export function ThinkingMessage({ content, isActive }: ThinkingMessageProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`
        my-2 rounded-lg border transition-all cursor-pointer
        ${isActive
          ? "border-blue-300 bg-blue-50"
          : "border-gray-200 bg-gray-50"
        }
      `}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-center gap-2 px-3 py-2">
        {isActive ? (
          <div className="animate-spin h-4 w-4 border-2 border-blue-500 rounded-full border-t-transparent" />
        ) : (
          <span className="text-gray-400">💭</span>
        )}
        <span className="text-sm font-medium text-gray-600">
          {isActive ? "Thinking..." : "Thought process"}
        </span>
        <span className="ml-auto text-xs text-gray-400">
          {expanded ? "▲" : "▼"}
        </span>
      </div>
      {expanded && (
        <div className="px-3 pb-3 text-sm text-gray-500 whitespace-pre-wrap border-t border-gray-100 pt-2">
          {content}
        </div>
      )}
    </div>
  );
}
```

### Wire it up with `useCoAgentStateRender`

```tsx
import { useCoAgentStateRender } from "@copilotkit/react-core";
import { ThinkingMessage } from "./ThinkingMessage";

export function AgentRenderer() {
  useCoAgentStateRender({
    name: "rag_agent",
    render: ({ status, state }) => {
      if (state?.thinking_buffer) {
        return (
          <ThinkingMessage
            content={state.thinking_buffer}
            isActive={status === "inProgress"}
          />
        );
      }
      return null;
    },
  });

  return null; // renders inline in chat
}
```

---

## 8. Debug & Troubleshooting

### 8.1 — Test SSE stream directly (no frontend)

```bash
curl -X POST http://localhost:8000/agui \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "threadId": "test-1",
    "runId": "run-1",
    "messages": [{"id":"1","role":"user","content":"What is RAG?"}],
    "tools": [],
    "context": [],
    "state": {},
    "forwardedProps": {}
  }' --no-buffer
```

You should see events like:
```
data: {"type":"RUN_STARTED","threadId":"test-1","runId":"run-1"}

data: {"type":"STEP_STARTED","stepName":"retrieve"}

data: {"type":"THINKING_START"}

data: {"type":"THINKING_TEXT_MESSAGE_START","messageId":"abc-123"}

data: {"type":"THINKING_TEXT_MESSAGE_CONTENT","messageId":"abc-123","delta":"Searching knowledge base..."}

data: {"type":"THINKING_TEXT_MESSAGE_END","messageId":"abc-123"}

data: {"type":"THINKING_END"}

...

data: {"type":"TEXT_MESSAGE_START","messageId":"def-456","role":"assistant"}

data: {"type":"TEXT_MESSAGE_CONTENT","messageId":"def-456","delta":"Based on the context..."}

data: {"type":"TEXT_MESSAGE_END","messageId":"def-456"}

data: {"type":"RUN_FINISHED","threadId":"test-1","runId":"run-1"}
```

### 8.2 — Enable debug logging

```python
# In main.py or config.py
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
# Quiet noisy libs
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
```

---

## 9. Known Errors & Fixes

### ❌ `ValidationError: Delta must not be an empty string`

**Cause:** Gemini (or any model) sends an empty `part.text` as a thinking delta. AG-UI's `ThinkingTextMessageContentEvent` has strict validation.

**Fix:** Already handled in `ThinkingStateTracker.emit_thinking()` — the guard `if not delta: return []` catches it. If you're building custom, ALWAYS filter:

```python
if part.text and len(part.text) > 0:
    yield ThinkingTextMessageContentEvent(delta=part.text, ...)
```

---

### ❌ `AGUIError: Cannot send TEXT_MESSAGE_START after TEXT_MESSAGE_START`

**Cause:** You emitted `TextMessageStartEvent` twice without a `TextMessageEndEvent` in between. Same for thinking events.

**Fix:** `ThinkingStateTracker` manages this — it tracks `in_thinking` / `in_answer` booleans and auto-closes before re-opening. Never emit Start/End events manually; always go through the tracker.

---

### ❌ `400: Function call FC1 in the 1. content block is missing a thought_signature`

**Cause:** Gemini 3 requires thought signatures to be circulated in multi-turn function calling. If you call Gemini → it returns a `functionCall` with a `thought_signature` → you send back `functionResponse` WITHOUT the signature → 400.

**Fix:** If you add tool calling to the Gemini stream (beyond the current RAG pipeline), extract and circulate signatures:

```python
# When Gemini returns a function call:
for part in chunk.candidates[0].content.parts:
    if hasattr(part, 'function_call'):
        # Save the thought_signature from this part
        sig = getattr(part, 'thought_signature', None)

        # Execute tool...
        result = execute_tool(part.function_call)

        # Send back WITH the signature
        response_parts = [
            genai_types.Part(
                function_response=genai_types.FunctionResponse(
                    name=part.function_call.name,
                    response=result,
                ),
                thought_signature=sig,  # MUST include this
            )
        ]
```

**For the current RAG pipeline (no Gemini function calling), this doesn't apply.** Your tools (retrieve, grade, rewrite) are Python functions, not Gemini function calls.

---

### ❌ `thinking_budget and thinking_level are not supported together`

**Cause:** Mixed Gemini 2.5 (`thinking_budget`) and Gemini 3 (`thinking_level`) params.

**Fix:** Use ONLY `thinking_level` with Gemini 3 Flash. Never pass `thinking_budget`. If using LangChain's wrapper, ensure it's updated.

```python
# ✅ Correct for Gemini 3
thinking_config=genai_types.ThinkingConfig(
    include_thoughts=True,
    thinking_level="high",     # "minimal" | "low" | "medium" | "high"
)

# ❌ Wrong — don't mix
thinking_config=genai_types.ThinkingConfig(
    thinking_budget=8192,      # ← Gemini 2.5 only
    thinking_level="high",     # ← Gemini 3 only
)
```

---

### ❌ Thinking events not rendering in CopilotChat

**Cause:** Your CopilotKit version may not support `THINKING_*` events yet.

**Fix options:**
1. Upgrade CopilotKit: `npm install @copilotkit/react-core@latest @copilotkit/react-ui@latest`
2. Use custom rendering with `useCoAgentStateRender` (Section 7)
3. Fall back to `STATE_DELTA` — emit thinking as state, render with custom component:

```python
# Backend: emit as state instead
yield encoder.encode(StateDeltaEvent(
    type=EventType.STATE_DELTA,
    delta=[{"op": "replace", "path": "/thinking", "value": text}],
))
```

```tsx
// Frontend: read from state
const { state } = useCoAgent({ name: "rag_agent" });
// state.thinking contains the current thought
```

---

### ❌ SSE stream buffered / events arrive all at once

**Cause:** Reverse proxy (nginx, Vercel, etc.) buffering the response.

**Fix:** Headers are already set in the endpoint. Also check:

```nginx
# nginx.conf
location /agui {
    proxy_buffering off;
    proxy_cache off;
    proxy_set_header Connection '';
    chunked_transfer_encoding off;
}
```

For development, run FastAPI directly:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

### ❌ `google.genai` import error / `Client` not found

**Cause:** Wrong package. `google-generativeai` ≠ `google-genai`.

**Fix:**
```bash
# ❌ Wrong
pip install google-generativeai

# ✅ Correct (the new unified SDK)
pip install google-genai
```

---

### ❌ `RunAgentInput` validation fails

**Cause:** CopilotKit sends a slightly different payload than raw `RunAgentInput` expects.

**Fix:** Add a permissive wrapper:

```python
from fastapi import Request

@app.post("/agui")
async def agui_handler(request: Request):
    body = await request.json()
    # CopilotKit may send extra fields — be permissive
    input_data = RunAgentInput.model_validate(body)
    # ... rest of handler
```

---

## 10. Event Flow Cheat Sheet

```
User sends message
│
├─ RUN_STARTED
│
├─ STEP_STARTED("retrieve")
│  ├─ THINKING_START
│  │  ├─ THINKING_TEXT_MESSAGE_START
│  │  ├─ THINKING_TEXT_MESSAGE_CONTENT × N  ← "Searching for X..."
│  │  ├─ THINKING_TEXT_MESSAGE_END
│  │  └─ THINKING_END
│  └─ STEP_FINISHED("retrieve")
│
├─ STEP_STARTED("grade")
│  ├─ THINKING_START
│  │  ├─ THINKING_TEXT_MESSAGE_CONTENT × N  ← "Evaluating relevance..."
│  │  └─ THINKING_END
│  └─ STEP_FINISHED("grade")
│
├─ (if retry) STEP_STARTED("rewrite_1")
│  ├─ THINKING_TEXT_MESSAGE_CONTENT × N     ← "Rewriting query..."
│  └─ STEP_FINISHED("rewrite_1")
│
├─ STEP_STARTED("generate")
│  ├─ THINKING_START
│  │  └─ THINKING_TEXT_MESSAGE_CONTENT × N  ← Gemini's actual reasoning
│  ├─ THINKING_END
│  ├─ TEXT_MESSAGE_START
│  │  └─ TEXT_MESSAGE_CONTENT × N           ← Final answer streaming
│  └─ TEXT_MESSAGE_END
│  └─ STEP_FINISHED("generate")
│
└─ RUN_FINISHED
```

---

## 11. Thinking Level Guide

| Level     | Latency | Use Case                                    |
|-----------|---------|---------------------------------------------|
| `minimal` | ~50ms   | Grading (yes/no), simple routing            |
| `low`     | ~200ms  | Query rewriting, classification             |
| `medium`  | ~500ms  | Moderate analysis, summarization            |
| `high`    | ~1-3s   | Final answer generation, complex reasoning  |

In the implementation above, grading uses `"low"`, rewriting uses `"low"`, and final generation uses `"high"`. Adjust based on your latency requirements.

---

## 12. File Summary

```
backend/
├── app/
│   ├── main.py              ← Add: register_agui_endpoint(app) + CORS
│   ├── agui_endpoint.py     ← NEW: AG-UI SSE handler + ThinkingStateTracker
│   ├── config.py            ← Update: CHAT_MODEL=gemini-3-flash-preview
│   └── graph/
│       ├── state.py         ← Optional: add thinking_buffer, current_node
│       ├── nodes.py         ← Unchanged (still used by /chat endpoint)
│       ├── edges.py         ← Unchanged
│       └── workflow.py      ← Unchanged
├── pyproject.toml           ← Add: ag-ui-protocol, google-genai

frontend/                     ← NEW Next.js app
├── app/
│   ├── api/copilotkit/
│   │   └── route.ts         ← CopilotKit runtime → HttpAgent → /agui
│   ├── layout.tsx            ← CopilotKit provider
│   └── page.tsx              ← CopilotChat component
├── components/
│   └── ThinkingMessage.tsx   ← Custom thinking UI (if needed)
└── package.json              ← @copilotkit/*, @ag-ui/client
```

Your existing `/chat` endpoint (LangGraph invoke, no streaming) stays as-is. The new `/agui` endpoint runs the same RAG logic but streams thinking + answer via SSE.
