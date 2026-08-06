"""Hacker News API collector.

封装 Hacker News Firebase API 的轻量级客户端，提供对 items、users 和 live data
（top/new/best/ask/show/job stories、updates、max item）的访问。

官方文档: https://github.com/HackerNews/API

Examples
--------
>>> with HackerNewsCollector() as hn:
...     top_ids = hn.get_top_stories()
...     if top_ids:
...         first = hn.get_item(top_ids[0])
...         print(first["title"])
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

import requests


# 公共常量，便于外部引用 endpoint 分类
STORY_TYPES = {"story", "job", "poll"}
COMMENT_TYPES = {"comment", "pollopt"}


class HackerNewsAPIError(Exception):
    """当 Hacker News API 请求失败或返回非预期结果时抛出。"""


class HackerNewsCollector:
    """Hacker News API 的封装客户端。

    Parameters
    ----------
    base_url:
        API 根地址。默认指向官方 `https://hacker-news.firebaseio.com/v0`。
    timeout:
        单次 HTTP 请求的超时时间（秒），默认 10 秒。
    session:
        可选，自定义 ``requests.Session``；常用于注入 mock 或复用连接。
    max_retries:
        失败重试次数，仅对网络层错误（连接错误、超时、5xx）生效，默认 2。
    backoff_factor:
        两次重试之间的指数退避基数（秒），默认 0.3。
    """

    BASE_URL = "https://hacker-news.firebaseio.com/v0"

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 10.0,
        session: requests.Session | None = None,
        max_retries: int = 2,
        backoff_factor: float = 0.3,
    ) -> None:
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self.timeout = timeout
        self._session = session or requests.Session()
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor

    # ------------------------------------------------------------------
    # 底层请求
    # ------------------------------------------------------------------
    def _request_json(self, endpoint: str) -> Any:
        """向 ``endpoint``（不含 ``.json`` 后缀）发起 GET 并解析 JSON。

        根据 Hacker News API 规范，未找到的 item/user 会返回 ``null``；
        此处保留原样返回，便于调用方自行判定 ``None``。
        """
        url = f"{self.base_url}/{endpoint}.json"
        attempt = 0
        last_exc: Exception | None = None
        while attempt <= self._max_retries:
            try:
                response = self._session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response.json()
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_exc = exc
            except requests.HTTPError as exc:
                # 5xx 视作可重试，4xx 直接抛出
                status = exc.response.status_code if exc.response is not None else 0
                if 500 <= status < 600 and attempt < self._max_retries:
                    last_exc = exc
                else:
                    raise HackerNewsAPIError(
                        f"Hacker News API 请求失败: {exc}"
                    ) from exc
            attempt += 1
            if attempt <= self._max_retries:
                self._sleep_backoff(attempt)

        raise HackerNewsAPIError(
            f"Hacker News API 重试 {self._max_retries} 次后仍失败: {last_exc}"
        ) from last_exc

    def _sleep_backoff(self, attempt: int) -> None:
        import time

        time.sleep(self._backoff_factor * (2 ** (attempt - 1)))

    # ------------------------------------------------------------------
    # Items
    # ------------------------------------------------------------------
    def get_item(self, item_id: int) -> dict[str, Any] | None:
        """获取单个 item（story/comment/job/poll/pollopt）。

        Parameters
        ----------
        item_id:
            Hacker News 的 item 唯一 ID。

        Returns
        -------
        dict 或 None
            item 的原始 JSON 数据；当 ID 不存在或 item 已被删除时返回 ``None``。
        """
        return self._request_json(f"item/{int(item_id)}")

    def get_items(
        self, item_ids: Iterable[int]
    ) -> list[dict[str, Any] | None]:
        """批量获取多个 item，返回顺序与 ``item_ids`` 一致。

        失败的 item 同样以 ``None`` 表示，不影响其他 item 的获取。
        """
        return [self.get_item(item_id) for item_id in item_ids]

    # ------------------------------------------------------------------
    # Live data
    # ------------------------------------------------------------------
    def get_max_item(self) -> int:
        """获取当前最大的 item ID，可用于反向遍历新增 item。"""
        max_id = self._request_json("maxitem")
        if not isinstance(max_id, int):
            raise HackerNewsAPIError(
                f"maxitem 接口返回非整数: {max_id!r}"
            )
        return max_id

    def _get_story_ids(self, endpoint: str) -> list[int]:
        """获取某个 story 列表的 ID 数组，endpoint 取值见下方的公开方法。"""
        result = self._request_json(endpoint)
        if not isinstance(result, list):
            raise HackerNewsAPIError(
                f"{endpoint} 接口返回非列表: {result!r}"
            )
        return result

    def get_top_stories(self) -> list[int]:
        """Top stories（最多 500 个 ID，含 job）。"""
        return self._get_story_ids("topstories")

    def get_new_stories(self) -> list[int]:
        """New stories（最多 500 个 ID）。"""
        return self._get_story_ids("newstories")

    def get_best_stories(self) -> list[int]:
        """Best stories ID 列表。"""
        return self._get_story_ids("beststories")

    def get_ask_stories(self) -> list[int]:
        """Ask HN stories ID 列表（最多 200 个）。"""
        return self._get_story_ids("askstories")

    def get_show_stories(self) -> list[int]:
        """Show HN stories ID 列表（最多 200 个）。"""
        return self._get_story_ids("showstories")

    def get_job_stories(self) -> list[int]:
        """Job stories ID 列表（最多 200 个）。"""
        return self._get_story_ids("jobstories")

    def get_updates(self) -> dict[str, list[Any]]:
        """获取最近发生变化的 items 和 profiles。

        Returns
        -------
        dict
            形如 ``{"items": [int, ...], "profiles": [str, ...]}``。
        """
        result = self._request_json("updates")
        if not isinstance(result, dict):
            raise HackerNewsAPIError(
                f"updates 接口返回非字典: {result!r}"
            )
        return {
            "items": list(result.get("items") or []),
            "profiles": list(result.get("profiles") or []),
        }

    # ------------------------------------------------------------------
    # 高阶采集：热门 stories + 嵌套评论
    # ------------------------------------------------------------------
    def collect_top_stories_with_comments(
        self,
        count: int = 10,
        max_depth: int = 2,
        include_deleted: bool = False,
        output_format: str = "full",
    ) -> list[dict[str, Any]]:
        """获取 Top N stories 及其评论树。

        Parameters
        ----------
        count:
            抓取的 story 数量，默认 10。
        max_depth:
            评论递归深度（1 = 仅顶层评论；2 = 顶层 + 一层回复，依此类推）。
            HN 评论树很深，建议 ≤ 3 以避免请求爆炸。
        include_deleted:
            是否保留 ``deleted`` / ``dead`` 的 item，默认过滤掉。
        output_format:
            - ``"full"``：保留所有 HN 原始字段 + ``time_iso`` + 嵌套 ``comments``
            - ``"simple"``：仅 ``{title, text, comment[]}``，适合喂给下游 LLM 分析

        Returns
        -------
        list[dict]
            每个元素是按 ``output_format`` 格式化后的 story。
        """
        if count <= 0:
            return []
        if output_format not in {"full", "simple"}:
            raise ValueError(
                f"output_format 必须是 'full' 或 'simple'，得到 {output_format!r}"
            )

        top_ids = self.get_top_stories()[:count]
        stories = self.get_items(top_ids)
        result: list[dict[str, Any]] = []
        for story in stories:
            if story is None:
                continue
            if not include_deleted and (story.get("deleted") or story.get("dead")):
                continue
            if story.get("type") != "story":
                continue
            enriched = self._enrich_item(story)
            kid_ids = story.get("kids") or []
            enriched["comments"] = self._collect_comments(
                kid_ids, current_depth=1, max_depth=max_depth,
                include_deleted=include_deleted,
            )
            if output_format == "simple":
                result.append(self._project_simple(enriched))
            else:
                result.append(enriched)
        return result

    def _collect_comments(
        self,
        comment_ids: list[int],
        current_depth: int,
        max_depth: int,
        include_deleted: bool,
    ) -> list[dict[str, Any]]:
        """递归收集评论。``current_depth`` 从 1 开始（顶层评论）。"""
        if not comment_ids or current_depth > max_depth:
            return []
        items = self.get_items(comment_ids)
        comments: list[dict[str, Any]] = []
        for item in items:
            if item is None:
                continue
            if not include_deleted and (item.get("deleted") or item.get("dead")):
                continue
            enriched = self._enrich_item(item)
            if current_depth < max_depth:
                kid_ids = item.get("kids") or []
                enriched["comments"] = self._collect_comments(
                    kid_ids,
                    current_depth=current_depth + 1,
                    max_depth=max_depth,
                    include_deleted=include_deleted,
                )
            comments.append(enriched)
        return comments

    @staticmethod
    def _project_simple(item: dict[str, Any]) -> dict[str, Any]:
        """把 full 格式的 item 投影成 ``{title, text, comment[]}`` 精简结构。

        ``comment`` 字段递归嵌套（reply 链），便于下游按层级理解语境。
        本函数对**顶层 story** 和**评论**都生效，但 story 才有 ``title``；
        评论节点只输出 ``{text, comment[]}``，避免冗余空字段。
        """
        kids = item.get("comments") or []
        is_story = item.get("type") == "story"
        projected_comments = [
            {
                "text": (c.get("text") or "").strip(),
                "comment": [
                    HackerNewsCollector._project_simple(r)
                    for r in (c.get("comments") or [])
                ],
            }
            for c in kids
        ]
        if is_story:
            return {
                "title": item.get("title") or "",
                "text": item.get("text") or "",
                "comment": projected_comments,
            }
        # 评论节点：只有 text + comment
        return {
            "text": (item.get("text") or "").strip(),
            "comment": projected_comments,
        }

    @staticmethod
    def _enrich_item(item: dict[str, Any]) -> dict[str, Any]:
        """为 item 增加 ``time_iso`` 可读时间戳，其余字段保持原样。"""
        enriched = dict(item)
        ts = item.get("time")
        if isinstance(ts, int):
            enriched["time_iso"] = datetime.fromtimestamp(
                ts, tz=timezone.utc
            ).isoformat().replace("+00:00", "Z")
        return enriched

    # ------------------------------------------------------------------
    # 会话生命周期
    # ------------------------------------------------------------------
    def close(self) -> None:
        """关闭底层 ``requests.Session``。"""
        self._session.close()

    def __enter__(self) -> "HackerNewsCollector":
        return self

    def __exit__(self, exc_type, exc_val, traceback) -> None:
        """释放底层 Session。

        ``__exit__`` 协议要求 ``exc_type``/``exc_val``/``traceback`` 三个入参。
        当前实现不消费异常信息（返回 ``None`` 让异常照常向上传播），
        但保留入参便于将来扩展（如未捕获异常上报/统计）。
        """
        # 显式引用一次以满足静态分析器对"已使用参数"的检查
        _ctx_exit_info = (exc_type, exc_val, traceback)
        del _ctx_exit_info
        self.close()