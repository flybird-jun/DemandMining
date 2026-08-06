import requests
import time
from typing import Any, Iterable
from abc import ABC, abstractmethod

class SocialMediaApi:
    MAX_RETRIES = 3
    SLEEP_FACTOR = 0.3
    TIMEOUT = 10.0
    def __init__(self) -> None:
        self._session = requests.Session()

    def _request(self, url:str) -> Any:
        attempt = 0
        while attempt < self.MAX_RETRIES:
            try:
                response = self._session.get(url, timeout = self.TIMEOUT)
                response.raise_for_status()
                return response
            except requests.HTTPError as e:
                if e.response is None or e.response.status_code < 500 or e.response.status_code >= 600:
                    raise e
            time.sleep(self.SLEEP_FACTOR * (2 ** attempt))
            attempt += 1
        raise Exception("request {str} error")

"""
迭代模型, 每次返回如下格式字典
{
    "title": "", # 标题
    "text": "", # 正文
    "comment": [ # 多条同样的格式的评论
        {
            "text": "" # 评论
            "comment": [] # comment节点, 本评论的回复, 可能为空, 即没有回复, 也可能有多条回复、回复评论的回复
        },
        {
            ...
        }
    ]
}
"""
class Collector(ABC):
    @abstractmethod
    def __iter__(self):
        pass
    @abstractmethod
    def __next__(self):
        pass

