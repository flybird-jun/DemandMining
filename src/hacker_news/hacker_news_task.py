import aiohttp
import asyncio
import logging
import time
import datetime
import re
import hashlib
from openai import APIStatusError, InternalServerError
from abc import ABC, abstractmethod
from common.crawl import Crawl
from common.text_clean import TextClean
from .hacker_news_storage import HackerNewsStorage, HackerNewsTable, HackerNewsAuxTable
from .hacker_news_ai_client import HackerNewsAiClient
from .hacker_news_api import HackerNewsApi
from runtime.coroutine_manager import CoroutineManager, Event

logger = logging.getLogger(__name__)

class _Task(ABC):
    def __init__(self, storage:HackerNewsStorage, cor_mgr:CoroutineManager, ai_client:HackerNewsAiClient, table:HackerNewsTable, batch_count:int, poll_interval:int):
        self._ai_client = ai_client
        self._storage = storage
        self._cor_mgr = cor_mgr
        self._running = True
        self._table = table
        self._previous_low_hwm = 0
        self._previous_high_hwm = 0
        self._batch_count = batch_count
        self._last_poll_at = 0
        self._poll_interval = poll_interval

    async def run(self) -> None:
        if self._table.previous is None:
            self._previous_low_hwm = await self._storage.fetch_hwm(self._table, False)
            self._previous_high_hwm = await self._fetch_previous_high_hwm()
        else:
            self._previous_low_hwm = await self._storage.fetch_hwm(self._table.previous, True)
            self._previous_high_hwm = await self._fetch_previous_high_hwm()
        
        self._running = False
        
        self._cor_mgr.register_scheduler_loop_func(self._schedule)

    async def stop(self) -> None:
        self._cor_mgr.unregister_scheduler_loop(self._schedule)
        while self._running:
            await asyncio.sleep(1)

    async def _schedule(self):
        gap = self._previous_high_hwm - self._previous_low_hwm
        if gap > self._batch_count:
            if self._table == HackerNewsTable.filter and gap > self._batch_count * 2:
                await self._trigger(self._previous_low_hwm, self._previous_low_hwm + self._batch_count * 2)
            else:
                await self._trigger(self._previous_low_hwm, self._previous_low_hwm + self._batch_count)

        cur = time.time()
        if cur - self._last_poll_at > self._poll_interval:
            self._previous_high_hwm = await self._fetch_previous_high_hwm()
            self._last_poll_at = cur

    async def _trigger(self, min_id:int, max_id:int) -> None:
        if self._running:
            return
        self._running = True
        e = Event(self._task(min_id, max_id), None, None)
        await self._cor_mgr.send_event(e)

    async def _fetch_previous_high_hwm(self) -> int:
        assert self._table.previous is not None
        return await self._storage.fetch_hwm(self._table.previous, False)
    
    async def _after_task(self, max_id:int) -> None:
        try:
            high_hwm = await self._storage.fetch_sequence_id(self._table)
            await self._storage.update_hwm(self._table, False, high_hwm)
            assert self._table.previous is not None
            await self._storage.update_hwm(self._table.previous, True, max_id)
            logger.warning(f"update hwm high_hwm = {high_hwm}, max_id = {max_id}")
            self._previous_low_hwm = max_id
        except Exception as e:
            raise e

    @abstractmethod
    async def _event(self, element):
        pass

    async def _wait_for_items_complete(self, items:list):
        futures = []
        for item in items:
            future = asyncio.Future()
            futures.append(future)
            e = Event(self._event(item), future, None)
            await self._cor_mgr.send_event(e)
        retry_items = []
        sleep_time = 3600
        for i, f in enumerate(futures):
            try:
                await f
            except (APIStatusError, InternalServerError) as e:
                if e.status_code == 402 or e.status_code == 500 or e.status_code == 529:
                    # logger.warning(f"chat rate quota limit, collected event item={items[i]}")
                    if e.status_code == 529:
                        sleep_time = 60
                    else:
                        sleep_time = 3600
                    retry_items.append(items[i])
                else:
                    logger.exception(f"{self._table.name} event index={i} failed with APIStatusError status_code={e.status_code}")
            except Exception:
                logger.exception(f"{self._table.name} event index={i} failed")
        if not retry_items:
            return
        await asyncio.sleep(sleep_time)
        await self._wait_for_items_complete(retry_items)
                    
    async def _task(self, min_id:int, max_id:int) -> None:
        start1 = time.time()
        if self._table.previous is None:
            items = [i for i in range(min_id + 1, max_id + 1)]
        else:
            items = await self._storage.fetch(self._table.previous, min_id, max_id)
        start = time.time()
        print(f"{datetime.datetime.now()}:{self._table} task start, count = {len(items)}, fetch cost time = {start - start1}")

        if self._table == HackerNewsTable.filter:
            batch = 10
        else:
            batch = 5

        for i in range(0, len(items), batch):
            await self._wait_for_items_complete(items[i:i + batch])
        await self._after_task(max_id)

        end = time.time()
        tasks = asyncio.all_tasks()
        print(f"{datetime.datetime.now()}:{self._table} distribute task cost time = {end - start}, cur task count = {len(tasks)}")
        self._running = False

    def _embedding_str(self, data:dict):
        return (f"problem:{data['problem']}\n"
                f"context:{data['context']}\n"
                f"job_to_be_done:{data['job_to_be_done']}\n"
                f"current_solution:{data['current_solution']}\n"
                f"pain_points:{data['demand_type']}")

