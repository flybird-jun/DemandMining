"""冒烟测试: 调用 HackerNewsCollector 的 public 接口并打印结果。

需要外网, 失败也不会崩。
"""
import asyncio
import sys
from pathlib import Path
import faulthandler, signal

faulthandler.register(signal.SIGUSR1)
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from collector.extract.hacker_news_collector import HackerNewsCollector


async def main() -> None:
    collector = HackerNewsCollector(item_id_qsize=10)
    collector._queue = asyncio.Queue(maxsize=1000)
    await collector.init()

    out_queue: asyncio.Queue = asyncio.Queue()
    n_consumers = 50
    consumers = [
        asyncio.create_task(collector.producer_item(out_queue))
        for _ in range(n_consumers)
    ]

    try:
        print(f"=== producer_item_ids (消费者 {n_consumers} 个) ===")
        producer = asyncio.create_task(collector.producer_item_ids())
        # 等 producer 跑完
        await producer
        print("queue size after producer:", collector._queue.qsize())

        print("=== consume, 限制最多 5 个 story ===")
        seen = 0
        while seen < 5:
            item = await out_queue.get()
            if item.get("comment"):
                item["comment"] = item["comment"][:2]
            print({k: (v[:60] + "...") if isinstance(v, str) and len(v) > 60 else v for k, v in item.items()})
            seen += 1

        # 取消所有 consumer
        for c in consumers:
            await c
    finally:
        await collector.destroy()


if __name__ == "__main__":
    asyncio.run(main())
