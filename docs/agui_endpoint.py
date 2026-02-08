"""
AG-UI SSE Endpoint — Gemini 3 Flash Thinking + LangGraph RAG
=============================================================

Drop this file into backend/app/agui_endpoint.py

Then in main.py add:
    from app.agui_endpoint import register_agui_endpoint
    register_agui_endpoint(app)

Streams Gemini's thought process via AG-UI ThinkingTextMessageContentEvent,
interleaved with step events for each RAG phase (retrieve, grade, rewrite, generate).

Requires:
    pip install ag-ui-protocol google-genai sse-starlette
    CHAT_MODEL=gemini-3-flash-preview in .env
"""
from __future__ import annotations

import uuid
import logging
import traceback
from typing import AsyncGenerator

from fastapi import FastAPI, Request
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
from app.services.supabase_ops import supabase_ops
from app.core.gemini_embeddings import GeminiEmbeddings

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
#  CLIENTS
# ═══════════════════════════════════════════════════════════

gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
_emb = GeminiEmbeddings(
    model=config.EMBEDDING_MODEL,
    output_dimensionality=config.EMBEDDING_DIM,
)


# ═══════════════════════════════════════════════════════════
#  THINKING STATE TRACKER
# ═══════════════════════════════════════════════════════════

class ThinkingStateTracker:
    """
    Manages thinking/answer phase transitions for AG-UI event emission.

    Prevents the two most common AG-UI errors:
    1. "Cannot send TEXT_MESSAGE_START after TEXT_MESSAGE_START"
       → Caused by not closing a phase before opening the same one
    2. "Delta must not be an empty string"
       → Caused by models sending empty text chunks

    Usage:
        tracker = ThinkingStateTracker(encoder)
        for ev in tracker.emit_thinking("Planning..."):
            yield ev
        for ev in tracker.emit_answer("The answer is..."):
            yield ev
        for ev in tracker.close_all():
            yield ev
    """

    def __init__(self, encoder: EventEncoder):
        self.encoder = encoder
        self.in_thinking = False
        self.in_answer = False
        self.thinking_msg_id = ""
        self.answer_msg_id = ""

    # ── Thinking phase ──

    def _open_thinking(self) -> list[str]:
        events = []
        if self.in_answer:
            events.extend(self._close_answer())
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

    def _close_thinking(self) -> list[str]:
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

    def emit_thinking(self, delta: str) -> list[str]:
        """Emit thinking content. Filters empty strings automatically."""
        if not delta or not delta.strip():
            return []
        events = self._open_thinking()
        events.append(self.encoder.encode(ThinkingTextMessageContentEvent(
            type=EventType.THINKING_TEXT_MESSAGE_CONTENT,
            message_id=self.thinking_msg_id,
            delta=delta,
        )))
        return events

    # ── Answer phase ──

    def _open_answer(self) -> list[str]:
        events = []
        if self.in_thinking:
            events.extend(self._close_thinking())
        if not self.in_answer:
            self.answer_msg_id = str(uuid.uuid4())
            events.append(self.encoder.encode(TextMessageStartEvent(
                type=EventType.TEXT_MESSAGE_START,
                message_id=self.answer_msg_id,
                role="assistant",
            )))
            self.in_answer = True
        return events

    def _close_answer(self) -> list[str]:
        events = []
        if self.in_answer:
            events.append(self.encoder.encode(TextMessageEndEvent(
                type=EventType.TEXT_MESSAGE_END,
                message_id=self.answer_msg_id,
            )))
            self.in_answer = False
        return events

    def emit_answer(self, delta: str) -> list[str]:
        """Emit answer content. Filters empty strings automatically."""
        if not delta:
            return []
        events = self._open_answer()
        events.append(self.encoder.encode(TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id=self.answer_msg_id,
            delta=delta,
        )))
        return events

    # ── Cleanup ──

    def close_all(self) -> list[str]:
        """Close whatever phase is open. MUST call at end of stream."""
        events = []
        events.extend(self._close_thinking())
        events.extend(self._close_answer())
        return events


