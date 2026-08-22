from util.util import logger
import time
from .hacker_news_storage import HackerNewsStorage

class HackerNewsAnalyzer:
    def __init__(self, storage:HackerNewsStorage):
        self._schedule_interval = 3600 # 1h分析一次
        self._last_schedule_time = 0
        self._storage = storage
        self._exec_completed = True
    
    async def scheuler(self) -> None:
        cur_time = time.time()
        if cur_time - self._last_schedule_time > self._schedule_interval:
            if not self._exec_completed:
                return
            
            self._exec_completed = False
            
    # 过滤掉无价值的评论，保留有价值的评论。
    async def _filter_valuable_comments(self) -> None:
        pass