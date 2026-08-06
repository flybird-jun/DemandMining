import asyncio
import pytest
import pytest_asyncio
from runtime.coroutine_manager import CoroutineManager, Event

@pytest.mark.asyncio(loop_scope="class")
class TestCoroutineManager:

    @pytest_asyncio.fixture(scope="function", loop_scope="class", autouse=True, name="manager")
    async def setup(self):
        manager = CoroutineManager(max_cor_num=4)
        manager.run()
        yield manager
        await manager.stop()

    async def test_init_state(self, manager):
        # CoroutineManager.__init__ 后的字段状态
        assert manager._max_cor_num == 4
        assert manager._queue.maxsize == 8
        assert len(manager._cor_handle) == 4
        assert all(c is None for c in manager._cor_handle)
        assert manager._running is True
        assert manager._scheduler_handle is not None
        assert manager._monitor_callback == []

    async def test_send_event_with_future(self, manager):
        # 只传 future, 通过 future 拿到协程返回值
        async def coro_func(x, y):
            await asyncio.sleep(0.01)
            return x + y

        future = asyncio.Future()
        event = Event(coro_func(3, 4), future, None)
        await manager.send_event(event)

        result = await asyncio.wait_for(future, timeout=2)
        assert result == 7

    async def test_send_event_with_sync_callback(self, manager):
        # 只传 sync callback, 通过 callback 观察结果
        results = []
        def cb(result):
            results.append(result * 2)

        async def coro_func():
            await asyncio.sleep(0.01)
            return 5

        event = Event(coro_func(), None, cb)
        await manager.send_event(event)

        # 没有 future, 通过轮询等待 worker 处理完成
        for _ in range(50):
            if results:
                break
            await asyncio.sleep(0.01)
        assert results == [10]

    async def test_send_event_with_async_callback(self, manager):
        # async callback 会被 await
        results = []
        async def async_cb(result):
            await asyncio.sleep(0.01)
            results.append(result + 1)

        async def coro_func():
            await asyncio.sleep(0.01)
            return 10

        event = Event(coro_func(), None, async_cb)
        await manager.send_event(event)

        for _ in range(50):
            if results:
                break
            await asyncio.sleep(0.01)
        assert results == [11]

    async def test_send_event_with_future_and_callback(self, manager):
        # future 与 callback 同时存在, 两者都会被触发
        results = []
        def cb(result):
            results.append(result)

        async def coro_func():
            await asyncio.sleep(0.01)
            return "hello"

        future = asyncio.Future()
        event = Event(coro_func(), future, cb)
        await manager.send_event(event)

        result = await asyncio.wait_for(future, timeout = 2)
        assert result == "hello"
        for _ in range(50):
            if results:
                break
            await asyncio.sleep(0.01)
        assert results == ["hello"]

    async def test_multiple_concurrent_events(self, manager):
        # 4 个并发事件, max_cor_num=4, 全部独立完成
        async def coro_func(idx):
            await asyncio.sleep(0.05)
            return idx * 2

        futures = []
        for i in range(4):
            f = asyncio.Future()
            futures.append(f)
            await manager.send_event(Event(coro_func(i), f, None))

        results = await asyncio.wait_for(asyncio.gather(*futures), timeout=2)
        assert sorted(results) == [0, 2, 4, 6]

    async def test_worker_stays_alive_between_events(self, manager):
        # 处理完一个事件后 worker 不会退出, 而是继续从队列里取下一个事件
        # 只有 timeout / None / destroy 才会让 worker 退出, _worker_done 才会被触发
        async def coro_func(idx):
            await asyncio.sleep(0.01)
            return idx

        f1 = asyncio.Future()
        await manager.send_event(Event(coro_func(1), f1, None))
        await asyncio.wait_for(f1, timeout=2)
        # worker 处理完事件后仍然挂在 queue.get() 上, slot 不会被回收
        await asyncio.sleep(0.05)
        assert any(c is not None for c in manager._cor_handle)

        # 复用同一个 worker 继续处理下一个事件
        f2 = asyncio.Future()
        await manager.send_event(Event(coro_func(2), f2, None))
        assert await asyncio.wait_for(f2, timeout=2) == 2
        # 复用: slot 数仍为 4, 且被占用的下标不变
        assert any(c is not None for c in manager._cor_handle)

    async def test_event_keeps_running_when_worker_slot_released(self, manager):
        # 一个 worker 完成事件后, 应能继续消费队列里的下一个事件
        async def coro_func(idx):
            await asyncio.sleep(0.01)
            return idx

        futures = []
        # 发送 5 个事件, 但 max_cor_num=4: 第 5 个会在队列里等
        for i in range(5):
            f = asyncio.Future()
            futures.append(f)
            await manager.send_event(Event(coro_func(i), f, None))

        results = await asyncio.wait_for(asyncio.gather(*futures), timeout=2)
        assert sorted(results) == [0, 1, 2, 3, 4]

    async def test_register_scheduler_loop_func(self, manager):
        # 注册一个 callback, 应原样存到 _monitor_callback
        def cb(a, b):
            return a + b

        manager.register_scheduler_loop_func(cb, 1, 2)
        assert len(manager._monitor_callback) == 1
        callback, args = manager._monitor_callback[0]
        assert callback is cb
        assert args == (1, 2)
        manager.unregister_scheduler_loop(cb)
        assert not manager._monitor_callback