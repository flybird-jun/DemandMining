import signal
import asyncio
import logging
from util.util import setup_logging
from runtime.coroutine_manager import CoroutineManager
from .hacker_news_storage import HackerNewsStorage
from .hacker_news_ai_client import HackerNewsAiClient
from .hacker_news_task import HackerNewsCrawlTask, HackerNewsFilterTask, HackerNewsDemandObjectTask, HackerNewsProductScoreTask, HackerNewsProductSolutionTask
import pdb

logger = logging.getLogger(__name__)
class HackerNewsPipline:
    pipline_running = True
    def __init__(self):
        self._cor_num = 50
        self._storage = HackerNewsStorage()
        self._cor_mgr = CoroutineManager(self._cor_num)
        self._ai_client = HackerNewsAiClient()

        task_class = [
           # HackerNewsCrawlTask,
           HackerNewsFilterTask,
           HackerNewsDemandObjectTask,
           HackerNewsProductScoreTask,
           HackerNewsProductSolutionTask,
        ]
        self._task = [cls(self._storage, self._cor_mgr, self._ai_client) for cls in task_class]

    async def run(self) -> None:
        logger.warning("HackerNewsPipline run")

        HackerNewsPipline.pipline_running = True
        await self._storage.init()
        for task in self._task:
            await task.run()
        self._cor_mgr.run()
        while HackerNewsPipline.pipline_running:
            await asyncio.sleep(1)
        await self._stop()
    async def _stop(self) -> None:
        for task in self._task:
            await task.stop()
        await self._cor_mgr.stop()
        await self._storage.destroy()
        await self._cor_mgr.destroy()
        await self._ai_client.destroy()
        logger.warning("HackerNewsPipline stop")

async def hacker_news_main():
    pipline = HackerNewsPipline()
    await pipline.run()

def debug(sig, frame):
    pdb.Pdb().set_trace(frame)

if __name__ == "__main__":
    def handle_signal(signum, frame):
        print("handle_signal reciver")
        HackerNewsPipline.pipline_running = False
    print("main start")
    setup_logging()
   # signal.signal(signal.SIGINT, handle_signal)
   # signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGUSR1, debug)
    asyncio.run(hacker_news_main())
    
    