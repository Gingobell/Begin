"""
Content2 生成服务（新版 prompt）。

目标：
- 保持“用户画像（Letta）+ 关键词链路（get_top_events → rerank_keywords_by_category → _format_category_keywords）”不变
- 不启用 memory_block 正文拼接（仅保留占位）
- 输出结构采用 V2：Overall(date_line/daily_management/today_actions/power_drain/surge_protection/recharge)，Domain(title_line/status/suggestion)
- 口吻更像人在说话：强制第二人称、去说明文/作文腔；禁止任何八字/塔罗术语与原理解释；不做反差噱头
"""

import instructor
import google.generativeai as genai
from pydantic import BaseModel, Field
from typing import Dict, Optional, List, Any
import os
import logging
import asyncio

from ..core.config import DEFAULT_CHAT_MODEL
from .fortune_scoring_engine import FortuneScoringEngine
# from .keyword import rerank_keywords_by_category
# from .keyword_v2 import get_top_events
from .letta_service import letta_service


# ----------------------------
# Legacy (kept for compatibility with test_prompt等)
# ----------------------------

class CategoryFortune(BaseModel):
    """通用单领域运势（兼容旧测试/工具）"""
    summary: str = Field(..., max_length=120)
    advice: str = Field(..., max_length=20)
    rating: int = Field(..., ge=1, le=5)


class AllCategoriesFortune(BaseModel):
    """多领域运势集合（兼容 test_prompt 等调试接口）"""
    overall: CategoryFortune
    career: Optional[CategoryFortune] = None
    love: Optional[CategoryFortune] = None
    wealth: Optional[CategoryFortune] = None
    study: Optional[CategoryFortune] = None
    social: Optional[CategoryFortune] = None
    health: Optional[CategoryFortune] = None


# ----------------------------
# Output Schema (V2)
# ----------------------------

class OverallFortune(BaseModel):
    """综合运势板块"""
    daily_management: str = Field(description="一句话描述今天整体会是什么感觉、适合什么节奏")
    today_actions: str = Field(description="今天最顺手的一件事 需要来自于今日得分最高的领域, 一句话，可以稍微长一点 包括描述适合做什么+推荐行动")
    power_drain: str = Field(description="今天可能卡的地方 来自于今天分数最低的领域 描述不适合做什么, 一句话")
    surge_protection: str = Field(description="卡住了怎么办：一个边界 或 一个最省力替代，一句话")
    recharge: str = Field(description="今天的小奖励，一句话，具体点, 从用户profile里面记录的的兴趣爱好里面选一件 不能用最近7天使用过的 如果没有可说的兴趣爱好 自行判断找一件用户会喜欢做的事")


class DomainFortune(BaseModel):
    """分领域运势"""
    status: str = Field(description="这个领域今天什么状态，顺的顺在哪，卡的卡在哪, 不许提起这个领域的名字")
    suggestion: str = Field(description="一个动作或一句提醒，像朋友的建议一样")


class BatteryFortuneResponse(BaseModel):
    """完整电池运势结构"""
    overall: OverallFortune
    career: Optional[DomainFortune] = None
    wealth: Optional[DomainFortune] = None
    love: Optional[DomainFortune] = None
    social: Optional[DomainFortune] = None
    study: Optional[DomainFortune] = None
    low_power_mode: Optional[bool] = None
    scores: Optional[Dict[str, int]] = None
    fast_charge_domain: Optional[str] = None
    power_drain_domain: Optional[str] = None

# ----------------------------
# Service
# ----------------------------

