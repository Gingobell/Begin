import os
import google.generativeai as genai
from typing import List
import asyncio
import logging

from app.config import DEFAULT_CHAT_MODEL, DEFAULT_EMBEDDING_MODEL


class GenAIService:
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set")
        genai.configure(api_key=api_key)
        try:
            self.model = genai.GenerativeModel(DEFAULT_CHAT_MODEL)
            logging.info(f"✅ 成功初始化模型: {DEFAULT_CHAT_MODEL}")
        except Exception as e:
            logging.error(f"❌ 初始化模型 {DEFAULT_CHAT_MODEL} 失败: {e}")
            raise ValueError(f"无法初始化 Gemini 模型: {DEFAULT_CHAT_MODEL}")
        self.embedding_model = f"models/{DEFAULT_EMBEDDING_MODEL}"

    async def generate_embedding(self, text: str, output_dimensionality: int = 768) -> List[float]:
        """为输入文本生成向量表示"""
        try:
            result = await asyncio.to_thread(
                genai.embed_content,
                model=self.embedding_model,
                content=text,
                task_type="retrieval_document",
                output_dimensionality=output_dimensionality,
            )
            if isinstance(result, dict):
                return result["embedding"]
            elif hasattr(result, "embedding"):
                embedding = result.embedding
                if isinstance(embedding, list):
                    return embedding
                elif hasattr(embedding, "values"):
                    return list(embedding.values)
                else:
                    return list(embedding)
            else:
                return result
        except Exception as e:
            logging.error(f"❌ 向量生成失败: {e}")
            raise

    async def generate_text(self, prompt: str) -> str:
        """根据输入的prompt生成文本内容"""
        try:
            response = await self.model.generate_content_async(prompt)
            finish_reason_value = response.candidates[0].finish_reason
            if response.candidates and finish_reason_value in [1, 2]:
                return "".join(
                    part.text
                    for part in response.candidates[0].content.parts
                    if hasattr(part, "text")
                )
            block_reason = (
                response.prompt_feedback.block_reason.name
                if response.prompt_feedback and response.prompt_feedback.block_reason
                else "未知"
            )
            error_message = f"AI内容生成失败. 阻塞原因: {block_reason}, 完成原因代码: {finish_reason_value}"
            logging.error(error_message)
            return error_message
        except Exception as e:
            logging.error(f"调用AI服务时发生未知错误: {e}", exc_info=True)
            return f"调用AI服务时发生未知错误: {e}"


genai_service = GenAIService()
