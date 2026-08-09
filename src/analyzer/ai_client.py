"""大模型分析模块 (基于 openai 官方 SDK)。

通过 base_url 切换 provider (OpenAI / DeepSeek / 通义千问 / 自建网关等都吃
OpenAI 兼容协议)。prompt 模板从 analyzer/prompt/ 目录加载。

接口:
    llm = LLM(api_url, api_key)
    text = await llm.article_parse(article)
    summary = await llm.article_aggregation_parse(articles)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI
from openai import APIError, APIConnectionError, RateLimitError


_PROMPT_DIR = Path(__file__).resolve().parent / "prompt"
_ARTICLE_PROMPT_PATH = _PROMPT_DIR / "article.prompt"
_ARTICLE_AGG_PROMPT_PATH = _PROMPT_DIR / "article_aggregation.prompt"

logger = logging.getLogger(__name__)


class AiClient:
    """封装 AsyncOpenAI 客户端, 暴露两个 prompt 模板方法。"""

    def __init__(self,api_url: str, api_key: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=api_url.rstrip("/"))
        self._article_prompt = self._read_prompt(_ARTICLE_PROMPT_PATH)
        self._article_agg_prompt = self._read_prompt(_ARTICLE_AGG_PROMPT_PATH)

    async def article_parse(self, article: str) -> str:
        """单篇正文分析, 使用 article.prompt 模板。"""
        if not article:
            logger.warning("article_parse called with empty article")
            return ""
        prompt = self._article_prompt.format(article=article)
        return await self._chat(prompt)

    async def article_aggregation_parse(self, articles: list[str]) -> str:
        """多篇正文聚合分析, 使用 article_aggregation.prompt 模板。"""
        if not articles:
            logger.warning("article_aggregation_parse called with empty list")
            return ""
        joined = "\n\n---\n\n".join(articles)
        prompt = self._article_agg_prompt.format(articles=joined)
        return await self._chat(prompt)

    @staticmethod
    def _read_prompt(path: Path) -> str:
        if not path.exists():
            raise FileNotFoundError(f"prompt not found: {path}")
        return path.read_text(encoding="utf-8")

    async def _chat(self, prompt: str) -> str:
        """调用 chat.completions.create 并返回首条 message content。"""
        try:
            resp = await self._client.chat.completions.create(
                model="MiniMax-V3",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
        except (APIError, APIConnectionError, RateLimitError) as exc:
            logger.error("LLM call failed: %s", exc)
            raise

        if not resp.choices:
            logger.error("LLM returned empty choices: %s", resp)
            raise RuntimeError("LLM returned no choices")
        return resp.choices[0].message.content or ""
