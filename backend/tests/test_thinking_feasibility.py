"""
Thinking 功能可行性测试
========================
验证三个关键路径：
  1. Gemini SDK 能否返回 thinking parts
  2. AG-UI 协议层 thinking 事件是否可用
  3. ag-ui-langgraph bridge 是否转发 state delta

运行: python -m pytest tests/test_thinking_feasibility.py -v -s
需要: GOOGLE_API_KEY 环境变量
"""
from __future__ import annotations

import os
import json
import pytest

# ── 从统一配置读取 ──
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import GOOGLE_API_KEY, DEFAULT_CHAT_MODEL


# ═══════════════════════════════════════════════════════════════
# Test 1: Gemini SDK — thinking parts 获取
# ═══════════════════════════════════════════════════════════════

class TestGeminiThinking:
    """验证 google.genai SDK 能否返回 thought=True 的 parts"""

    @pytest.fixture(autouse=True)
    def skip_no_key(self):
        if not GOOGLE_API_KEY:
            pytest.skip("GOOGLE_API_KEY not set")

    def test_thinking_stream_returns_thought_parts(self):
        """Gemini stream 应该返回 is_thought=True 的 chunk"""
        from google import genai
        from google.genai import types as genai_types

        client = genai.Client(api_key=GOOGLE_API_KEY)

        config = genai_types.GenerateContentConfig(
            thinking_config={"includeThoughts": True, "thinkingLevel": "HIGH"},
        )

        thought_texts = []
        answer_texts = []

        for chunk in client.models.generate_content_stream(
            model=DEFAULT_CHAT_MODEL,
            contents="What is 15 * 37? Show your reasoning.",
            config=config,
        ):
            if not chunk.candidates:
                continue
            for part in chunk.candidates[0].content.parts:
                if not part.text:
                    continue
                if getattr(part, "thought", False):
                    thought_texts.append(part.text)
                else:
                    answer_texts.append(part.text)

        print(f"\n[Gemini] Thought chunks: {len(thought_texts)}")
        print(f"[Gemini] Answer chunks: {len(answer_texts)}")
        if thought_texts:
            print(f"[Gemini] Thought preview: {thought_texts[0][:200]}...")
        if answer_texts:
            print(f"[Gemini] Answer preview: {''.join(answer_texts)[:200]}...")

        # 核心断言：必须有 thinking 内容
        assert len(thought_texts) > 0, "Gemini 没有返回任何 thought parts — thinking 不可用"
        assert len(answer_texts) > 0, "Gemini 没有返回 answer — 响应异常"

    def test_thinking_sync_single_call(self):
        """非 stream 模式也能拿到 thought"""
        from google import genai
        from google.genai import types as genai_types

        client = genai.Client(api_key=GOOGLE_API_KEY)

        config = genai_types.GenerateContentConfig(
            thinking_config={"includeThoughts": True, "thinkingLevel": "HIGH"},
        )

        response = client.models.generate_content(
            model=DEFAULT_CHAT_MODEL,
            contents="Explain why the sky is blue in one sentence.",
            config=config,
        )

        parts = response.candidates[0].content.parts
        thoughts = [p for p in parts if getattr(p, "thought", False)]
        answers = [p for p in parts if not getattr(p, "thought", False) and p.text]

        print(f"\n[Gemini sync] Thought parts: {len(thoughts)}")
        print(f"[Gemini sync] Answer parts: {len(answers)}")

        assert len(thoughts) > 0, "同步调用也应该返回 thought parts"


# ═══════════════════════════════════════════════════════════════
# Test 2: AG-UI 协议层 — thinking 事件序列化
# ═══════════════════════════════════════════════════════════════

class TestAGUIThinkingEvents:
    """验证 ag-ui-protocol 的 thinking 事件能否正确创建和序列化"""

    def test_thinking_event_types_exist(self):
        """所有 thinking 相关的 EventType 都存在"""
        from ag_ui.core import EventType

        required = [
            "THINKING_START",
            "THINKING_END",
            "THINKING_TEXT_MESSAGE_START",
            "THINKING_TEXT_MESSAGE_CONTENT",
            "THINKING_TEXT_MESSAGE_END",
        ]
        for name in required:
            assert hasattr(EventType, name), f"EventType.{name} 不存在"
            print(f"  ✓ EventType.{name} = {getattr(EventType, name)}")

    def test_thinking_events_serialize(self):
        """Thinking 事件能正确序列化为 SSE 格式"""
        from ag_ui.core import EventType
        from ag_ui.core.events import (
            ThinkingStartEvent,
            ThinkingTextMessageStartEvent,
            ThinkingTextMessageContentEvent,
            ThinkingTextMessageEndEvent,
            ThinkingEndEvent,
        )
        from ag_ui.encoder import EventEncoder

        encoder = EventEncoder()

        events = [
            ThinkingStartEvent(type=EventType.THINKING_START),
            ThinkingTextMessageStartEvent(type=EventType.THINKING_TEXT_MESSAGE_START),
            ThinkingTextMessageContentEvent(
                type=EventType.THINKING_TEXT_MESSAGE_CONTENT,
                delta="正在分析你的问题...",
            ),
            ThinkingTextMessageEndEvent(type=EventType.THINKING_TEXT_MESSAGE_END),
            ThinkingEndEvent(type=EventType.THINKING_END),
        ]

        for event in events:
            encoded = encoder.encode(event)
            assert encoded, f"{event.type} 编码失败"
            # SSE 格式应该以 "data: " 开头
            assert "data:" in encoded, f"{event.type} 不是 SSE 格式"
            print(f"  ✓ {event.type}: {encoded.strip()[:100]}")

    def test_thinking_content_with_chinese(self):
        """中文 thinking 内容能正确序列化"""
        from ag_ui.core import EventType
        from ag_ui.core.events import ThinkingTextMessageContentEvent
        from ag_ui.encoder import EventEncoder

        encoder = EventEncoder()
        event = ThinkingTextMessageContentEvent(
            type=EventType.THINKING_TEXT_MESSAGE_CONTENT,
            delta="让我想想这个八字的五行分布...",
        )
        encoded = encoder.encode(event)
        assert "让我想想" in encoded or "\\u" in encoded, "中文内容丢失"
        print(f"  ✓ 中文序列化: {encoded.strip()[:120]}")

    def test_state_delta_event_exists(self):
        """STATE_DELTA 事件可用（作为 thinking 的备选传输方案）"""
        from ag_ui.core import EventType

        assert hasattr(EventType, "STATE_DELTA"), "STATE_DELTA 不存在"
        print(f"  ✓ EventType.STATE_DELTA = {EventType.STATE_DELTA}")


