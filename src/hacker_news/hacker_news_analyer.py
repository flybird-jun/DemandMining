from util.util import logger
import time
from .hacker_news_storage import HackerNewsStorage
from runtime.coroutine_manager import CoroutineManager, Event
import asyncio
import re
import hashlib
import json
class HackerNewsAnalyzer:
    def __init__(self, storage:HackerNewsStorage, cor_mgr:CoroutineManager):
        self._schedule_interval = 3600 # 1h分析一次
        self._last_schedule_time = 0
        self._storage = storage
        # self._exec_completed = True
        self._cor_mgr = cor_mgr
        self._low_info_words = [] #json.load()
        self._filter_rule_threshold = 1000
        self._filter_rules_completed = True
        self._comment_hash = set()

    async def _filter_rule_process_story(self, story:dict) -> None:
        for comment_id in story["comment_id"]:
            comment = await self._storage.get_comment(comment_id)
            if self._filter_rules_for_comments(comment['text']):
                await self._storage.save_filter_rule(story['story_id'], comment_id)
            else:
                logger.info(f"filter rules failed, {comment['text']}")
            
    async def _process_origin_infos(self, storys:list):
        futures = []
        for story in storys:
            future = asyncio.get_event_loop().create_future()
            futures.append(future)
            e = Event(self._filter_rule_process_story(story), future, None)
            await self._cor_mgr.send_event(e)

        for f in futures:
            await f
        
        parse_id_hwm = await self._storage.get_parsed_item_hwm()
        await self._storage.update_parsed_item_hwm(parse_id_hwm + self._filter_rule_threshold)
        
        await self._storage.save_filter_rule_hwm()
        self._filter_rules_completed = True
    
    async def scheuler(self) -> None:
        cur_time = time.time()
        if cur_time - self._last_schedule_time > self._schedule_interval:
            item_id_hwm = await self._storage.get_item_id_hwm()
            parse_id_hwm = await self._storage.get_parsed_item_hwm()

            if parse_id_hwm - item_id_hwm > self._filter_rule_threshold and self._filter_rules_completed:
                self._filter_rules_completed = False
                e = Event(self._storage.get_delta_origin_infos(parse_id_hwm, parse_id_hwm + self._filter_rule_threshold), 
                          None, self._process_origin_infos)
                await self._cor_mgr.send_event(e)
            
            # if not self._exec_completed:
            #     return
            
            # self._exec_completed = False

    # 规则过滤, 明显无价值的评论
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
        # 6. 大量引用
        lines = text.splitlines()
        if lines is not None:
            quote_lines = [line for line in lines if line.strip().startswith(">")]
            if len(quote_lines) / len(lines) > 0.7:
                return False 
        # 7. 检测重复
        normalize_text = text.lower().strip()
        normalize_text = re.sub(r"\s+", " ", normalize_text)
        h = hashlib.md5(normalize_text.encode("utf-8")).hexdigest()
        if h in self._comment_hash:
            return False
        self._comment_hash.add(h)
        # 8. 低价值信息模板
        if normalize_text in self._low_info_words:
            return False
        return True