class HackerNewsCrawlTask(_Task):
    def __init__(self, storage:HackerNewsStorage, cor_mgr:CoroutineManager, ai_client:HackerNewsAiClient):
        # 不精准的估计，hacker news 1s中可以请求150个
        # 1800s 查询一次
        super().__init__(storage, cor_mgr, ai_client, HackerNewsTable.hacker_news, 100, 1800) 

        timeout = aiohttp.ClientTimeout(total = 30, connect = 10, sock_connect = 10, sock_read = 20)
        self._session = aiohttp.ClientSession(timeout = timeout)
    async def _fetch_previous_high_hwm(self) -> int:
        return await HackerNewsApi.get_max_item_id(self._session)
    async def _after_task(self, max_id:int) -> None:
        await self._storage.update_hwm(self._table, False, max_id)
        self._previous_low_hwm = max_id
    async def _event(self, element:int):
        try:
            item = await HackerNewsApi.get_item(self._session, element)
            if item is None:
                logger.warning(f"request item {element}, return None")
                return
        except Exception as e:
            logger.exception(f"request_item {element} failed error = {type(e).__name__}:'{e}'")
            raise
        try:
            if "dead" not in item and "deleted" not in item:
                if item["type"] == "story" and "url" in item:
                    await self._crawl_and_summary_text(element, item['url'])
                if item['type'] == "story" or item['type'] == "comment":
                    result = self._transform_to_storage(item)
                    await self._storage.insert(self._table, result)    
            else:
                logger.warning(f"{item['type']} item_id:{item['id']} discard, dead or deleted")

        except Exception as e:
            logger.exception(f"request_item parse {element} failed, item = {item} error = {type(e).__name__}:'{e}'")
            raise

    def _transform_to_storage(self, item:dict):
        insert_item = {
            'id': item['id'],
            'time': item['time'],
            'type': item['type']
        }
        if item['type'] == "story":
            insert_item['title'] = item['title']
            if "url" in item:
                insert_item['url'] = item['url']
        else:
            insert_item['text'] = item['text']
            insert_item['parent'] = item['parent']
        return insert_item

    async def _crawl_and_summary_text(self, item_id:int, url:str):
        text = await Crawl.get_text(self._session, url)
        if text != "":
            text = TextClean.clean_html(text)
            await self._storage.save_story_text(item_id, text)
            summary = await self._ai_client.summary_text(text)
            await self._storage.insert(HackerNewsAuxTable.story_summary, item_id, summary)

