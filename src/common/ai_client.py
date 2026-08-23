from __future__ import annotations

from pathlib import Path
from typing import Any
from openai import AsyncOpenAI
from openai import APIError, APIConnectionError, RateLimitError
import asyncio
from util import util
logger = util.logger

class AiClient:
   
    
    def __init__(self, api_url: str, api_key: str, model:str = "MiniMax-M3") -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=api_url.rstrip("/"))
        self._model = model
        self._summary_text_prompt = self._read_prompt(AiClient._SUMMARY_TEXT_PATH)
        self._extract_comments_prompt = self._read_prompt(AiClient._EXTRACT_COMMENTS_PATH)
        self._aggre_analyzer_prompt = self._read_prompt(AiClient._EXTRACT_COMMENTS_PATH)

    @staticmethod
    def _read_prompt(path: Path) -> str:
        if not path.exists():
            raise FileNotFoundError(f"prompt not found: {path}")
        return path.read_text(encoding="utf-8")

    async def chat(self, prompt: str, content:str, temperature:float = 0.2) -> str:
        while True:
            try:
                resp = await self._client.responses.create(
                    model="MiniMax-M3",
                    input=[{"role": "user", "content": content}],
                    instructions = prompt,
                    temperature = temperature
                )
            except RateLimitError as e:
                await asyncio.sleep(3)
            except (APIError, APIConnectionError) as e:
                logger.error("LLM call failed: %s", e)
                raise e
            except Exception as e:
                raise e
            else:
                return resp.output_text
    