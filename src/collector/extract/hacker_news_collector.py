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
from util import util
logger = util.logger

class HackerNewsCollector(Collector):
    ITEM_ID_QSIZE = 50
    def __init__(self, item_id_qsize: int = ITEM_ID_QSIZE) -> None:
        super().__init__(item_id_qsize, api = HackerNewsApi)
        self._session : aiohttp.ClientSession

    async def init(self) -> None:
        timeout = aiohttp.ClientTimeout(
            total=30,
            connect=10,
            sock_connect=10,
            sock_read=20,
        )
        self._session = aiohttp.ClientSession(timeout = timeout)
    @staticmethod
    def get_text(item:dict) -> str:
        return "title:" + item["title"] + "\n" + item["text"]
    
    @staticmethod
    def _recursive_add_comment(comment_item:dict, comment:list):
        if comment_item["text"] != "" and comment_item["text"] != "[dead]":
            comment.append(comment_item["text"])
        for sub_comment in comment_item["comment"]:
            HackerNewsCollector._recursive_add_comment(sub_comment, comment)

    @staticmethod 
    def get_comments(item:dict) -> list[list[str]]:
        comments = []
        for sub_comment in item["comment"]:
            comment:list = []
            HackerNewsCollector._recursive_add_comment(sub_comment, comment)
            comments.append(comment)
        return comments

    async def destroy(self) -> None:
        await self._session.close()

    async def producer_item_ids(self) -> None:
        new_stories_ids = await HackerNewsApi.get_top_stories(self._session)
        for i, item_id in enumerate(new_stories_ids, 1):
            await self._queue.put(item_id)
        await self._queue.put(None)

    async def producer_item(self, out_queue: asyncio.Queue) -> None:
        while True:
            try:
                item_id = await self._queue.get()
                print(f"start produce {item_id}")
                if item_id is None:
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
            except Exception as e:
                continue

    async def _get_article(self, url:str) -> str:
        if not url:
            logger.info(f"url is None")
            return ""
        try:
            html = await Crawl.get_text(self._session, url)
        except Exception:
            logger.info(f"_get_article:get {url} fail")
            return ""
        return TextClean.clean_article(html)

    async def _recursive_get_comment_list(self, kids: list) -> list:
        out: list[dict] = []
        for kid in kids:
            kid_json = await HackerNewsApi.get_item(self._session, kid)
            if not kid_json:
                logger.info(f"comment item_id = {kid} is not json")
                continue
            text = TextClean.clean_comment(kid_json.get("text", ""))
            out.append({
                "text": text,
                "comment": await self._recursive_get_comment_list(
                    kid_json.get("kids", [])
                ) if kid_json.get("kids") else [],
            })
        return out
