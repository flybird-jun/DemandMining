import pytest
import pytest_asyncio
import asyncio
from unittest.mock import patch
from pathlib import Path
from collector.extract.hacker_news_collector import HackerNewsCollector
from runtime.coroutine_manager import CoroutineManager
from storage.storage import Storage
from util.util import *

@pytest.mark.asyncio(loop_scope="class")
class TestHackerNewsCollector:
    @pytest_asyncio.fixture(scope="class", loop_scope="class", autouse = True, name = "collector")
    async def setup(self):
        storage = Storage(config["raw_data_path"] + "test", config["database_path"] + "test")
        await storage.init("test", "test")
        # 执行一遍删除所有数据，防止用例之间的干扰
        try:
            async with storage._pool.acquire() as conn, conn.transaction():
                await conn.execute("Drop Table comment;")
                await conn.execute("Drop Table story;")
                await conn.execute("Drop Table storyhwm;")
        except Exception as e:
            print(f"{e}")
        await storage.destory()
        await storage.init("test", "test")

        cor_mgr = CoroutineManager(10)
        cor_mgr._scheduler_period = 1
        await cor_mgr.run()
        hacker_news_collector = HackerNewsCollector(storage, cor_mgr)
        #await hacker_news_collector.init()
        yield hacker_news_collector
        #await hacker_news_collector.destroy()
        await cor_mgr.stop()
        await storage.destory()
        await hacker_news_collector.destroy()
        await cor_mgr.destory()
    async def test_hacker_news_collector(self, collector, monkeypatch):
        async def mock_get_max_item_id(session):
            return 49300000 + 100
        monkeypatch.setattr("collector.api.hacker_news_api.HackerNewsApi.get_max_item_id", mock_get_max_item_id)

        collector._schedule_interval = 2
        await collector.init()
        await asyncio.sleep(2)
        while sum(x is not None for x in collector._cor_mgr._cor_handle) != 0:
            #print(collector._cor_mgr._cor_handle)
            await asyncio.sleep(2)
        await asyncio.sleep(10)
        print(collector._cor_mgr._cor_handle)
        item_hwm = await collector._storage.get_item_id_hwm()
        assert item_hwm == (49300000 + 100)

        
        