import pytest
import pytest_asyncio
import asyncio
import json
from pathlib import Path
from hacker_news.hacker_news_task import HackerNewsCrawlTask, HackerNewsFilterTask, HackerNewsDemandObjectTask, HackerNewsProductScoreTask, HackerNewsProductSolutionTask
from hacker_news.hacker_news_storage import HackerNewsStorage, HackerNewsTable
from hacker_news.hacker_news_ai_client import HackerNewsAiClient
from runtime.coroutine_manager import CoroutineManager

@pytest.mark.asyncio(loop_scope="class")
class TestHackerNewsTask:
    @pytest_asyncio.fixture(scope="class", loop_scope="class", autouse = True, name = "storage")
    async def setup_storage(self, clean_env):
        storage = HackerNewsStorage()
        await storage.init()
        yield storage
        await storage.destroy()
    @pytest_asyncio.fixture(scope="class", loop_scope="class", autouse = True, name = "cor_mgr")
    async def setup_coroutine_mgr(self, storage):
        cor_mgr = CoroutineManager(50)
        cor_mgr.run()
        yield cor_mgr
        await cor_mgr.stop()
    @pytest_asyncio.fixture(scope="class", loop_scope="class", autouse = True, name = "client")
    async def setup_ai_client(self):
        client = HackerNewsAiClient()
        yield client
        await client.destroy()
    @pytest_asyncio.fixture(scope="class", loop_scope="class", autouse = True, name = "test_data")
    async def setup_test_data(self):
        file_path = Path(__file__).resolve().parent / "test_data.json"
        
        with open(file_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        return result["hacker_news_task_test"]
    async def test_crawl_task(self, storage, cor_mgr, client):
        task = HackerNewsCrawlTask(storage, cor_mgr, client)
        await task.run()
        await asyncio.sleep(30)
        await task.stop()
        high_hwm = await storage.fetch_hwm(HackerNewsTable.hacker_news, False)
        assert high_hwm > (49300000 + 100 * 3)
    async def test_filter_task(self, storage, cor_mgr, client, test_data):
        task = HackerNewsFilterTask(storage, cor_mgr, client)
        data_set = test_data['test_filter_task']
        for data in data_set:
            await storage.insert(HackerNewsTable.hacker_news, data)
        await storage.update_hwm(HackerNewsTable.hacker_news, False, 49303000)
        await storage.update_hwm(HackerNewsTable.hacker_news, True, 49300000)
        await task.run()
        await asyncio.sleep(30)
        await task.stop()
        high_hwm = await storage.fetch_hwm(HackerNewsTable.filter, False)
        assert high_hwm > 1 and high_hwm < 40
        low_hwm = await storage.fetch_hwm(HackerNewsTable.hacker_news, True)
        assert low_hwm == 49303000
    async def test_demand_object_task(self, storage, cor_mgr, client, test_data):
        task = HackerNewsDemandObjectTask(storage, cor_mgr, client)
        data_set = test_data['test_demand_object_task']
        for data in data_set:
            await storage.insert(HackerNewsTable.filter, data['item_id'], data['text'])
        await storage.update_hwm(HackerNewsTable.filter, False, 102)
        await storage.update_hwm(HackerNewsTable.filter, True, 1)
        await task.run()
        await asyncio.sleep(30)
        await task.stop()
        high_hwm = await storage.fetch_hwm(HackerNewsTable.demand_object, False)
        assert high_hwm == 20
        low_hwm = await storage.fetch_hwm(HackerNewsTable.filter, True)
        assert low_hwm == 101
    async def test_product_score_task(self, storage, cor_mgr, client, test_data):
        task = HackerNewsProductScoreTask(storage, cor_mgr, client)
        data_set = test_data['test_product_score_task']
        for data in data_set:
            await storage.insert(HackerNewsTable.demand_object, data, [0] * 1024)
        await storage.update_hwm(HackerNewsTable.demand_object, False, 102)
        await storage.update_hwm(HackerNewsTable.demand_object, True, 0)
        await task.run()
        await asyncio.sleep(30)
        await task.stop()
        high_hwm = await storage.fetch_hwm(HackerNewsTable.score, False)
        assert high_hwm == 20
        low_hwm = await storage.fetch_hwm(HackerNewsTable.demand_object, True)
        assert low_hwm == 100

    async def test_product_solution_task(self, storage, cor_mgr, client, test_data):
            task = HackerNewsProductSolutionTask(storage, cor_mgr, client)
            data_set = test_data['test_product_solution_task']
            for data in data_set['demand_object']:
                await storage.insert(HackerNewsTable.demand_object, data, [0] * 1024)
            for data in data_set['score']:
                await storage.insert(HackerNewsTable.score, *data)

            await storage.update_hwm(HackerNewsTable.score, False, 102)
            await storage.update_hwm(HackerNewsTable.score, True, 0)
            await task.run()
            await asyncio.sleep(30)
            await task.stop()
            high_hwm = await storage.fetch_hwm(HackerNewsTable.score, True)
            assert high_hwm == 100
          