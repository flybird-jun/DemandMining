import pytest
import pytest_asyncio
from pathlib import Path
from util.util import *
from storage.storage import storage
@pytest.mark.asyncio(loop_scope="class")
class TestStorage:

    @pytest_asyncio.fixture(scope="function", loop_scope="class", autouse = True, name = "storage_")
    async def setup(self):
        storage_ = storage(config["raw_data_path"] + "test", config["database_path"] + "test")
        await storage_.init("test", "test")
        # 执行一遍删除所有数据，防止用例之间的干扰
        try:
            async with storage_._pool.acquire() as conn, conn.transaction():
                await conn.execute("Drop Table comment;")
                await conn.execute("Drop Table story;")
                await conn.execute("Drop Table storyhwm;")
                print(f"drop")
        except Exception as e:
            print(f"{e}")
        await storage_.destory()
        await storage_.init("test", "test")
        yield storage_

        await storage_.destory()
    async def test_save_item(self, storage_):
        story = {
            "id": 49299605,
            "time": 1786719600,
            "type": "story",
            "url": "https://huggingface.co/Qwen/Qwen3.8-27B-FP8",
            "title": "Qwen 3.8 27B",
            "summary": "Qwen 3.8 27B summary"
        }
        await storage_.save_item(story)

        comment = {
                    "id": 49305335,
                    "time": 1786746139,
                    "type": "comment",
                    "text": "Credit where it",
                    "parent": 49299605
                  }
        await storage_.save_item(comment)

        comment = {
                    "id": 49311329,
                    "time": 1786807196,
                    "type": "comment",
                    "text": "correctly reason throught one of my private benchmarks",
                    "parent": 49305335
                  }
        await storage_.save_item(comment)

        comment = {
                    "id": 49311339,
                    "time": 1786807192,
                    "type": "comment",
                    "text": "wrong comment",
                    "parent": 49305336
                  }
        try:
            await storage_.save_item(comment)
        except ParentException as e:
            assert True
        else:
            assert False


    async def test_get_story_id_hwm_initial(self, storage_):
        # init() 会插入初始高水位 49300000
        assert await storage_.get_story_id_hwm() == 49300000

    async def test_update_story_hwm(self, storage_):
        await storage_.update_story_hwm(49350000)
        assert await storage_.get_story_id_hwm() == 49350000

        await storage_.update_story_hwm(49310000)
        assert await storage_.get_story_id_hwm() == 49350000

    async def test_update_ai_parse_time(self, storage_):
        await storage_.update_ai_parse_time(1786730000)
        await storage_.update_ai_parse_time(1786710000)
        assert await storage_._get_ai_parse_time() == 1786730000

    async def test_get_story_ids(self, storage_):
        stories = [
            {"id": 49400101, "time": 1786719100, "type": "story", "url": "u1", "title": "t1", "summary": "s1"},
            {"id": 49400102, "time": 1786719200, "type": "story", "url": "u2", "title": "t2", "summary": "s2"},
            {"id": 49400103, "time": 1786719300, "type": "story", "url": "u3", "title": "t3", "summary": "s3"},
        ]
        for s in stories:
            await storage_.save_item(s)

        await storage_.update_ai_parse_time(1786719200)

        ids = await storage_.get_story_ids()
        assert 49400103 in ids
        assert 49400101 not in ids
        assert 49400102 not in ids

    async def test_get_story(self, storage_):
        story = {
            "id": 49400200,
            "time": 1786719400,
            "type": "story",
            "url": "https://example.com",
            "title": "Test Story",
            "summary": "Test Summary",
        }
        await storage_.save_item(story)

        # 一级评论挂在 story 上
        await storage_.save_item({
            "id": 49400201, "time": 1786746140, "type": "comment",
            "text": "First comment", "parent": 49400200,
        })
        # 二级评论挂在评论上，应仍然归到同一个 story
        await storage_.save_item({
            "id": 49400202, "time": 1786746141, "type": "comment",
            "text": "Reply comment", "parent": 49400201,
        })

        result = await storage_.get_story(49400200)
        assert "Test Story" in result["text"]
        assert "Test Summary" in result["text"]
        assert "First comment" in result["comment"]
        assert "Reply comment" in result["comment"]

    async def test_save_story_text(self, storage_):
        item_id = 49400300
        text = "This is the full story text for testing."
        await storage_.save_story_text(item_id, text)

        file_path = storage_._raw_data_path / f"{item_id}"
        try:
            assert file_path.exists()
            assert file_path.read_text(encoding="utf-8") == text
        finally:
            if file_path.exists():
                file_path.unlink()