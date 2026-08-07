"""冒烟测试: 调用 Crawl.get_text 并打印结果。

需要外网, 失败也不会崩。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import aiohttp

from collector.net.crawl import Crawl
from collector.net.robot_checker import RobotsChecker


async def main() -> None:
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for url in [
            "https://example.com/",
            "https://news.ycombinator.com/item?id=1",
        ]:
            print(f"=== Crawl.get_text({url}) ===")
            try:
                text = await Crawl.get_text(session, url)
                print("len:", len(text), "preview:", text[:80].replace("\n", " "))
            except Exception as e:
                print("get_text failed:", repr(e))

    RobotsChecker.clear_cache()


if __name__ == "__main__":
    asyncio.run(main())
