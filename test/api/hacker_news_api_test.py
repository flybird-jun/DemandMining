"""冒烟测试: 调用 HackerNewsApi 的 public 接口并打印结果。

需要外网, 失败也不会崩。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import aiohttp

from collector.api.hacker_news_api import HackerNewsApi


async def main() -> None:
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            print("=== get_max_item_id ===")
            print(await HackerNewsApi.get_max_item_id(session))
        except Exception as e:
            print("get_max_item_id failed:", repr(e))

        try:
            print("=== get_top_stories (前 10 个) ===")
            ids = await HackerNewsApi.get_top_stories(session)
            print("count:", len(ids), "first 10:", ids[:10])
        except Exception as e:
            print("get_top_stories failed:", repr(e))

        try:
            print("=== get_new_stories (前 10 个) ===")
            ids = await HackerNewsApi.get_new_stories(session)
            print("count:", len(ids), "first 10:", ids[:10])
        except Exception as e:
            print("get_new_stories failed:", repr(e))

        try:
            print("=== get_item(8863) ===")
            item = await HackerNewsApi.get_item(session, 8863)
            print(item)
        except Exception as e:
            print("get_item failed:", repr(e))

if __name__ == "__main__":
    asyncio.run(main())
