"""冒烟测试: 调用 RobotsChecker 的 public 接口并打印结果。

需要外网, 失败也不会崩。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import aiohttp

from collector.net.robot_checker import RobotsChecker


async def main() -> None:
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for url in [
            "https://news.ycombinator.com/",
            "https://example.com/",
            "https://httpbin.org/deny",
        ]:
            print(f"=== RobotsChecker.check({url}) ===")
            try:
                allowed = await RobotsChecker.check(session, url)
                print("allowed:", allowed)
            except Exception as e:
                print("check failed:", repr(e))
            print("cache keys:", list(RobotsChecker._cache.keys()))


if __name__ == "__main__":
    asyncio.run(main())