# ═══════════════════════════════════════════════════════════════
# Test 3: ag-ui-langgraph bridge — 能否安装 + state 转发
# ═══════════════════════════════════════════════════════════════

class TestBridgeAvailability:
    """验证 ag-ui-langgraph bridge 的可用性"""

    def test_bridge_importable(self):
        """ag-ui-langgraph 能否导入"""
        try:
            import ag_ui_langgraph
            ver = getattr(ag_ui_langgraph, "__version__", "unknown")
            print(f"  ✓ ag_ui_langgraph 已安装: {ver}")
            available = True
        except ImportError:
            available = False
            print("  ✗ ag_ui_langgraph 未安装")

        if not available:
            pytest.skip(
                "ag-ui-langgraph 未安装 — 需要 pip install ag-ui-langgraph\n"
                "  如果安装失败，说明需要走手写 SSE 方案（路径 A）"
            )

    def test_bridge_has_endpoint_function(self):
        """bridge 提供 add_langgraph_fastapi_endpoint"""
        try:
            from ag_ui_langgraph import add_langgraph_fastapi_endpoint
            import inspect
            sig = inspect.signature(add_langgraph_fastapi_endpoint)
            print(f"  ✓ add_langgraph_fastapi_endpoint{sig}")
        except ImportError:
            pytest.skip("ag-ui-langgraph 未安装")

    def test_copilotkit_importable(self):
        """copilotkit SDK 能否导入"""
        try:
            from copilotkit import CopilotKitState, LangGraphAGUIAgent
            print("  ✓ CopilotKitState 可用")
            print("  ✓ LangGraphAGUIAgent 可用")
        except ImportError as e:
            pytest.skip(f"copilotkit 未安装: {e}")

    def test_copilotkit_state_supports_custom_fields(self):
        """CopilotKitState 能否扩展自定义字段（如 thinking_buffer）"""
        try:
            from copilotkit import CopilotKitState

            class TestState(CopilotKitState):
                thinking_buffer: str

            # CopilotKitState 是 TypedDict，用 dict 方式访问
            state: TestState = {"messages": [], "thinking_buffer": "test thinking"}
            assert state["thinking_buffer"] == "test thinking"
            print("  ✓ CopilotKitState 支持扩展 thinking_buffer（TypedDict, dict 访问）")
        except ImportError:
            pytest.skip("copilotkit 未安装")
        except Exception as e:
            pytest.fail(f"CopilotKitState 不支持自定义字段: {e}")


# ═══════════════════════════════════════════════════════════════
# 综合结论
# ═══════════════════════════════════════════════════════════════

class TestFeasibilitySummary:
    """运行完所有测试后的结论输出"""

    def test_print_summary(self):
        """输出可行性结论"""
        results = {}

        # Check 1: Gemini thinking
        try:
            from google.genai import types as genai_types
            genai_types.ThinkingConfig(includeThoughts=True)
            results["gemini_thinking_api"] = "✓ 可用"
        except Exception as e:
            results["gemini_thinking_api"] = f"✗ {e}"

        # Check 2: AG-UI thinking events
        try:
            from ag_ui.core.events import ThinkingStartEvent
            from ag_ui.encoder import EventEncoder
            results["agui_thinking_events"] = "✓ 可用"
        except Exception as e:
            results["agui_thinking_events"] = f"✗ {e}"

        # Check 3: Bridge
        try:
            import ag_ui_langgraph
            results["bridge"] = "✓ 已安装"
        except ImportError:
            results["bridge"] = "✗ 未安装 — 需要 pip install ag-ui-langgraph copilotkit"

        # Check 4: CopilotKit
        try:
            from copilotkit import CopilotKitState
            results["copilotkit"] = "✓ 已安装"
        except ImportError:
            results["copilotkit"] = "✗ 未安装"

        print("\n" + "=" * 60)
        print("  THINKING 功能可行性报告")
        print("=" * 60)
        for k, v in results.items():
            print(f"  {k:30s} {v}")
        print("=" * 60)

        bridge_ok = "✓" in results.get("bridge", "")
        copilotkit_ok = "✓" in results.get("copilotkit", "")

        if bridge_ok and copilotkit_ok:
            print("  推荐方案: 路径 B — LangGraph state + STATE_DELTA")
            print("  在 agent_node 中用 Gemini SDK 获取 thinking，")
            print("  写入 state.thinking_buffer，bridge 自动转发")
        else:
            print("  推荐方案: 路径 A — 手写 SSE endpoint")
            print("  直接发射 THINKING_* 事件，绕过 bridge")
            print(f"  (需先安装: pip install ag-ui-langgraph copilotkit)")
        print("=" * 60)
