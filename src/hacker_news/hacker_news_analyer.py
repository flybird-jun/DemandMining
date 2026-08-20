import aiohttp
from common.dbms import Dbms
class HackerNewsAnalyzer:
    def __init__(self, storage:Dbms):
        self._session : aiohttp.ClientSession
        self._schedule_interval = 300 # 300s 收集一次
        self._last_schedule_time = 0
        self._storage = storage
    async def scheuler(self):
        pass