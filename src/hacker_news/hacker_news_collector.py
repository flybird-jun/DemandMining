import aiohttp
from .hacker_news_storage import HackerNewsStorage
from .hacker_news_clean import HackerNewsClean
from .hacker_news_api import HackerNewsApi
from util.util import logger
import time
from runtime.coroutine_manager import CoroutineManager, Event
class HackerNewsCollector:
    def __init__(self, cor_mgr:CoroutineManager, storage:HackerNewsStorage) -> None:
        self._session : aiohttp.ClientSession
        self._schedule_interval = 300 # 300s 收集一次
        self._last_schedule_time = 0
        self._storage = storage
        self._cor_mgr = cor_mgr
        self._db_item_hwm = 0
        self._batch_completed_count = 200
        self._batch_count = 200

    async def init(self) -> None:
        # await self._storage.init()
        timeout = aiohttp.ClientTimeout(total = 30, connect = 10, sock_connect = 10, sock_read = 20)
        self._session = aiohttp.ClientSession(timeout = timeout)
        self._cor_mgr.register_scheduler_loop_func(self.scheduler)

    async def destroy(self) -> None:
        await self._session.close()
        # await self._storage.destory()
    
    async def _get_item_callback(self, data:dict | None) -> None:
        if data is None:
            self._batch_completed_count += 1
            return
        
        try:
            is_valid = HackerNewsClean.clean(data)
            if is_valid:
                await self._storage.save_item(data)
            else:
                logger.info(f"f{data['type']} item_id:f{data['id']} discard")

        except Exception as e:
            logger.exception(f"story item failed error = {type(e).__name__}:'{e}', data = {data}")

        if self._batch_completed_count == self._batch_count - 1:
            await self._storage.update_item_id_hwm(self._db_item_hwm + self._batch_count)
        self._batch_completed_count += 1
            
    # 注册到协程管理器的scheduler函数
    async def scheduler(self) -> None:
        try:
            cur_time = time.time()
            if cur_time - self._last_schedule_time > self._schedule_interval:
                # 上一次发布的event还没执行完毕, 本次就不发布event了
                if self._batch_count != self._batch_completed_count:
                    logger.warning(f"expected={self._batch_count}, completed={self._batch_completed_count}")
                    return
                
                self._batch_completed_count = 0
                self._last_schedule_time = cur_time
                remote_max_item_id = await HackerNewsApi.get_max_item_id(self._session)
                self._db_item_hwm = await self._storage.get_item_id_hwm()
                # 数量小于batch_count, 返回
                if remote_max_item_id - self._db_item_hwm < self._batch_count:
                    logger.warning(f"remote = {remote_max_item_id}, item_hwm = {self._db_item_hwm}")
                    return
                
                for item_id in range(self._db_item_hwm + 1, remote_max_item_id + 1):
                    cor_obj = HackerNewsApi.get_item(self._session, item_id)
                    e = Event(cor_obj, None, self._get_item_callback)
                    await self._cor_mgr.send_event(e)
        except Exception as e:
            logger.exception(f"HackerNewsCollector scheduler failed, {type(e).__name__}:'{e}' ")


