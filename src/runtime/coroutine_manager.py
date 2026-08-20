import asyncio
import types
import inspect
from collections.abc import Callable
from typing import Any
from util.util import *

class Event:
    def __init__(self, cor_object:types.CoroutineType, future:asyncio.Future | None, callback:Callable[..., Any] | None):
        self.cor_object = cor_object
        self.future = future
        self.callback = callback

class CoroutineManager:
    def __init__(self, max_cor_num:int):
        self._max_cor_num = max_cor_num
        self._queue = asyncio.Queue(max_cor_num * 2)
        self._cor_handle : list[asyncio.Task | None] = [None] * self._max_cor_num
        self._running = True
        self._scheduler_handle : asyncio.Task | None = None
        self._monitor_callback:list[tuple[Callable[..., Any], tuple[Any, ...]]] = []
        self._scheduler_period = 30
    # 监控是否有协程退出，回收_cor_handle资源
    async def scheduler_loop(self, *args):
        while self._running:
            await asyncio.sleep(self._scheduler_period)
            for callback, args in self._monitor_callback:
                try:
                    result = callback(*args)
                    if inspect.isawaitable(result):
                        await result
                except Exception as e:
                    logger.exception(f"execute {callback} failed, {type(e).__name__}: {e}")

    async def run(self):
        self._scheduler_handle = asyncio.create_task(self.scheduler_loop())

    # 注册到monitor线程的任务必须能短暂执行完毕
    def register_scheduler_loop_func(self, callback:Callable[..., Any], *args):
        self._monitor_callback.append((callback, args))

    def _worker_done(self, task: asyncio.Task):
        index = self._cor_handle.index(task)
        self._cor_handle[index] = None

    async def task_main(self) -> None:
        while True:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout = 3)
            except asyncio.TimeoutError:
                return
            if event is None:
                await self._queue.put(event)
                return
            
            try:
                result = await event.cor_object
                
                if event.future is not None:
                    event.future.set_result(result)
                if event.callback is not None:
                    result_ = event.callback(result)
                    if inspect.isawaitable(result_):
                        await result_

            except Exception as e:
                if event.future is not None and not event.future.done():
                    event.future.set_exception(e)
                if event.callback is not None:
                    event.callback(None)
                logger.exception(f"worker execute failed, {repr(event.cor_object)}")
            

    async def send_event(self, event:Event) -> None:
        for i, cor in enumerate(self._cor_handle):
            if cor is None:
                cor_handle = asyncio.create_task(self.task_main())
                self._cor_handle[i] = cor_handle
                cor_handle.add_done_callback(self._worker_done)
                break
        await self._queue.put(event)

    async def stop(self):
        await self._queue.put(None)
        self._running = False
        for cor in self._cor_handle:
            if cor is not None:
                await cor
        
    async def destory(self):
        # 释放task引用
        self._cor_handle = []
        if self._scheduler_handle is not None:
            await self._scheduler_handle
        self._scheduler_handle = None