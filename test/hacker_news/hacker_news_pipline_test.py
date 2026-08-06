import pytest
import asyncio
from hacker_news.hacker_news_pipline import HackerNewsPipline
from runtime.coroutine_manager import Event
@pytest.mark.asyncio(loop_scope="class")
class TestHackerNewsPipline:
    async def pipline_stop(self):
        await asyncio.sleep(300)
        HackerNewsPipline.pipline_running = False
    async def test_run(self, clean_env):
        pipline = HackerNewsPipline()
        await pipline._cor_mgr.send_event(Event(self.pipline_stop(), None, None))
        await pipline.run()
        