class HackerNewsFilterTask(_Task):
    def __init__(self, storage:HackerNewsStorage, cor_mgr:CoroutineManager, ai_client:HackerNewsAiClient):
        # hacker_news 中累积的评论数达到5000才触发
        # 1h 检查一次
        super().__init__(storage, cor_mgr, ai_client, HackerNewsTable.filter, 5000, 3600)
        self._comment_hash = set()

    async def _event(self, element) -> None:
        # 1. 规则过滤: 先把明显无价值的评论剔除
        filter_rule = {}
        comments = []
        for c in element['comments']:
            if self._filter_rules_for_comments(c['text']):
                comments.append(c)
        # 2. 语义过滤
        if len(comments) > 0:
            filter_rule['comments'] = comments
            if element['story_id'] is not None:
                filter_rule['text'] = await self._storage.fetchrow_from_summary_text(element['story_id'])
                row = await self._storage.fetchrow_from_hacker_news(element['story_id'])
                filter_rule['title'] = row['title']
            
            results = await self._ai_client.extract_valuable_comments(filter_rule)
            for result in results:
                await self._storage.insert(self._table, result['item_id'], result['text'])

    def _filter_rules_for_comments(self, text:str) -> bool:
        # 1. 空文本
        if text is None or text.strip() == "":
            return False
        # 2. 极短文本
        text = text.strip()
        if len(text) < 15:
            return False
        # 3. emoji符号
        cleaned = re.sub(r"[\W_]+", "", text, flags=re.UNICODE)
        if cleaned == "":
            return False
        # 4. 纯URL
        urls = re.findall(r"https?://\S+", text)
        if urls is not None:
            url_length = sum(len(u) for u in urls)
            if url_length / len(text) > 0.8:
                return False
        # 5. 代码检测
        if "```" in text: # markdown
            return False
        symbols = ["{", "}", "(", ")", ";", "=>", "==", "!=", "def ", "class ", "import ", "function "]
        count = sum(text.count(s) for s in symbols)
        if count / len(text) > 0.15:
            return False
        # 6. 检测重复
        normalize_text = text.lower().strip()
        normalize_text = re.sub(r"\s+", " ", normalize_text)
        h = hashlib.md5(normalize_text.encode("utf-8")).hexdigest()
        if h in self._comment_hash:
            return False
        self._comment_hash.add(h)
        return True
class HackerNewsDemandObjectTask(_Task):
    def __init__(self, storage:HackerNewsStorage, cor_mgr:CoroutineManager, ai_client:HackerNewsAiClient):
        # 100 个 filter 评论抽取一次
        # 6h 抽取一次demand object
        super().__init__(storage, cor_mgr, ai_client, HackerNewsTable.demand_object, 100, 3600 * 2)
    
    async def _event(self, element):
        struct_datas = await self._ai_client.extract_demand_object(element)
        for struct_data in struct_datas:
            # text = self._embedding_str(struct_data)
            # text_embedding = await self._ai_client.embedding(text)
            # if await self._storage.check_demand_repeat(text_embedding):
            #     print("demand repeat")
            #     continue
            await self._storage.insert(self._table, struct_data, [0] * 1024)
class HackerNewsProductScoreTask(_Task):

    def __init__(self, storage:HackerNewsStorage, cor_mgr:CoroutineManager, ai_client:HackerNewsAiClient):
        # 200 个 demand_object 做一次产品分析
        # 6h 做一次产品分析
        super().__init__(storage, cor_mgr, ai_client, HackerNewsTable.score, 100, 3600 * 2)

    async def _event(self, element):
        result = await self._ai_client.product_score(element)
        await self._storage.insert(self._table, element['item_id'], result['score'])
class HackerNewsProductSolutionTask(_Task):
    def __init__(self, storage:HackerNewsStorage, cor_mgr:CoroutineManager, ai_client:HackerNewsAiClient):
        # 5 个 高评分评论做一次产品方案
        # 8h 做一次产品分析
        super().__init__(storage, cor_mgr, ai_client, HackerNewsTable.solution, 100, 3600 * 2)

    async def _event(self, element):
        solution = await self._ai_client.output_solution(element)
        await self._storage.save_solution(element['item_id'], solution)
