from __future__ import annotations
import aiohttp
from collector.api.hacker_news_api import HackerNewsApi
from collector.extract.text_clean import TextClean
from collector.net.crawl import Crawl
from util.util import logger, ParentException
import time
from storage.storage import Storage
from queue import Queue
from runtime.coroutine_manager import CoroutineManager, Event
from analyzer.ai_client import AiClient
class HackerNewsCollector:
    def __init__(self, storage:Storage, cor_mgr:CoroutineManager, ai_client:AiClient) -> None:
        self._session : aiohttp.ClientSession
        self._schedule_interval = 300 # 300s 收集一次
        self._last_schedule_time = 0
        self._storage = storage
        self._cor_mgr = cor_mgr
        self._ai_client = ai_client
        self._story_miss_queue = Queue() # 没找到父评论或id 挂到链上后续再插入
        self._db_item_hwm = 0
        self._remote_max_item_id = 0
        self._batch_completed_count = 0

    async def init(self) -> None:
        timeout = aiohttp.ClientTimeout(total = 30, connect = 10, sock_connect = 10, sock_read = 20)
        self._session = aiohttp.ClientSession(timeout = timeout)
        self._cor_mgr.register_scheduler_loop_func(self.scheduler)

    async def destroy(self) -> None:
        await self._session.close()
    
    async def _get_item_callback(self, data:dict) -> None:
        try:
            if data["type"] == "story":
                text = await self._get_story_text(data["url"])
                await self._storage.save_story_text(data["id"], text)
                data["summary"] = await self._ai_client.summary_text("title:" + data["title"] + ", Text:" + text)
                await self._storage.save_story(data)
            
            elif data["type"] == "comment":
                data["text"] = TextClean.clean_comment(data["text"])
                await self._storage.save_comment(data)
            else:
                logger.info(f"f{data['type']} item_id:f{data['id']} discard")
            
            self._batch_completed_count += 1
        except ParentException:
            if data["parent"] <= self._db_item_hwm:
                story_info = {
                    "id":data["parent"],
                    "time": 0,
                    "title":"",
                    "type":"story",
                    "url":"",
                    "summary":""
                }
                await self._storage.save_story(story_info)
                await self._get_item_callback(data)
                logger.info(f"{data['parent']} construct empty")
            else:
                self._story_miss_queue.put(data)
        except Exception as e:
            logger.exception(f"story item failed error = {type(e).__name__}:'{e}', data = {data}")
            self._batch_completed_count += 1 # 异常不再重试，但是event已经执行完毕了，所以也要加1
            
    async def _process_miss_queue(self):
        item_list = []
        while not self._story_miss_queue.empty():
            item_list.append(self._story_miss_queue.get())
        
        item_list.sort(key = lambda x: x["id"])
        for item in item_list:
            await self._get_item_callback(item)
        # 这些都是异常的item, 打印出来，后续定位
        while not self._story_miss_queue.empty():
            data = self._story_miss_queue.get()
            logger.error(f"{data} parent is None")
    # 注册到协程管理器的scheduler函数
    async def scheduler(self) -> None:
        # 将缺失story_id的评论重新插入到storage
        qsize = self._story_miss_queue.qsize()
        try:
            for i in range(0, qsize):
                data = self._story_miss_queue.get()
                await self._get_item_callback(data)

            cur_time = time.time()
            if cur_time - self._last_schedule_time > self._schedule_interval:
                # 需要将上一次没插回去的数据处理干净
                await self._process_miss_queue()
                # 上一次发布的event还没执行完毕, 本次就不发布event了
                if self._remote_max_item_id - self._db_item_hwm != self._batch_completed_count:
                    logger.warning(f"expected={self._remote_max_item_id - self._db_item_hwm}, completed={self._batch_completed_count}")
                    return
                
                if self._remote_max_item_id != 0:
                    await self._storage.update_item_id_hwm(self._remote_max_item_id)
                self._batch_completed_count = 0
                self._last_schedule_time = cur_time
                self._remote_max_item_id = await HackerNewsApi.get_max_item_id(self._session)
                self._db_item_hwm = await self._storage.get_item_id_hwm()

                for item_id in range(self._db_item_hwm + 1, self._remote_max_item_id + 1):
                    cor_obj = HackerNewsApi.get_item(self._session, item_id)

                    e = Event(cor_obj, None, self._get_item_callback)
                    await self._cor_mgr.send_event(e)
        except Exception as e:
            logger.exception(f"HackerNewsCollector scheduler failed, {type(e).__name__}:'{e}' ")

    async def _get_story_text(self, url:str) -> str:
        if not url:
            logger.info(f"url is None")
            return ""
        try:
            html = await Crawl.get_text(self._session, url)
        except Exception:
            logger.info(f"_get_article:get {url} fail")
            return ""
        return TextClean.clean_article(html)

