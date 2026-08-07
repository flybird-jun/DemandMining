"""Collector 抽象基类, 描述 “生产者/消费者” 流水线的最小协议。

不依赖任何网络/HTTP 实现, 只描述协程队列交互。
"""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any


class Collector(ABC):
    def __init__(self, queue_size: int, api: Any = None) -> None:
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=queue_size)
        self._api = api

    @abstractmethod
    async def producer_item_ids(self) -> None:
        """往 self._queue 写入需要抓取的 item id, 以 INVALID_ITEM_ID 结束。"""
        raise NotImplementedError

    @abstractmethod
    async def producer_item(self, out_queue: asyncio.Queue) -> None:
        """从 self._queue 读 id, 抓数据, 写入 out_queue。"""
        raise NotImplementedError
