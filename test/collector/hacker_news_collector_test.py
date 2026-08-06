"""调用 HackerNewsApi 的每个接口, 把返回值打印出来。

运行方式(在仓库根目录):
    python3 test/collector/hacker_news_collector_test.py
"""

import sys
from pathlib import Path

# 源码根目录是 src/, 需要加入 sys.path 才能 import collector.*
# 本文件位于 <repo>/test/collector/, 向上三级得到 <repo>
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from collector.hacker_news import HackerNewsApi

api = HackerNewsApi()

print("get_max_item_id  :", api.get_max_item_id())
print("get_top_stories  :", api.get_top_stories())
print("get_new_stories  :", api.get_new_stories())
print("get_best_stories :", api.get_best_stories())
print("get_ask_stories  :", api.get_ask_stories())
print("get_show_stories :", api.get_show_stories())
print("get_job_stories  :", api.get_job_stories())
print("get_updates      :", api.get_updates())
print("get_item(8863)   :", api.get_item(8863))       # story
print("get_item(2921983):", api.get_item(2921983))    # comment
print("get_item(126809) :", api.get_item(126809))     # poll
print("get_item(0)      :", api.get_item(0))          # 不存在 -> None