class StructuredFortuneService:
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set")

        genai.configure(api_key=api_key)

        self.model = genai.GenerativeModel(
            model_name=DEFAULT_CHAT_MODEL,
            generation_config={"response_mime_type": "application/json"},
        )

        self.client = instructor.from_gemini(
            client=self.model,
            mode=instructor.Mode.GEMINI_JSON,
        )

        self.scoring_engine = FortuneScoringEngine()

        # 初始化 Supabase 客户端用于查询历史运势
        from supabase import create_client, Client
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # 统一 Prompt（V2 结构，强调口语与禁术语）
        self.BATTERY_PROMPT_TEMPLATE = """
你输出"电池运势"（严格 JSON）。
【输入分数（已算好）】
- 综合: {score_overall}/100
- 事业: {score_career}/100
- 财富: {score_wealth}/100
- 感情: {score_love}/100
- 人际: {score_social}/100
- 学业: {score_study}/100
- 低电量模式: {low_power_mode_text}
【写作倾向】
当前: {writing_tilt}
- sunny_witty：轻快带点俏皮，像朋友在调侃你
- confident_light：干脆利落，肯定但不浮夸
- steady_warm：稳当有温度，像靠谱的老友
- focused_sharp：直接犀利，不废话
- gentle_guardrails：温和但有边界，照顾情绪但不哄骗
- low_power_soft：轻柔省力，先护住状态再说别的
【内部参考（不要复述）】
- 领域排序: {ranked_domains_text}
- 第一高: {top1_text}
- 最低: {drain_domain_name}
- 后三低: {bottom3_text}
【能量背景（脑内用，禁止输出术语）】
- 体质: {body_strength}
- 十二长生: {energy_phase}
- 日主: {day_master}
- 天干: {stem_relation}（{stem_analysis}）
- 地支: {branch_relation}（{branch_analysis}）
- 今日塔罗: {card_name}（{orientation}） 正位: {meaning_up} | 逆位: {meaning_down}
{user_profile_block}
{recent_recharges_block}
{yesterday_diary_block}

---
【用户信息怎么用】
画像是让你知道在跟谁说话，不是让你每次都把里面的词念一遍。 
像朋友一样：偶尔记得对方喜欢什么、在忙什么，但不会每次见面都复述一遍对方的简历。
✅ 好的用法：
- 知道他在做开发 → "代码趁手感好多写点"（没提项目名、没提百分比）
- 知道他有对象 → "感情上别想太多"（没复述约会状态）
- 偶尔提一句他喜欢的东西 → "晚上去吃火锅吧"（自然带过，不是每次都说）
❌ 坏的用法：
- 每次都提同一个细节 → 用户会觉得你只会这一招
- 照抄数字和进度 → "把50%推到60%" 像在读他的TODO list
- 编造画像里没有的东西 → 没提实验室就别说"回实验室"
关键：用画像来**选话题方向**，不是用来**填词**。
---
【核心：像朋友发微信，带点温度】
口语感：
- 句子可以不完整
- 动词打头，少堆形容词
- 不解释为什么，直接说做什么
- 留白比写满有温度

语气词（重要！）：
- 有的时候用 "你" 这样感觉真正的朋友间语气
- 句尾加 呗、呀、嘛、吧、啦、噢、哦 让语气变软
- 偶尔用 好不好、行不行、怎么样 把命令变邀请
- 适当用 可能、感觉、有点 让判断不那么绝对
- 不是每句都加，自然穿插，别刻意

对比：
❌ "直接推掉" → ✅ "直接推掉呗"
❌ "别预设立场" → ✅ "别预设立场好不好"
❌ "容易走神" → ✅ "可能容易走神，注意一下呀"
❌ "检查订阅" → ✅ "顺手看看订阅有没有浪费的"
❌ "集中精力解决卡点" → ✅ "那个卡点今天能收就收一下呗"
❌ "节奏挺稳" → ✅ "今天节奏蛮稳的"

语气层次：
- 肯定/鼓励：蛮好的、挺顺的、不错噢
- 提醒/建议：注意一下呀、试试看呗、要不就...
- 边界/劝退：算了吧、先放放嘛、没必要的
- 小奖励：去吧去吧、犒劳下自己呀

---
【禁止】
- 八字/命理/塔罗术语
- 解释原理
- 形容词堆叠
- 书面连接词（"与其...不如..."）
- 编造画像里没有的具体场景
- 纯命令式语气（没有语气词的祈使句连续出现）
中文，短句，无表情符号，严格JSON。
"""

    def _get_recent_recharges(self, user_id: str, days: int = 7) -> str:
        """
        查询用户最近N天的运势记录中的 recharge 字段

        参数:
        - user_id: 用户ID
        - days: 查询天数，默认7天

        返回:
        - 格式化的文本，如："这些是最近7天使用过的小奖励：xxx, xxx"
        """
        if not user_id:
            return ""

        try:
            from datetime import date, timedelta

            # 计算查询的起始日期
            today = date.today()
            start_date = today - timedelta(days=days)

            # 查询最近N天的运势记录
            response = self.supabase.table("daily_fortune_details").select("battery_fortune, fortune_date").eq("user_id", user_id).gte("fortune_date", start_date.isoformat()).lt("fortune_date", today.isoformat()).order("fortune_date", desc=True).execute()

            if not response.data:
                return ""

            # 提取 recharge 字段
            recharges = []
            for record in response.data:
                battery_fortune = record.get("battery_fortune")
                if battery_fortune and isinstance(battery_fortune, dict):
                    overall = battery_fortune.get("overall")
                    if overall and isinstance(overall, dict):
                        recharge = overall.get("recharge")
                        if recharge and isinstance(recharge, str) and recharge.strip():
                            recharges.append(recharge.strip())

            if not recharges:
                return ""

            # 格式化返回文本
            recharges_text = "、".join(recharges)
            return f"这些是最近{days}天使用过的小奖励：{recharges_text}"

        except Exception as e:
            logging.error(f"❌ 查询最近{days}天 recharge 失败: {e}")
            return ""

    def _get_yesterday_diary(self, user_id: str) -> str:
        """查询用户昨日的日记"""
        if not user_id:
            return ""

        try:
            from datetime import date, timedelta
            yesterday = date.today() - timedelta(days=1)

            yesterday_start = f"{yesterday.isoformat()}T00:00:00+00:00"
            today_start = f"{(yesterday + timedelta(days=1)).isoformat()}T00:00:00+00:00"
            response = self.supabase.table("diary_entries").select("content").eq("user_id", user_id).gte("created_at", yesterday_start).lt("created_at", today_start).order("created_at", desc=True).limit(1).execute()

            if not response.data:
                return ""

            content = (response.data[0].get("content") or "").strip()
            if not content:
                return ""

            content_preview = content[:200] + "..." if len(content) > 200 else content
            return f"【昨日能量】\n昨天记录：{content_preview}\n如果今日运势和昨日记录有关联，可以稍微提一句，但不要生硬，没关联就不提"

        except Exception as e:
            logging.error(f"❌ 查询昨日日记失败: {e}")
            return ""

    def _choose_writing_tilt(self, overall_score: int) -> str:
        if overall_score >= 90:
            return "sunny_witty"
        if overall_score >= 80:
            return "confident_light"
        if overall_score >= 70:
            return "steady_warm"
        if overall_score >= 60:
            return "focused_sharp"
        if overall_score >= 50:
            return "gentle_guardrails"
        return "low_power_soft"

    async def generate_battery_fortune(
        self,
        bazi_analysis: Dict,
        tarot_reading: Dict,
        user_memory: Dict,
        contextual_memory: Dict,
        user_id: Optional[str],
        language: str = "zh-CN",
        gender: str = "Male",
        debug_print_prompt: bool = False,
    ) -> Dict:
        card = tarot_reading.get("card", {})
        tarot_card_id = card.get("card_id", "")
        is_upright = (tarot_reading.get("orientation", "upright") == "upright")

        stem_relation = bazi_analysis.get("stem_influence", {}).get("relation", "")
        branch_relation = bazi_analysis.get("branch_influence", {}).get("relation", "")
        stem_god_raw = bazi_analysis.get("stem_influence", {}).get("raw", "比肩")
        branch_god_raw = bazi_analysis.get("branch_influence", {}).get("raw", "比肩")
        branch_relation_type = bazi_analysis.get("branch_influence", {}).get("relation_type", "none")
        nobleman_score = bazi_analysis.get("nobleman_score", 0)

        # 评分
        scoring_result = self.scoring_engine.calculate(
            body_strength=bazi_analysis.get("body_strength", "Balanced"),
            energy_phase=bazi_analysis.get("energy_phase", ""),
            branch_relation=branch_relation_type,
            nobleman_score=int(nobleman_score or 0),
            stem_god=stem_god_raw,
            branch_god=branch_god_raw,
            tarot_card_id=tarot_card_id,
            tarot_is_upright=is_upright,
            gender=gender or "Male",
        )

        domain_scores = scoring_result.domain_scores
        domain_labels = {
            "career": "事业",
            "wealth": "财富",
            "love": "感情",
            "social": "人际",
            "study": "学业",
        }
        domain_tarot_contribs = getattr(scoring_result, "domain_tarot_contribution", {})

        def _is_major(card_id: str) -> int:
            if not card_id:
                return 0
            parts = str(card_id).split("_")
            if parts and parts[0].isdigit() and int(parts[0]) < 22:
                return 1
            return 0

        is_major_arcana = 1 if getattr(scoring_result, "is_major_arcana", False) else _is_major(tarot_card_id)

        energy_intensity_table = {
            "七杀": 5,
            "伤官": 4,
            "偏财": 4,
            "劫财": 3,
            "食神": 3,
            "正官": 3,
            "正财": 2,
            "正印": 2,
            "偏印": 2,
            "比肩": 1,
        }

        def _energy_intensity(god: str) -> int:
            return energy_intensity_table.get(god, 0)

        energy_intensity = max(_energy_intensity(stem_god_raw), _energy_intensity(branch_god_raw))

        static_priority = {"career": 5, "wealth": 4, "love": 3, "study": 2, "social": 1}

        sortable_items: List[Dict[str, Any]] = []
        for domain, score in domain_scores.items():
            tarot_contribution = domain_tarot_contribs.get(domain, scoring_result.tarot_modifiers.get(domain, 0))
            priority = static_priority.get(domain, 0)
            sortable_items.append(
                {
                    "domain": domain,
                    "score": score,
                    "tarot_contrib": tarot_contribution,
                    "is_major": is_major_arcana,
                    "energy_intensity": energy_intensity,
                    "priority": priority,
                }
            )

        sorted_domains = sorted(
            sortable_items,
            key=lambda x: (x["score"], x["tarot_contrib"], x["is_major"], x["energy_intensity"], x["priority"]),
            reverse=True,
        )

        fast_domain = sorted_domains[0]["domain"]
        drain_domain = sorted_domains[-1]["domain"]

        ranked_domains_cn = [domain_labels[item["domain"]] for item in sorted_domains]
        ranked_domains_text = " > ".join(ranked_domains_cn)
        top1_text = "、".join(ranked_domains_cn[:1])
        bottom3_text = "、".join(ranked_domains_cn[-3:])

        writing_tilt = self._choose_writing_tilt(int(scoring_result.overall_score or 0))

        # 记忆正文不启用
        memory_block = ""

        # 关键词与画像
        category_keywords: Dict[str, Any] = {}
        user_profile = ""

        # 获取用户画像（保留）
        try:
            if not user_id:
                if user_memory and isinstance(user_memory, dict):
                    user_id = user_memory.get("user_id")
                if not user_id and contextual_memory and isinstance(contextual_memory, dict):
                    user_id = contextual_memory.get("user_id")

            if user_id:
                # 保留用户画像获取
                user_profile = await letta_service.get_user_profile(user_id)

                # ===== 关键词提取步骤已注释掉（只注释关键词，保留画像） =====
                # candidate_events = get_top_events(user_profile, top_k=30)
                #
                # if candidate_events:
                #     category_keywords = await rerank_keywords_by_category(
                #         user_memory=user_memory or {},
                #         contextual_memory=contextual_memory or {},
                #         candidate_events=candidate_events,
                #     )
                # ===== 关键词提取步骤已注释掉 =====
            else:
                logging.warning("⚠️ 缺少 user_id，跳过用户画像获取")
        except Exception as e:
            logging.error(f"❌ 用户画像获取失败: {e}")
            user_profile = ""

        # category_keywords 为空，所以 category_keywords_block 会是空字符串
        category_keywords_block = self._format_category_keywords(category_keywords)

        # 用户画像块会被正常填充到 prompt 中
        if user_profile and user_profile != "暂无用户画像":
            user_profile_block = f"【用户画像（来自 Letta）】\n{user_profile}"
        else:
            user_profile_block = ""

        # 查询最近7天使用过的小奖励
        recent_recharges_text = ""
        if user_id:
            recent_recharges_text = self._get_recent_recharges(user_id, days=7)
            if recent_recharges_text:
                logging.info(f"✅ 获取最近7天 recharge: {recent_recharges_text}")

        # 查询昨日日记
        yesterday_diary_block = ""
        if user_id:
            yesterday_diary_block = self._get_yesterday_diary(user_id)

        # 构建最近小奖励块
        if recent_recharges_text:
            recent_recharges_block = f"【最近使用过的小奖励】\n{recent_recharges_text}"
        else:
            recent_recharges_block = ""

        prompt = self.BATTERY_PROMPT_TEMPLATE.format(
            score_overall=scoring_result.overall_score,
            score_career=domain_scores.get("career", 60),
            score_wealth=domain_scores.get("wealth", 60),
            score_love=domain_scores.get("love", 60),
            score_social=domain_scores.get("social", 60),
            score_study=domain_scores.get("study", 60),
            low_power_mode_text="是" if scoring_result.low_power_mode else "否",
            writing_tilt=writing_tilt,
            ranked_domains_text=ranked_domains_text,
            top1_text=top1_text,
            bottom3_text=bottom3_text,
            drain_domain_name=domain_labels.get(drain_domain, drain_domain),
            body_strength=bazi_analysis.get("body_strength", ""),
            energy_phase=bazi_analysis.get("energy_phase", ""),
            day_master=bazi_analysis.get("day_master", ""),
            stem_relation=stem_relation,
            stem_analysis=bazi_analysis.get("stem_influence", {}).get("analysis", ""),
            branch_relation=branch_relation,
            branch_analysis=bazi_analysis.get("branch_influence", {}).get("analysis", ""),
            card_name=card.get("card_name", ""),
            orientation=tarot_reading.get("orientation", "upright"),
            meaning_up=card.get("meaning_up", ""),
            meaning_down=card.get("meaning_down", ""),
            user_profile_block=user_profile_block,
            recent_recharges_block=recent_recharges_block,
            yesterday_diary_block=yesterday_diary_block,
            memory_block=memory_block or "【用户记忆】无特别备注",
            category_keywords_block=category_keywords_block,
        )

        if language and language.startswith("en"):
            prompt += "\n\nRespond in English. Keep sentences short. Do NOT add emojis. Output must be valid JSON per schema."
        else:
            prompt += "\n\n请用中文输出，保持短句、无表情符号，严格按照 JSON 结构返回。"

        # 调试模式：打印完整 Prompt
        if debug_print_prompt:
            print("\n" + "=" * 80)
            print(f"📝 完整 Prompt (长度: {len(prompt)} 字符)")
            print("=" * 80)
            print(prompt)
            print("=" * 80 + "\n")

        result = await asyncio.to_thread(
            self.client.chat.completions.create,
            response_model=BatteryFortuneResponse,
            messages=[{"role": "user", "content": prompt}],
            max_retries=2,
        )

        result_dict = result.model_dump()

        result_dict["low_power_mode"] = scoring_result.low_power_mode
        result_dict["scores"] = {
            "overall": scoring_result.overall_score,
            **domain_scores,
        }
        result_dict["fast_charge_domain"] = domain_labels.get(fast_domain, fast_domain)
        result_dict["power_drain_domain"] = domain_labels.get(drain_domain, drain_domain)

        return result_dict

    def _format_category_keywords(self, keywords: Dict[str, Any]) -> str:
        """格式化类别关键词为 Prompt 文本块（旧版格式 + 新版鲁棒性）"""
        if not keywords:
            return ""

        domain_labels = {
            "career": "事业",
            "wealth": "财富",
            "love": "感情",
            "social": "人际",
            "study": "学业",
        }

        def _normalize(v: Any) -> str:
            if v is None:
                return ""
            if isinstance(v, str):
                return v.strip()
            if isinstance(v, list):
                items = []
                for x in v:
                    s = _normalize(x)
                    if s:
                        items.append(s)
                return "；".join(items[:2]).strip()
            if isinstance(v, dict):
                for key in ("event", "text", "content", "title", "summary", "value"):
                    if key in v:
                        return _normalize(v[key])
                return ""
            return str(v).strip()

        parts = ["【用户行为关键词】"]
        for category, raw in keywords.items():
            text = _normalize(raw)
            if not text:
                continue
            label = domain_labels.get(category, str(category))
            parts.append(f"- {label}: {text}")

        if len(parts) == 1:
            return ""

        return "\n".join(parts)


structured_fortune_service = StructuredFortuneService()
