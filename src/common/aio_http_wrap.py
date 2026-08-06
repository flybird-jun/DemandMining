from __future__ import annotations
import asyncio
from typing import Any, Mapping
import aiohttp

# 默认网络参数
MAX_RETRIES = 3
SLEEP_FACTOR = 0.3
TIMEOUT = 10.0

async def request(session:aiohttp.ClientSession, url: str) -> aiohttp.ClientResponse:
    if session is None:
        raise Exception("session is none")
    for attempt in range(MAX_RETRIES):
        try:
            resp = await session.get(url)
            resp.raise_for_status()
            return resp
        except aiohttp.ClientResponseError as e:
            if 400 <= e.status < 500:
                raise
        await asyncio.sleep(SLEEP_FACTOR * (2 ** attempt))
    raise Exception(f"request {url} error")


async def get_json(session: aiohttp.ClientSession, url: str) -> Any:
    resp = await request(session, url)
    try:
        return await resp.json(content_type=None)
    finally:
        resp.release()


async def get_text(session: aiohttp.ClientSession,url: str,errors: str = "replace") -> str:
    resp = await request(session, url)
    try:
        return await resp.text(errors=errors)
    finally:
        resp.release()
