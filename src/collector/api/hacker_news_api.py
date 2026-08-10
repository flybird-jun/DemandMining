"""Hacker News 官方 API(v0) 异步封装。
文档: https://github.com/HackerNews/API, 所有端点都在 https://hacker-news.firebaseio.com/v0/ 下
"""
from __future__ import annotations

from typing import Any

import aiohttp

from collector.net import aio_http_wrap

class HackerNewsApi:
    """HackerNews v0 API 的静态封装。"""

    BASE_URL: str = "https://hacker-news.firebaseio.com/v0"

    # ---------------- Items ----------------

    @staticmethod
    async def get_item(
        session: aiohttp.ClientSession,
        item_id: int,
    ) -> dict | None:
        """获取单个 item (story/comment/job/poll/pollopt), id 不存在时返回 None。"""
        url = f"{HackerNewsApi.BASE_URL}/item/{item_id}.json"
        return await aio_http_wrap.get_json(session, url)
    # ---------------- Live Data ----------------

    @staticmethod
    async def get_max_item_id(session: aiohttp.ClientSession) -> int:
        """当前最大的 item id。"""
        url = f"{HackerNewsApi.BASE_URL}/maxitem.json"
        return await aio_http_wrap.get_json(session, url)

    @staticmethod
    async def get_top_stories(session: aiohttp.ClientSession) -> list[int]:
        """最多 500 条最热帖子 id。"""
        url = f"{HackerNewsApi.BASE_URL}/topstories.json"
        return await aio_http_wrap.get_json(session, url)

    @staticmethod
    async def get_new_stories(session: aiohttp.ClientSession) -> list[int]:
        """最多 500 条最新帖子 id。"""
        url = f"{HackerNewsApi.BASE_URL}/newstories.json"
        return await aio_http_wrap.get_json(session, url)

    @staticmethod
    async def get_best_stories(session: aiohttp.ClientSession) -> list[int]:
        """最佳帖子 id 列表。"""
        url = f"{HackerNewsApi.BASE_URL}/beststories.json"
        return await aio_http_wrap.get_json(session, url)

    @staticmethod
    async def get_ask_stories(session: aiohttp.ClientSession) -> list[int]:
        """最多 200 条 Ask HN 帖子 id。"""
        url = f"{HackerNewsApi.BASE_URL}/askstories.json"
        return await aio_http_wrap.get_json(session, url)

    @staticmethod
    async def get_show_stories(session: aiohttp.ClientSession) -> list[int]:
        """最多 200 条 Show HN 帖子 id。"""
        url = f"{HackerNewsApi.BASE_URL}/showstories.json"
        return await aio_http_wrap.get_json(session, url)

    @staticmethod
    async def get_job_stories(session: aiohttp.ClientSession) -> list[int]:
        """最多 200 条 Job 帖子 id。"""
        url = f"{HackerNewsApi.BASE_URL}/jobstories.json"
        return await aio_http_wrap.get_json(session, url)

    @staticmethod
    async def get_updates(session: aiohttp.ClientSession) -> dict[str, Any]:
        """最近发生变化的 item 和 user。"""
        url = f"{HackerNewsApi.BASE_URL}/updates.json"
        return await aio_http_wrap.get_json(session, url)
