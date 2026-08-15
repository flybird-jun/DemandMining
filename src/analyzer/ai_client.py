from __future__ import annotations

from pathlib import Path
from typing import Any
from openai import AsyncOpenAI
from openai import APIError, APIConnectionError, RateLimitError
import asyncio
from util import util
logger = util.logger

class AiClient:
    _PROMPT_DIR = Path(__file__).resolve().parent / "prompt"
    _SUMMARY_TEXT_PATH = _PROMPT_DIR / "summary_text.prompt"
    _EXTRACT_COMMENTS_PATH = _PROMPT_DIR / "extract_comments.prompt"
    _AGGRE_ANALYZER_PATH = _PROMPT_DIR / "aggregation_analyzer.prompt"
    
    def __init__(self,api_url: str, api_key: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=api_url.rstrip("/"))
        self._summary_text_prompt = self._read_prompt(AiClient._SUMMARY_TEXT_PATH)
        self._extract_comments_prompt = self._read_prompt(AiClient._EXTRACT_COMMENTS_PATH)
        self._aggre_analyzer_prompt = self._read_prompt(AiClient._EXTRACT_COMMENTS_PATH)

    # 抽取有效评论
    async def extract_comments(self, article: str) -> str:
        if not article:
            logger.warning("article_parse called with empty article")
            return ""
        return await self._chat(self._extract_comments_prompt, article, 0.3)
    # 总结正文
    async def summary_text(self, text:str) -> str:
        if not text or text == "":
            logger.warning("main text is empty")
        return await self._chat(self._summary_text_prompt, text)
    # 聚合评论进行分析
    async def aggregation_analyzer(self, articles: list[str]) -> str:
        if not articles:
            logger.warning("article_aggregation_parse called with empty list")
            return ""
       # joined = "\n\n---\n\n".join(articles)
        return await self._chat(self._aggre_analyzer_prompt, f"{articles}", 0.7)

    @staticmethod
    def _read_prompt(path: Path) -> str:
        if not path.exists():
            raise FileNotFoundError(f"prompt not found: {path}")
        return path.read_text(encoding="utf-8")

    async def _chat(self, prompt: str, entry:str, temperature:float = 0.2) -> str:
        while True:
            try:
                resp = await self._client.responses.create(
                    model="MiniMax-M3",
                    input=[{"role": "user", "content": entry}],
                    instructions = prompt,
                    temperature = temperature
                )
            except RateLimitError as e:
                await asyncio.sleep(3)
            except (APIError, APIConnectionError) as exc:
                logger.error("LLM call failed: %s", exc)
                raise
            else:
                return resp.output_text
    