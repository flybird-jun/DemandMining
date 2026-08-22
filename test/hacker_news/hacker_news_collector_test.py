import pytest
import pytest_asyncio
import asyncio
from unittest.mock import patch
from pathlib import Path
from hacker_news import HackerNewsCollector, HackerNewsStorage
from runtime.coroutine_manager import CoroutineManager
from common.dbms import Dbms
from util.util import *

@pytest.mark.asyncio(loop_scope="class")
class TestHackerNewsCollector:
    @pytest_asyncio.fixture(scope="class", loop_scope="class", autouse = True, name = "collector")
    async def setup(self, clean_env):
        cor_mgr = CoroutineManager(10)
        cor_mgr._scheduler_period = 1
        await cor_mgr.run()
        storage = HackerNewsStorage()
        await storage.init()
        hacker_news_collector = HackerNewsCollector(cor_mgr, storage)
        await hacker_news_collector.init()
        yield hacker_news_collector

        await cor_mgr.stop()
        await hacker_news_collector.destroy()
        await cor_mgr.destory()
        await storage.destory()
    async def test_hacker_news_collector(self, collector, monkeypatch):
        async def mock_get_max_item_id(session):
            return 49300000 + 200
        monkeypatch.setattr("hacker_news.hacker_news_api.HackerNewsApi.get_max_item_id", mock_get_max_item_id)

        collector._schedule_interval = 2
        await collector.init()
        await asyncio.sleep(2)
        while sum(x is not None for x in collector._cor_mgr._cor_handle) != 0:
            await asyncio.sleep(2)
        await asyncio.sleep(10)
        print(collector._cor_mgr._cor_handle)
        item_hwm = await collector._storage.get_item_id_hwm()
        assert item_hwm == (49300000 + 200)

        
        