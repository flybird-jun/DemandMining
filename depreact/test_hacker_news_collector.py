"""HackerNewsCollector 集成测试：实际访问 Hacker News API 验证连通性。

运行方式: ``python3 test_hacker_news_collector.py``
"""

from __future__ import annotations

import sys
import time
from typing import Any, Callable

from hacker_news_collector import HackerNewsAPIError, HackerNewsCollector


GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"


def _run_case(
    name: str,
    cases: list[tuple[str, Callable[[HackerNewsCollector], Any]]],
) -> bool:
    """执行一组用例，全部通过返回 True。"""
    print(f"\n{YELLOW}=== {name} ==={RESET}")
    all_passed = True
    with HackerNewsCollector() as hn:
        for case_name, fn in cases:
            start = time.perf_counter()
            try:
                result = fn(hn)
            except Exception as exc:  # noqa: BLE001
                elapsed = (time.perf_counter() - start) * 1000
                print(f"  {RED}✗{RESET} {case_name}  ({elapsed:.0f} ms)  {exc!r}")
                all_passed = False
                continue
            elapsed = (time.perf_counter() - start) * 1000
            preview = repr(result)
            if len(preview) > 100:
                preview = preview[:97] + "..."
            print(f"  {GREEN}✓{RESET} {case_name}  ({elapsed:.0f} ms)  {preview}")
    return all_passed


def case_max_item(hn: HackerNewsCollector) -> int:
    max_id = hn.get_max_item()
    assert isinstance(max_id, int) and max_id > 0, f"max_id 无效: {max_id}"
    return max_id


def case_top_stories(hn: HackerNewsCollector) -> list[int]:
    ids = hn.get_top_stories()
    assert isinstance(ids, list) and len(ids) > 0, "top stories 为空"
    assert all(isinstance(i, int) for i in ids), "top stories 包含非 int"
    return ids[:5]  # 只返回前 5 个做断言展示


def case_new_stories(hn: HackerNewsCollector) -> int:
    return len(hn.get_new_stories())


def case_best_stories(hn: HackerNewsCollector) -> int:
    return len(hn.get_best_stories())


def case_ask_show_job_stories(hn: HackerNewsCollector) -> dict[str, int]:
    return {
        "ask": len(hn.get_ask_stories()),
        "show": len(hn.get_show_stories()),
        "job": len(hn.get_job_stories()),
    }


def case_get_item_real(hn: HackerNewsCollector) -> dict[str, Any]:
    item = hn.get_item(8863)  # API 文档里的示例 story
    assert item is not None, "id=8863 应存在"
    assert item["id"] == 8863
    assert item["type"] == "story"
    assert "title" in item
    return item


def case_get_item_not_found(hn: HackerNewsCollector) -> None:
    # 一个明显不存在的 ID，HN API 应返回 None
    result = hn.get_item(0)
    assert result is None, f"期望 None，得到 {result!r}"


def case_get_items_batch(hn: HackerNewsCollector) -> list[dict[str, Any] | None]:
    top = hn.get_top_stories()[:3]
    items = hn.get_items(top)
    assert len(items) == 3
    assert all(i is not None for i in items)
    return items


def case_get_user(hn: HackerNewsCollector) -> dict[str, Any]:
    user = hn.get_user("jl")  # API 文档示例用户
    assert user is not None, "用户 jl 应存在"
    assert user["id"] == "jl"
    assert "karma" in user and user["karma"] > 0
    return {"id": user["id"], "karma": user["karma"], "submitted_count": len(user.get("submitted", []))}


def case_get_user_not_found(hn: HackerNewsCollector) -> None:
    user = hn.get_user("__definitely_not_a_real_user__")
    assert user is None, f"期望 None，得到 {user!r}"


def case_updates(hn: HackerNewsCollector) -> dict[str, int]:
    upd = hn.get_updates()
    assert isinstance(upd, dict)
    assert "items" in upd and "profiles" in upd
    return {"items": len(upd["items"]), "profiles": len(upd["profiles"])}


def case_error_path() -> bool:
    """自定义 base_url 指向不存在的主机，验证异常路径。"""
    print(f"\n{YELLOW}=== error path ==={RESET}")
    try:
        with HackerNewsCollector(
            base_url="http://127.0.0.1:1",  # 永远连不通
            timeout=1.0,
            max_retries=1,
        ) as hn:
            hn.get_max_item()
    except HackerNewsAPIError as exc:
        print(f"  {GREEN}✓{RESET} 异常被正确抛出: {exc}")
        return True
    print(f"  {RED}✗{RESET} 未抛出 HackerNewsAPIError")
    return False


def main() -> int:
    suite: list[tuple[str, list[tuple[str, Callable[[HackerNewsCollector], Any]]]]] = [
        (
            "live data",
            [
                ("get_max_item", case_max_item),
                ("get_top_stories", case_top_stories),
                ("get_new_stories", case_new_stories),
                ("get_best_stories", case_best_stories),
                ("get_ask/show/job_stories", case_ask_show_job_stories),
                ("get_updates", case_updates),
            ],
        ),
        (
            "items",
            [
                ("get_item(8863)", case_get_item_real),
                ("get_item(0) -> None", case_get_item_not_found),
                ("get_items batch", case_get_items_batch),
            ],
        ),
        (
            "users",
            [
                ("get_user(jl)", case_get_user),
                ("get_user(unknown) -> None", case_get_user_not_found),
            ],
        ),
    ]

    results = [_run_case(name, cases) for name, cases in suite]
    results.append(case_error_path())

    total = len(results)
    passed = sum(results)
    print(f"\n{'=' * 40}")
    if passed == total:
        print(f"{GREEN}全部通过: {passed}/{total}{RESET}")
        return 0
    print(f"{RED}失败: {total - passed}/{total}{RESET}")
    return 1


if __name__ == "__main__":
    sys.exit(main())