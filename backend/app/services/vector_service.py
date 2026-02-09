import logging
from typing import List, Dict, Any, Optional

from app.core.db import supabase
from app.core.genai_service import genai_service


class VectorService:
    def __init__(self):
        self.supabase = supabase

    async def store_diary_embedding(self, user_id: str, diary_id: str, content: str):
        """生成日记内容的向量并存储到Supabase"""
        try:
            embedding = await genai_service.generate_embedding(content)
            data_to_insert = {
                "user_id": user_id,
                "diary_id": diary_id,
                "content_chunk": content[:1000],
                "embedding": embedding,
            }
            response = self.supabase.table("diary_embeddings").insert(data_to_insert).execute()
            if not response.data:
                logging.error(f"🔥 向量存储失败 - diary_id: {diary_id}")
        except Exception as e:
            logging.error(f"🔥 日记向量化存储异常 - diary_id: {diary_id}, 错误: {e}", exc_info=True)
            raise

    async def search_similar_diaries(
        self,
        user_id: str,
        query: str,
        threshold: float = 0.7,
        max_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """搜索相似的日记内容"""
        if not query or not query.strip():
            return []
        try:
            query_embedding = await genai_service.generate_embedding(query)
            response = self.supabase.rpc(
                "search_diary_entries_by_vector",
                {
                    "user_id_param": user_id,
                    "query_embedding": query_embedding,
                    "max_results": max_results,
                },
            ).execute()

            if not response.data:
                logging.info(f"日记检索无结果 - user: {user_id}, query: {query}")
                return []

            results = []
            for row in response.data:
                results.append(
                    {
                        "diary_id": row["diary_id"],
                        "content_preview": row["content"][:200],
                        "similarity": float(row["similarity"]),
                        "metadata": {},
                        "created_at": row["created_at"],
                    }
                )
            logging.info(f"日记检索成功 - user: {user_id}, query: {query}, 结果数: {len(results)}")
            return results

        except Exception as e:
            logging.error(f"日记检索失败 - user: {user_id}, query: {query}, 错误: {e}")
            try:
                fallback_response = (
                    self.supabase.table("diary_entries")
                    .select("id, content, created_at")
                    .eq("user_id", user_id)
                    .ilike("content", f"%{query}%")
                    .limit(max_results)
                    .execute()
                )
                if fallback_response.data:
                    results = []
                    for row in fallback_response.data:
                        results.append(
                            {
                                "diary_id": row["id"],
                                "content_preview": row["content"][:200],
                                "similarity": 0.5,
                                "metadata": {},
                                "created_at": row["created_at"],
                            }
                        )
                    logging.info(f"使用文本匹配搜索日记 - 结果数: {len(results)}")
                    return results
            except Exception as fallback_error:
                logging.error(f"日记降级检索也失败: {fallback_error}")
            return []

    async def search_similar_content(
        self,
        query: str,
        threshold: float = 0.7,
        max_results: int = 5,
        category_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """在知识库中搜索相似内容"""
        try:
            query_embedding = await genai_service.generate_embedding(query)
            response = self.supabase.rpc(
                "search_knowledge_by_vector",
                {
                    "query_embedding": query_embedding,
                    "similarity_threshold": threshold,
                    "max_results": max_results,
                    "category_filter": category_filter,
                },
            ).execute()
            if not response.data:
                return []
            results = []
            for row in response.data:
                results.append(
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "content": row["content"],
                        "category": row["category"],
                        "similarity": float(row["similarity"]),
                        "type": "local_knowledge",
                    }
                )
            return results
        except Exception as e:
            logging.error(f"知识库检索失败 - query: {query}, 错误: {e}")
            return []


vector_service = VectorService()
