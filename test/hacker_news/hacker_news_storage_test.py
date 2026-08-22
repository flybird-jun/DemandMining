import pytest
import pytest_asyncio
from pathlib import Path
from util.util import *
from hacker_news.hacker_news_storage import HackerNewsStorage
@pytest.mark.asyncio(loop_scope="class")
class TestHackerNewsStorage:
    @pytest_asyncio.fixture(scope="function", loop_scope="class", autouse = True, name = "storage")
    async def setup(self, clean_env):
        hacker_news_storage = HackerNewsStorage()
        await hacker_news_storage.init()
        yield hacker_news_storage
        await hacker_news_storage.destory()

    async def test_save_item(self, storage):
        story = {
            "id": 49299605,
            "time": 1786719600,
            "type": "story",
            "url": "https://huggingface.co/Qwen/Qwen3.8-27B-FP8",
            "title": "Qwen 3.8 27B",
            "summary": "Qwen 3.8 27B summary"
        }
        await storage.save_item(story)

        comment = {
                    "id": 49305335,
                    "time": 1786746139,
                    "type": "comment",
                    "text": "Credit where it",
                    "parent": 49299605
                  }
        await storage.save_item(comment)

    async def test_item_id_hwm(self, storage):
        # init() 会插入初始高水位 49300000
        assert await storage.get_item_id_hwm() == 49300000
        await storage.update_item_id_hwm(49350000)
        assert await storage.get_item_id_hwm() == 49350000

    async def test_parsed_item_hwm(self, storage):
        assert await storage.get_parsed_item_hwm() == 0
        await storage.update_parsed_item_hwm(2000)
        assert await storage.get_parsed_item_hwm() == 2000

    async def test_save_story_text(self, storage):
        item_id = 49400300
        text = "This is the full story text for testing."
        await storage.save_story_text(item_id, text)

        file_path = storage._raw_data_path / f"{item_id}"
        try:
            assert file_path.exists()
            assert file_path.read_text(encoding="utf-8") == text
        finally:
            if file_path.exists():
                file_path.unlink()