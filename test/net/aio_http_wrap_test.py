"""冒烟测试: 调用 aio_http_wrap 的 public 接口并打印结果。

直接发到 example.com (需要外网), 失败也不会崩。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import aiohttp

from collector.net import aio_http_wrap


async def main() -> None:
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        print("=== aio_http_wrap.request ===")
        try:
            resp = await aio_http_wrap.request(session, "https://example.com/")
            print("status:", resp.status)
            text = await resp.text(errors="replace")
            print("body[:120]:", text[:120].replace("\n", " "))
            resp.release()
        except Exception as e:
            print("request failed:", repr(e))

        print()
        print("=== aio_http_wrap.get_text ===")
        text = await aio_http_wrap.get_text(session, "https://example.com/")
        print("text[:120]:", text[:120].replace("\n", " "))

        print()
        print("=== aio_http_wrap.get_json ===")
        try:
            payload = await aio_http_wrap.get_json(
                session, "https://hacker-news.firebaseio.com/v0/maxitem.json"
            )
            print("maxitem:", payload)
        except Exception as e:
            print("get_json failed:", repr(e))


if __name__ == "__main__":
    asyncio.run(main())
