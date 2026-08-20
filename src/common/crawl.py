"""网络层: 控制抓取行为。

Crawl 类对外提供静态入口, 把 robots 限速 + 实际抓取编排在一起, 调用方无需
关心 sleep / retry / header 注入。
"""
from __future__ import annotations

import asyncio
from typing import Any, ClassVar

import aiohttp

from common import aio_http_wrap
from common.robot_checker import RobotsChecker

class Crawl:
    @staticmethod
    async def _request(session: aiohttp.ClientSession, url: str) -> aiohttp.ClientResponse | None:
       
        allowed = await RobotsChecker.check(session,url)
        if not allowed:
            return None
        return await aio_http_wrap.request(session, url)
    @staticmethod
    async def get_text(session: aiohttp.ClientSession, url: str) -> str:
        response = await Crawl._request(session, url)
        return await response.text(errors = "replace") if not response is None else ""