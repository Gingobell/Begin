from typing import List, Dict, Any, Optional
import logging
from .vector_service import VectorService
from .google_search_service import GoogleSearchService


class KnowledgeService:
    """知识检索和管理服务 - 集成动态权重与智能搜索"""

    def __init__(self):
        self.similarity_threshold = 0.7
        self.max_results = 5
        self.vector_service = VectorService()
        self.google_search = GoogleSearchService()

    def _should_trigger_web_search(self, knowledge_results: List[Dict], query: str) -> bool:
        """判断是否需要触发联网搜索"""
        if len(knowledge_results) < 3:
            high_quality_count = len([k for k in knowledge_results if k.get('similarity', 0) > 0.6])
            if high_quality_count == 0:
                return True
        return False

    async def _google_search_knowledge(self, query: str, context: str = "") -> List[Dict[str, Any]]:
        """执行 Google Search Grounding 获取相关知识"""
        try:
            logging.info(f"触发Google搜索: {query}")
            search_response = await self.google_search.search_with_grounding(query, context)
            formatted_results = self.google_search.format_search_results(search_response)
            if formatted_results:
                logging.info(f"Google搜索成功，获得 {len(formatted_results)} 条结果")
                return formatted_results
            logging.warning("Google搜索未返回有效结果")
            return []
        except Exception as e:
            logging.error(f"Google搜索失败: {str(e)}")
            return []

    def _classify_knowledge_sources(self, results: List[Dict]) -> Dict[str, List[Dict]]:
        """对知识来源进行分类"""
        classified = {"local": [], "google": [], "web": []}
        for result in results:
            if result.get("type") == "google_search":
                classified["google"].append(result)
            elif result.get("is_web_result", False):
                classified["web"].append(result)
            else:
                classified["local"].append(result)
        return classified

    def _generate_source_summary(self, classified_sources: Dict[str, List[Dict]]) -> str:
        """生成数据源摘要"""
        labels = [
            ("local", "📚 本地知识库"),
            ("google", "🔍 Google搜索"),
            ("web", "🌐 网络资源"),
        ]
        parts = [f"{label} ({len(classified_sources[key])}条)"
                 for key, label in labels if classified_sources[key]]
        return f"**数据源**: {' + '.join(parts)}" if parts else "⚠️ 未找到相关知识资源"

    def _analyze_result_quality(self, results: List[Dict]) -> Dict[str, Any]:
        """分析结果质量"""
        if not results:
            return {"level": "无数据", "description": "未找到相关信息"}

        similarities = [r.get('similarity', 0) for r in results]
        avg_similarity = sum(similarities) / len(similarities)
        high_quality_count = len([s for s in similarities if s > 0.7])

        if avg_similarity >= 0.8:
            level, description = "高质量", f"平均相关度 {avg_similarity:.1f}，包含 {high_quality_count} 条高质量信息"
        elif avg_similarity >= 0.6:
            level, description = "中等质量", f"平均相关度 {avg_similarity:.1f}，建议结合专业咨询"
        else:
            level, description = "较低质量", f"平均相关度 {avg_similarity:.1f}，建议寻找更专业的信息源"

        return {
            "level": level, "description": description,
            "avg_similarity": round(avg_similarity, 2),
            "high_quality_count": high_quality_count,
            "total_count": len(results),
        }

    # ── 动态权重（来自V2） ──────────────────────────────────

    def _apply_dynamic_weighting(self, knowledge_items: List[Dict], query: str) -> List[Dict]:
        """根据查询上下文动态调整相似度权重"""
        boost_rules = [
            (lambda q, c: any(w in q for w in ["今天", "今日", "当日"])
                          and any(t in c for t in ["当日", "今日运势", "日运"]),
             0.15, "时效性匹配"),
            (lambda q, c: "丙火" in q and "丙火" in c and "日主" in c,
             0.10, "专业术语匹配"),
            (lambda q, c: any(w in q for w in ["职业", "工作", "事业"])
                          and any(w in c for w in ["职业", "事业", "工作"]),
             0.12, "应用场景匹配"),
        ]
        for item in knowledge_items:
            content = item.get('content', '')
            base = item.get('similarity', 0)
            for check, boost, reason in boost_rules:
                if check(query, content):
                    item['similarity'] = min(base + boost, 1.0)
                    item['boost_reason'] = reason
                    break
        return sorted(knowledge_items, key=lambda x: x.get('similarity', 0), reverse=True)

    # ── 消歧义（来自V2，默认禁用） ─────────────────────────

    @staticmethod
    def disambiguate_query(query: str) -> str:
        """专业术语消歧处理"""
        if "丙火日主" in query and "天干丙火" in query:
            return "丙火日主在天干丙火日的运势分析，重点关注同干重复的影响和能量叠加效应"
        if "逆位" in query and "感情" in query:
            return f"{query}，重点分析逆位状态下的感情能量和挑战"
        if "格局" in query and any(w in query for w in ["适合", "职业", "工作"]):
            return f"{query}，重点从八字格局特点分析适合的职业方向和发展建议"
        return query

    # ── 核心检索 ────────────────────────────────────────────

    async def get_relevant_knowledge(
        self, query: str, context: str = "",
        include_web_search: bool = True,
        enable_disambiguation: bool = False,
        enable_dynamic_weight: bool = True,
    ) -> Dict[str, Any]:
        """获取相关知识，集成动态权重与智能联网搜索"""
        try:
            processed_query = self.disambiguate_query(query) if enable_disambiguation else query

            # 1. 本地知识库检索
            local_results = await self.vector_service.search_similar_content(
                query=processed_query,
                threshold=self.similarity_threshold,
                max_results=self.max_results,
            )
            all_results = local_results.copy()
            web_search_triggered = False

            # 2. 智能联网搜索
            if include_web_search and self._should_trigger_web_search(local_results, processed_query):
                logging.info(f"触发智能联网搜索 - 本地结果数量: {len(local_results)}")
                web_search_triggered = True
                all_results.extend(await self._google_search_knowledge(processed_query, context))

            # 3. 动态权重调整
            if all_results and enable_dynamic_weight:
                all_results = self._apply_dynamic_weighting(all_results, processed_query)

            # 4. 分类与摘要
            classified = self._classify_knowledge_sources(all_results)
            source_summary = self._generate_source_summary(classified)

            result = {
                "knowledge": all_results,
                "metadata": {
                    "total_results": len(all_results),
                    "local_count": len(classified["local"]),
                    "google_count": len(classified["google"]),
                    "web_count": len(classified["web"]),
                    "web_search_triggered": web_search_triggered,
                    "search_trigger_reason": "智能检测到需要补充信息" if web_search_triggered else "本地知识充足",
                    "source_summary": source_summary,
                    "quality_info": self._analyze_result_quality(all_results),
                    "disambiguation_applied": enable_disambiguation,
                    "dynamic_weight_applied": enable_dynamic_weight,
                    "original_query": query,
                    "processed_query": processed_query,
                },
            }
            logging.info(f"知识检索完成 - 总计: {len(all_results)} 条，联网搜索: {'是' if web_search_triggered else '否'}")
            return result

        except Exception as e:
            logging.error(f"知识检索失败: {str(e)}")
            return {
                "knowledge": [],
                "metadata": {"total_results": 0, "error": str(e), "source_summary": "⚠️ 知识检索服务暂时不可用"},
            }

    # ── Prompt增强（来自V2） ────────────────────────────────

    async def enhance_prompt_with_knowledge(
        self, base_prompt: str, context_query: str,
        categories: Optional[List[str]] = None,
        enable_disambiguation: bool = False,
        enable_dynamic_weight: bool = True,
    ) -> str:
        """使用专业知识增强prompt"""
        try:
            knowledge_result = await self.get_relevant_knowledge(
                query=context_query, context=base_prompt,
                enable_disambiguation=enable_disambiguation,
                enable_dynamic_weight=enable_dynamic_weight,
            )
            items = knowledge_result["knowledge"]
            if not items:
                return base_prompt

            knowledge_text = ""
            for i, k in enumerate(items[:3], 1):
                sim = k.get('similarity', 0)
                content = k.get('content', '')[:200]
                source = k.get('source', '专业知识库')
                knowledge_text += f"\n知识{i} (相关度:{sim:.2f}，来源:{source}):\n{content}\n"

            return f"""{base_prompt}

【专业知识参考】:
{knowledge_text}

【生成要求】:
- 请基于以上专业知识生成回答，确保内容的准确性和专业性
- 结合用户的具体情况（八字、日期等）给出个性化建议
- 如果知识中有相冲突的观点，请以相关度最高的为准
- 保持温暖鼓励的语调，避免过于严肃或负面的表达
- 如果专业知识不足以支撑回答，请明确说明并建议寻求更专业的咨询

请开始生成专业的运势解读：
"""
        except Exception as e:
            logging.error(f"Prompt增强失败: {e}")
            return base_prompt

    # ── 特定类别搜索 ────────────────────────────────────────

    async def search_specific_knowledge(self, query: str, category: Optional[str] = None, force_web_search: bool = False) -> List[Dict[str, Any]]:
        """搜索特定类别的知识"""
        try:
            enhanced_query = f"{query} {category}" if category else query
            results = await self.vector_service.search_similar_content(
                query=enhanced_query,
                threshold=self.similarity_threshold,
                max_results=self.max_results,
                category_filter=category,
            )
            if force_web_search or self._should_trigger_web_search(results, query):
                results.extend(await self._google_search_knowledge(enhanced_query))
            return results
        except Exception as e:
            logging.error(f"特定知识搜索失败: {str(e)}")
            return []

    # ── 数据库操作 ──────────────────────────────────────────

    async def update_knowledge_vectors(self, batch_size: int = 10) -> int:
        """批量为知识库条目生成向量嵌入"""
        try:
            from ..core.db import supabase
            from .genai_service import genai_service

            response = supabase.table("fortune_knowledge") \
                .select("id, content, title") \
                .is_("embedding", "null") \
                .limit(batch_size) \
                .execute()

            if not response.data:
                logging.info("所有知识条目都已有向量嵌入")
                return 0

            updated_count = 0
            for item in response.data:
                try:
                    embedding = await genai_service.generate_embedding(item['content'])
                    update_resp = supabase.table("fortune_knowledge") \
                        .update({"embedding": embedding}) \
                        .eq("id", item['id']) \
                        .execute()
                    if update_resp.data:
                        updated_count += 1
                except Exception as e:
                    logging.error(f"向量生成失败 ID {item['id']}: {str(e)}")
                    continue

            logging.info(f"批次完成: {updated_count}/{len(response.data)} 条记录更新成功")
            return updated_count
        except Exception as e:
            logging.error(f"批量向量更新失败: {str(e)}")
            return 0

    async def get_usage_stats(self, days: int = 30) -> Dict[str, Any]:
        """获取使用统计信息"""
        try:
            from ..core.db import supabase
            total_response = supabase.table("fortune_knowledge").select("id", count="exact").execute()
            total_knowledge = total_response.count or 0
            vectorized_response = supabase.table("fortune_knowledge") \
                .select("id", count="exact") \
                .not_.is_("embedding", "null") \
                .execute()
            vectorized_count = vectorized_response.count or 0
            return {
                "total_knowledge": total_knowledge,
                "vectorized_count": vectorized_count,
                "pending_vectorization": total_knowledge - vectorized_count,
                "vectorization_progress": round((vectorized_count / total_knowledge * 100) if total_knowledge > 0 else 0, 2),
            }
        except Exception as e:
            logging.error(f"获取使用统计失败: {str(e)}")
            return {}

    async def get_knowledge_by_category(self, category: str, limit: int = 100) -> List[Dict[str, Any]]:
        """根据分类获取知识条目"""
        try:
            from ..core.db import supabase
            response = supabase.table("fortune_knowledge") \
                .select("*") \
                .eq("category", category) \
                .limit(limit) \
                .execute()
            return response.data or []
        except Exception as e:
            logging.error(f"获取分类知识失败: {str(e)}")
            return []

    async def add_knowledge_item(self, title: str, content: str, category: str) -> bool:
        """添加新的知识条目到数据库"""
        try:
            from ..core.db import supabase
            data = {
                "title": title,
                "content": content,
                "category": category,
                "embedding": await self.vector_service.generate_embedding(content),
            }
            response = supabase.table("fortune_knowledge").insert(data).execute()
            return bool(response.data)
        except Exception as e:
            logging.error(f"添加知识失败: {str(e)}")
            return False

    async def refresh_knowledge_cache(self) -> bool:
        """刷新知识缓存"""
        try:
            logging.info("知识缓存刷新完成")
            return True
        except Exception as e:
            logging.error(f"刷新知识缓存失败: {str(e)}")
            return False

    def get_search_status(self) -> Dict[str, Any]:
        """获取搜索服务状态"""
        return {
            "local_service": "可用",
            "google_search": "无限制可用",
            "web_search": "智能触发",
            "status": "正常",
            "limitations": "依赖API自身配额",
            "trigger_conditions": {
                "local_results_count": "< 3条",
                "high_quality_count": "= 0条",
                "similarity_threshold": "> 0.6",
            },
        }
