"""HackerNewsCollector: 编排 HackerNewsApi + Crawl + TextClean。

完全静态化/外部依赖注入:
    - api 提供原始数据
    - crawl 提供正文抓取能力
    - text_clean 负责 HTML -> 纯文本
"""
from __future__ import annotations
import asyncio
from typing import Any
import aiohttp
from collector.api.hacker_news_api import HackerNewsApi
from collector.collector import Collector
from collector.extract.text_clean import TextClean
from collector.net.crawl import Crawl
import logging
logger = logging.getLogger(__name__)

class HackerNewsCollector(Collector):
    ITEM_ID_QSIZE = 50
    INVALID_ITEM_ID = -1

    def __init__(self, item_id_qsize: int = ITEM_ID_QSIZE) -> None:
        super().__init__(item_id_qsize, api = HackerNewsApi)
        self._session : aiohttp.ClientSession

    async def init(self) -> None:
        self._session = aiohttp.ClientSession()
    async def destroy(self) -> None:
        await self._session.close()

    async def producer_item_ids(self) -> None:
        new_stories_ids = await HackerNewsApi.get_top_stories(self._session)
        for i, item_id in enumerate(new_stories_ids, 1):
            await self._queue.put(item_id)
        await self._queue.put(HackerNewsCollector.INVALID_ITEM_ID)

    async def producer_item(self, out_queue: asyncio.Queue) -> None:
        while True:
            item_id = await self._queue.get()
            if item_id == HackerNewsCollector.INVALID_ITEM_ID:
                await self._queue.put(item_id)
                break

            item_json = await HackerNewsApi.get_item(self._session, item_id)
            if not item_json or item_json.get("type") != "story":
                logger.info(f"get {item_id} failed")
                continue
            text = ""
            if "url" in item_json:
                text = await self._get_article(item_json["url"]) if not "text" in item_json else item_json["text"]
            else:
                logger.info("{item_id} don't have url: {item_json}")
            out: dict[str, Any] = {
                "item_id":item_id,
                "title": item_json.get("title", ""),
                "url": item_json.get("url", ""),
                "text": text,
                "comment": await self._recursive_get_comment_list(item_json.get("kids", []))
            }
            await out_queue.put(out)

    async def _get_article(self, url:str) -> str:
        if not url:
            logger.info(f"url is None")
            return ""
        try:
            html = await Crawl.get_text(self._session, url)
        except Exception:
            logger.info(f"_get_article:get {url} fail")
            return ""
        return TextClean.extract_article(html)

    async def _recursive_get_comment_list(self, kids: list) -> list:
        out: list[dict] = []
        for kid in kids:
            kid_json = await HackerNewsApi.get_item(self._session, kid)
            if not kid_json:
                continue
            out.append({
                "text": kid_json.get("text", ""),
                "comment": await self._recursive_get_comment_list(
                    kid_json.get("kids", [])
                ) if kid_json.get("kids") else [],
            })
        return out
