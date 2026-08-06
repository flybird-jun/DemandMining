from __future__ import annotations

import asyncio
import time
from typing import ClassVar
from urllib.parse import urlparse
from urllib.robotparser import RequestRate, RobotFileParser
import aiohttp

class RobotsChecker:
    """robots.txt 解析 + 限速决策, 静态化接口。"""

    # 类级共享缓存
    user_agent: ClassVar[str] = "DemandMiningBot/0.1 (+https://github.com/xujun/DemandMining; x240859954@gmail.com)"
    DEFAULT_DELAY: ClassVar[float] = 1.0
    _cache: ClassVar[dict[str, RobotFileParser]] = {}
    _cache_lock: ClassVar[dict[str, asyncio.Lock]] = {}
    _access_history: ClassVar[dict[str, list]] = {}

    @staticmethod
    async def check(session: aiohttp.ClientSession, url: str) -> bool:
        domain = RobotsChecker._get_domain(url)
        try:
            robot_protype = await RobotsChecker._get_robot_protype(session, domain)
        except Exception:
            return False

        if not robot_protype.can_fetch(RobotsChecker.user_agent, url):
            return False

        crawl_delay = robot_protype.crawl_delay(RobotsChecker.user_agent)

        rate = robot_protype.request_rate(RobotsChecker.user_agent)
        
        async with RobotsChecker._cache_lock[domain]:
            delay = RobotsChecker._calc_delay(RobotsChecker._access_history[domain], crawl_delay, rate)
            await asyncio.sleep(delay)
            RobotsChecker._access_history[domain].append(time.monotonic())
        
        return True
    # tag.uncomplete 实现删除长期不用的domain，减少内存占用, 后期实现
    @staticmethod
    def clear_cache() -> None:
        """清空所有缓存, 便于测试或多账号场景。"""
        RobotsChecker._cache.clear()
        RobotsChecker._cache_lock.clear()
        RobotsChecker._access_history.clear()

    @staticmethod
    def _get_domain(url: str) -> str:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        # 去掉默认端口
        if (parsed.scheme == "http" and netloc.endswith(":80")) or (
            parsed.scheme == "https" and netloc.endswith(":443")
        ):
            netloc = netloc.rsplit(":", 1)[0]
        if parsed.scheme not in {"http", "https"} or not netloc:
            raise ValueError(f"invalid url for robots check: {url!r}")
        return f"{parsed.scheme}://{netloc}"

    @staticmethod
    def _calc_delay(
        history: list,
        interval: float | None,
        rate: RequestRate | None,
    ) -> float:
        now = time.monotonic()
        delay = 0
        last_access_time = 0
        if history:
            last_access_time = history[-1]
        if interval and now - last_access_time < interval:
            delay = interval - (now - last_access_time)
        
        if rate is not None:
            if rate.requests != 0:
                while history and now - history[0] >= rate.seconds:
                    history.pop(0)
                if len(history) >= rate.requests:
                    delay = max(rate.seconds - (now - history[0]), delay)

        return delay
    
    @staticmethod
    async def _get_robot_protype(session:aiohttp.ClientSession, domain:str) -> RobotFileParser:
        if domain not in RobotsChecker._cache:
            lock = RobotsChecker._cache_lock.setdefault(domain, asyncio.Lock())
            async with lock:
                # 加完锁再判断_cache[domain] 是否存在，防止加锁时被另一个协程拿走, 解析一遍robots协议，回到本协程又会再次解析
                if domain not in RobotsChecker._cache:
                    rp = RobotFileParser()
                    try:
                        response = await session.get(f"{domain}/robots.txt")
                    except aiohttp.ClientResponseError as e:
                        # 404 = 网站没 robots.txt, 写入默认
                        # 其他 HTTP 错误 (403/5xx 等) 视为网络异常, 抛给 check 处理
                        if e.status == 404:
                            rp.parse([
                                "User-agent: *",
                                "Allow: /",
                                f"Crawl-delay: {RobotsChecker.DEFAULT_DELAY}",
                                f"Request-rate: 1/{RobotsChecker.DEFAULT_DELAY}",
                            ])
                        else:
                            raise
                    else:
                        rp = RobotFileParser()
                        text = await response.text()
                        rp.parse(text.splitlines())
                    
                    RobotsChecker._access_history[domain] = []
                    RobotsChecker._cache[domain] = rp

        return RobotsChecker._cache[domain]