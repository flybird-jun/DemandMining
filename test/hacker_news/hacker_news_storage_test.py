import pytest
import pytest_asyncio
import json
import random
from pathlib import Path
from hacker_news.hacker_news_storage import HackerNewsStorage, HackerNewsTable, HackerNewsAuxTable
@pytest.mark.asyncio(loop_scope="class")
class TestHackerNewsStorage:
    @pytest_asyncio.fixture(scope="function", loop_scope="class", autouse = True, name = "storage")
    async def setup(self, clean_env):
        hacker_news_storage = HackerNewsStorage()
        
        await hacker_news_storage.init()
        yield hacker_news_storage
        await hacker_news_storage.destroy()

    @pytest.fixture(scope="class", name = "test_data")
    def test_data(self):
        file_path = Path(__file__).resolve().parent / "test_data.json"

        with open(file_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        return result["hacker_news_storage_test"]
    
    @pytest.mark.parametrize("table", HackerNewsTable)
    async def test_hwm(self, table, storage):
        await storage.update_hwm(table, True, 49350000)
        assert await storage.fetch_hwm(table, True) == 49350000

        await storage.update_hwm(table, False, 49360000)
        assert await storage.fetch_hwm(table, False) == 49360000

    async def test_insert_fetch(self, storage, test_data):
        data = test_data["test_insert_fetch"]
        for table, items in data.items():
            for item in items:
                if table == HackerNewsTable.hacker_news.name:
                    await storage.insert(HackerNewsTable.hacker_news, item)
                elif (table == HackerNewsTable.filter.name or table == HackerNewsTable.score.name or table == HackerNewsAuxTable.story_summary.name
                      or table == HackerNewsAuxTable.hwm.name):
                    if table in HackerNewsTable.__members__:
                        await storage.insert(HackerNewsTable[table], *item)
                    else:
                        await storage.insert(HackerNewsAuxTable[table], *item)
                elif table == HackerNewsTable.demand_object.name:
                    await storage.insert(HackerNewsTable.demand_object, item, [0] * 1024)

        for table in HackerNewsTable:
            await storage.fetch(table, 1, 40000)

    async def test_story_text(self, storage):
        item_id = 49400300
        text = "This is the full story text for testing."
        await storage.save_story_text(item_id, text)

        read_text = await storage.get_story_text(item_id)
        assert read_text == text

        file_path = storage._raw_data_path / f"{item_id}"
        try:
            assert file_path.exists()
            assert file_path.read_text(encoding="utf-8") == text
        finally:
            if file_path.exists():
                file_path.unlink()
    async def test_fetch_sequence_id(self, storage):
        await storage.insert(HackerNewsTable.filter, 100, "i love three things")
        await storage.insert(HackerNewsTable.filter, 1020, "i love three things")
        await storage.insert(HackerNewsTable.filter, 1030, "i love three things")
        result = await storage.fetch_sequence_id(HackerNewsTable.filter)
        assert result == 3
    async def test_check_demand_repeat(self, storage):
        item = {}
        await storage.insert(HackerNewsTable.demand_object, item, [0.1] * 1024)
        repeat = await storage.check_demand_repeat([0.1] * 1024)
        assert repeat
        repeat = await storage.check_demand_repeat([*([0.1] * 512), *([0.3] * 512)])
        assert not repeat
    async def test_save_solution(self, storage):
        await storage.save_solution(10002, "i love three things")