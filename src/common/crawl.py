from __future__ import annotations
import logging
import aiohttp

from common import aio_http_wrap
from common.robot_checker import RobotsChecker

logger = logging.getLogger(__name__)

class Crawl:
    @staticmethod
    async def _request(session: aiohttp.ClientSession, url: str) -> aiohttp.ClientResponse | None:
        allowed = await RobotsChecker.check(session,url)
        if not allowed:
            return None
        try:
            return await aio_http_wrap.request(session, url)
        except Exception as e:
            logger.info(f"crawl request {url} failed, error = {type(e).__name__}:'{e}'")
            return None
    @staticmethod
    async def get_text(session: aiohttp.ClientSession, url: str) -> str:
        response = await Crawl._request(session, url)
        if response is None:
            return ""
        try:
            return await response.text(errors="replace")
        finally:
            response.release()