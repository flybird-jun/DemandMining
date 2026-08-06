"""Hacker News 官方 API(v0) 封装。

文档: https://github.com/HackerNews/API
所有端点都在 https://hacker-news.firebaseio.com/v0/ 下, 目前无频率限制。
"""

from collector.collector import SocialMediaApi


class HackerNewsApi(SocialMediaApi):
    BASE_URL = "https://hacker-news.firebaseio.com/v0"

    def __init__(self) -> None:
        super().__init__()

    # 统一拼接 URL 并解析 JSON, endpoint 不带 .json 后缀
    def _get_json(self, endpoint: str):
        url = f"{self.BASE_URL}/{endpoint}.json"
        return self._request(url).json()

    # ---------------- Items ----------------

    # 获取单个 item(story/comment/job/poll/pollopt), id 不存在时 HN 返回 null -> None
    # {"id":8863, "type":"story", "by":"dhouston", "title":"...", "kids":[8952, ...], ...}
    def get_item(self, item_id: int) -> dict | None:
        return self._get_json(f"item/{item_id}")

    # ---------------- Users ----------------

    # 获取用户信息, 只有有公开活动(发帖/评论)的用户才查得到, 不存在时返回 None
    # {"id":"jl", "created":1173923446, "karma":2937, "about":"...", "submitted":[...]}
    def get_user(self, user_id: str) -> dict | None:
        return self._get_json(f"user/{user_id}")

    # ---------------- Live Data ----------------

    # 当前最大的 item id, 可从这里向前遍历所有 item: 9130260
    def get_max_item_id(self) -> int:
        return self._get_json("maxitem")

    # 最多500条最热帖子id(含job):[ 9129911, 9129199, 9127761, 9128141, ..., 9038733 ]
    def get_top_stories(self) -> list:
        return self._get_json("topstories")

    # 最多500条最新帖子id:[ 9129911, 9129199, 9127761, 9128141, ..., 9038733 ]
    def get_new_stories(self) -> list:
        return self._get_json("newstories")

    # 最佳帖子id列表
    def get_best_stories(self) -> list:
        return self._get_json("beststories")

    # 最多200条 Ask HN 帖子id:[ 9127232, 9128437, 9130049, ..., 9120990 ]
    def get_ask_stories(self) -> list:
        return self._get_json("askstories")

    # 最多200条 Show HN 帖子id
    def get_show_stories(self) -> list:
        return self._get_json("showstories")

    # 最多200条 Job 帖子id
    def get_job_stories(self) -> list:
        return self._get_json("jobstories")

    # 最近发生变化的item和用户
    # {"items":[ 8423305, 8420805, ... ], "profiles":[ "thefox", "mdda", ... ]}
    def get_updates(self) -> dict:
        return self._get_json("updates")