# ═══════════════════════════════════════════════════════════
#  GEMINI STREAMING WITH THINKING
# ═══════════════════════════════════════════════════════════

def gemini_stream(
    prompt: str,
    system_instruction: str | None = None,
    thinking_level: str = "high",
):
    """
    Call Gemini 3 Flash with thinking. Yields (is_thought: bool, text: str).

    Args:
        prompt: User/task prompt
        system_instruction: Optional system prompt
        thinking_level: "minimal" | "low" | "medium" | "high"
    """
    cfg = genai_types.GenerateContentConfig(
        thinking_config=genai_types.ThinkingConfig(
            include_thoughts=True,
            thinking_level=thinking_level,
        ),
    )
    if system_instruction:
        cfg.system_instruction = system_instruction

    try:
        stream = gemini_client.models.generate_content_stream(
            model=config.CHAT_MODEL,
            contents=prompt,
            config=cfg,
        )
        for chunk in stream:
            if not chunk.candidates:
                continue
            candidate = chunk.candidates[0]
            if not candidate.content or not candidate.content.parts:
                continue
            for part in candidate.content.parts:
                if not part.text:
                    continue
                yield (bool(getattr(part, "thought", False)), part.text)

    except Exception as e:
        logger.error(f"Gemini stream error: {e}")
        raise


# ═══════════════════════════════════════════════════════════
#  RAG PIPELINE WITH THINKING
# ═══════════════════════════════════════════════════════════

async def rag_with_thinking(
    question: str,
    encoder: EventEncoder,
    tracker: ThinkingStateTracker,
) -> AsyncGenerator[str, None]:
    """
    Full RAG pipeline:
      retrieve → grade → (rewrite if needed) → generate

    Each phase emits:
      - StepStarted/StepFinished for progress tracking
      - ThinkingTextMessageContent for Gemini's reasoning
      - TextMessageContent for the final answer
    """

    # ── RETRIEVE ──
    yield encoder.encode(StepStartedEvent(type=EventType.STEP_STARTED, step_name="retrieve"))

    for ev in tracker.emit_thinking(f'Searching knowledge base for: "{question}"...'):
        yield ev

    vec = _emb.embed_query(question)
    results = supabase_ops.retrieve_context_mesh(question, vec)
    context = "\n\n".join([r.get("content", "") for r in results])
    num_results = len(results)

    yield encoder.encode(StepFinishedEvent(type=EventType.STEP_FINISHED, step_name="retrieve"))

    # ── GRADE ──
    yield encoder.encode(StepStartedEvent(type=EventType.STEP_STARTED, step_name="grade"))

    for ev in tracker.emit_thinking(f"Retrieved {num_results} documents. Evaluating relevance..."):
        yield ev

    grade_prompt = (
        f"Does this context help answer the question? Reply ONLY 'yes' or 'no'.\n\n"
        f"Context: {context[:2000]}\n\nQuestion: {question}"
    )
    grade_result = ""
    for is_thought, text in gemini_stream(grade_prompt, thinking_level="low"):
        if is_thought:
            for ev in tracker.emit_thinking(text):
                yield ev
        else:
            grade_result += text

    is_relevant = "yes" in grade_result.lower()

    for ev in tracker.emit_thinking(
        f'Grade: {"relevant ✓" if is_relevant else "not relevant ✗"}'
    ):
        yield ev

    yield encoder.encode(StepFinishedEvent(type=EventType.STEP_FINISHED, step_name="grade"))

    # ── REWRITE LOOP ──
    retry = 0
    while not is_relevant and retry < config.MAX_RETRY:
        retry += 1
        step = f"rewrite_{retry}"

        yield encoder.encode(StepStartedEvent(type=EventType.STEP_STARTED, step_name=step))

        for ev in tracker.emit_thinking(
            f"Rewriting query (attempt {retry}/{config.MAX_RETRY})..."
        ):
            yield ev

        new_q = ""
        for is_thought, text in gemini_stream(
            f"Rewrite this search query for better results: {question}",
            thinking_level="low",
        ):
            if is_thought:
                for ev in tracker.emit_thinking(text):
                    yield ev
            else:
                new_q += text

        question = new_q.strip()
        for ev in tracker.emit_thinking(f'New query: "{question}"'):
            yield ev

        yield encoder.encode(StepFinishedEvent(type=EventType.STEP_FINISHED, step_name=step))

        # Re-retrieve
        r_step = f"retrieve_{retry + 1}"
        yield encoder.encode(StepStartedEvent(type=EventType.STEP_STARTED, step_name=r_step))

        vec = _emb.embed_query(question)
        results = supabase_ops.retrieve_context_mesh(question, vec)
        context = "\n\n".join([r.get("content", "") for r in results])

        yield encoder.encode(StepFinishedEvent(type=EventType.STEP_FINISHED, step_name=r_step))

        # Re-grade (minimal thinking — just need yes/no)
        grade_result = ""
        for is_thought, text in gemini_stream(
            f"Does this context help? 'yes' or 'no'.\n"
            f"Context: {context[:2000]}\nQuestion: {question}",
            thinking_level="minimal",
        ):
            if not is_thought:
                grade_result += text
        is_relevant = "yes" in grade_result.lower()

    # ── GENERATE ──
    yield encoder.encode(StepStartedEvent(type=EventType.STEP_STARTED, step_name="generate"))

    system = (
        "You are a knowledgeable RAG assistant. Answer precisely based on "
        "the provided context. Cite specific parts when possible. "
        "If the context is insufficient, say so clearly."
    )
    gen_prompt = (
        f"Answer based on context. If context doesn't help, say so.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}"
    )

    for is_thought, text in gemini_stream(gen_prompt, system_instruction=system, thinking_level="high"):
        if is_thought:
            for ev in tracker.emit_thinking(text):
                yield ev
        else:
            for ev in tracker.emit_answer(text):
                yield ev

    yield encoder.encode(StepFinishedEvent(type=EventType.STEP_FINISHED, step_name="generate"))


