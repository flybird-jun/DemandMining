import pytest
import pytest_asyncio
import aiohttp
from hacker_news.hacker_news_api import HackerNewsApi
@pytest.mark.asyncio(loop_scope="class")
class TestHackerNewsApi:
    @pytest_asyncio.fixture(scope="class", loop_scope="class", autouse = True, name = "session")
    async def setup(self):
        timeout = aiohttp.ClientTimeout(total=15)
        session = aiohttp.ClientSession(timeout = timeout)
        yield session
        await session.close()

    async def test_get_max_item_id(self, session):
        max_id = await HackerNewsApi.get_max_item_id(session)
        assert isinstance(max_id, int)
        assert max_id > 49308436

    async def test_update(self, session):
        update_info = await HackerNewsApi.get_updates(session)
        assert "items" in update_info
        assert "profiles" in update_info
        assert isinstance(update_info["items"], list)

    async def test_get_top_stories(self, session):
        top_story_ids = await HackerNewsApi.get_top_stories(session)
        assert isinstance(top_story_ids, list)

    async def test_get_new_stories(self, session):
        new_story_ids = await HackerNewsApi.get_new_stories(session)
        assert isinstance(new_story_ids, list)
        assert len(new_story_ids) > 0
        assert all(isinstance(item_id, int) for item_id in new_story_ids)
        assert len(new_story_ids) <= 500

    async def test_get_best_stories(self, session):
        best_story_ids = await HackerNewsApi.get_best_stories(session)
        assert isinstance(best_story_ids, list)
        assert all(isinstance(item_id, int) for item_id in best_story_ids)

    async def test_get_ask_stories(self, session):
        ask_story_ids = await HackerNewsApi.get_ask_stories(session)
        assert isinstance(ask_story_ids, list)
        assert all(isinstance(item_id, int) for item_id in ask_story_ids)
        assert len(ask_story_ids) <= 200

    async def test_get_show_stories(self, session):
        show_story_ids = await HackerNewsApi.get_show_stories(session)
        assert isinstance(show_story_ids, list)
        assert all(isinstance(item_id, int) for item_id in show_story_ids)
        assert len(show_story_ids) <= 200

    async def test_get_job_stories(self, session):
        job_story_ids = await HackerNewsApi.get_job_stories(session)
        assert isinstance(job_story_ids, list)
        assert all(isinstance(item_id, int) for item_id in job_story_ids)
        assert len(job_story_ids) <= 200

    async def test_get_item(self, session):
        # 评论
        item_id = 49309057 # 48820709 dead comment, 49309057 used
        item = await HackerNewsApi.get_item(session, item_id)
        assert isinstance(item, dict)
        assert item["id"] == item_id
        assert "type" in item
        assert item["type"] == "comment"
        # story
        item_id = 49299605 # 48868688 dead story, 49299605 used
        item = await HackerNewsApi.get_item(session, item_id)
        assert isinstance(item, dict)
        assert item["id"] == item_id
        assert "type" in item
        assert item["type"] == "story"

    async def test_get_item_nonexistent(self, session):
        # HN API 对不存在的 id 返回 null -> Python None
        item = await HackerNewsApi.get_item(session, 0)
        assert item is None