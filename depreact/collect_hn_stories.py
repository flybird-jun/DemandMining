"""抓取 Top 10 Hacker News stories 及其评论树，输出到 hacker_news_story.json。

运行方式: ``python3 collect_hn_stories.py [count] [depth] [output]``

默认参数: 抓取 10 个 story，评论深度 2（顶层评论 + 一层回复），写入
``hacker_news_story.json``。
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from hacker_news_collector import HackerNewsCollector


def main() -> int:
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    depth = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    output = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("hacker_news_story.json")

    print(f"抓取 Top {count} stories，评论深度 {max(depth, 1)} → {output}")
    start = time.perf_counter()

    with HackerNewsCollector() as hn:
        stories = hn.collect_top_stories_with_comments(
            count=count,
            max_depth=max(depth, 1),
            output_format="simple",
        )

    # 简要统计
    def count_comments(nodes: list[dict]) -> int:
        total = 0
        for node in nodes:
            total += 1
            total += count_comments(node.get("comments") or [])
        return total

    total_comments = count_comments([s for s in stories])
    elapsed = time.perf_counter() - start

    output.write_text(
        json.dumps(stories, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    size_kb = output.stat().st_size / 1024
    print(f"✓ 完成：{len(stories)} 个 story，{total_comments} 条评论，"
          f"文件大小 {size_kb:.1f} KB，耗时 {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())