# ═══════════════════════════════════════════════════════════
#  REGISTER ENDPOINT
# ═══════════════════════════════════════════════════════════

def register_agui_endpoint(app: FastAPI):
    """
    Register POST /agui — AG-UI SSE streaming endpoint.

    Call this in main.py:
        from app.agui_endpoint import register_agui_endpoint
        register_agui_endpoint(app)
    """

    @app.post("/agui")
    async def agui_handler(request: Request):
        body = await request.json()

        try:
            input_data = RunAgentInput.model_validate(body)
        except Exception as e:
            logger.error(f"Input validation error: {e}")
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=422, content={"error": str(e)})

        async def event_generator():
            encoder = EventEncoder()
            tracker = ThinkingStateTracker(encoder)

            yield encoder.encode(RunStartedEvent(
                type=EventType.RUN_STARTED,
                thread_id=input_data.thread_id,
                run_id=input_data.run_id,
            ))

            try:
                # Extract question
                user_msgs = [m for m in input_data.messages if m.role == "user"]
                if not user_msgs:
                    for ev in tracker.emit_answer("No question provided."):
                        yield ev
                else:
                    content = user_msgs[-1].content
                    # Handle both string and list[ContentPart] formats
                    if isinstance(content, list):
                        question = " ".join(
                            getattr(p, "text", "") for p in content
                        ).strip()
                    else:
                        question = str(content)

                    if not question:
                        for ev in tracker.emit_answer("Empty question received."):
                            yield ev
                    else:
                        async for event in rag_with_thinking(question, encoder, tracker):
                            yield event

            except Exception as e:
                logger.error(f"Agent error: {e}\n{traceback.format_exc()}")
                for ev in tracker.close_all():
                    yield ev
                yield encoder.encode(RunErrorEvent(
                    type=EventType.RUN_ERROR,
                    message=f"Internal error: {str(e)}",
                ))
                return

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
                "X-Accel-Buffering": "no",
            },
        )
