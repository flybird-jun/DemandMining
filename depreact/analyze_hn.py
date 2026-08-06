"""Hacker News 创业需求挖掘分析器。

工作流：
1. 读取 ``config.json`` 配置 LLM API。
2. 读取 ``hacker_news_story_cn.json``，对每个 story：
   * 用 ``story_prompt.txt`` 模板 + 格式化后的评论作为输入
   * 调用 LLM，得到结构化需求分析 JSON
   * 写入本次运行子目录下的 ``story_<id>.json``
3. 收集所有 story 的分析结果，用 ``aggregation_prompt.txt``：
   * 调用 LLM 做聚合（趋势、痛点聚类、Top 10 机会）
   * 写入 ``aggregation_result.json``

每次运行都会创建一个独立的时间戳子目录（默认 ``output/run_YYYYMMDD_HHMMSS/``，
可通过 ``--run-id`` 自定义），所有产物（含 ``run.log``）都落在该子目录内，
避免覆盖历史运行结果，便于后续对比分析。

支持 ``--dry-run`` 仅生成 prompt 不调用 LLM，便于调试与成本估算。

Examples
--------
# 真跑（默认全部 10 个 story）
python3 analyze_hn.py

# 只跑前 3 个 story 试水
python3 analyze_hn.py --limit 3

# 仅生成 prompt，验证格式
python3 analyze_hn.py --dry-run --limit 1

# 自定义运行名，便于多次对比（例如基线 vs 实验组）
python3 analyze_hn.py --run-id baseline
python3 analyze_hn.py --run-id exp_v2
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

from llm_client import LLMAPIError, LLMClient


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = PROJECT_ROOT / "hacker_news_story_cn.json"
DEFAULT_CONFIG = PROJECT_ROOT / "config.json"
DEFAULT_STORY_PROMPT = PROJECT_ROOT / "story_prompt.txt"
DEFAULT_AGG_PROMPT = PROJECT_ROOT / "aggregation_prompt.txt"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"

# 评论渲染的截断阈值（字符）
MAX_COMMENT_CHARS = 500
MAX_TOTAL_COMMENT_CHARS = 18_000
MAX_TITLE_CHARS = 300
MAX_TEXT_CHARS = 4_000

logger = logging.getLogger("analyze_hn")


def setup_logging(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    log_file = output_dir / "run.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
        force=True,
    )


def create_run_subdir(base_dir: Path, run_id: str | None = None) -> Path:
    """Create a per-run subdirectory under ``base_dir`` and return its path.

    When ``run_id`` is None, generates ``run_YYYYMMDD_HHMMSS`` from local time.
    When provided, ``run_id`` must match ``[A-Za-z0-9_-]+``; an existing
    directory with the same name raises (preserves historical runs).
    """
    if run_id is None:
        run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    else:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
            raise SystemExit(
                f"--run-id must match [A-Za-z0-9_-]+, got: {run_id!r}"
            )
    run_dir = base_dir / run_id
    if run_dir.exists():
        raise SystemExit(
            f"运行目录已存在: {run_dir}（避免覆盖历史结果，请更换 --run-id 或稍后重试）"
        )
    run_dir.mkdir(parents=True)
    return run_dir


# ----------------------------------------------------------------------
# 1) 输入装载
# ----------------------------------------------------------------------
def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        cfg = json.load(f)
    for key in ("ai_api_url", "ai_api_key"):
        if key not in cfg or not cfg[key]:
            raise SystemExit(f"config.json 缺少字段 {key!r}")
    return cfg


def load_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_stories(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise SystemExit(f"{path} 顶层必须是数组")
    return data


# ----------------------------------------------------------------------
# 2) 评论渲染
# ----------------------------------------------------------------------
def truncate(text: str, limit: int) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def format_comments(
    comments: list[dict[str, Any]],
    path_prefix: str = "",
    budget: int = MAX_TOTAL_COMMENT_CHARS,
) -> tuple[str, int]:
    """把嵌套评论渲染为 LLM 友好的文本。

    格式：``[1] text...``，子评论 ``[1.1] text...``，依此类推。
    返回 ``(文本, 渲染字节数)``，并在接近预算时停止继续展开。
    """
    lines: list[str] = []
    used = 0

    def render(items: list[dict[str, Any]], prefix: str) -> None:
        nonlocal used
        for idx, c in enumerate(items, start=1):
            if used >= budget:
                return
            text = truncate((c.get("text") or "").strip(), MAX_COMMENT_CHARS)
            label = f"[{prefix}{idx}]"
            line = f"{label} {text}".strip()
            lines.append(line)
            used += len(line) + 1
            kids = c.get("comment") or []
            if kids:
                render(kids, f"{prefix}{idx}.")

    render(comments, path_prefix)
    return "\n".join(lines), used


# ----------------------------------------------------------------------
# 3) 单 story 分析
# ----------------------------------------------------------------------
def build_story_user_prompt(template: str, story: dict[str, Any]) -> str:
    """把 ``{title}``/``{text}``/``{comments}`` 替换进 story_prompt 模板。"""
    title = truncate(story.get("title") or "", MAX_TITLE_CHARS)
    text = truncate(story.get("text") or "", MAX_TEXT_CHARS)
    comments_text, _ = format_comments(story.get("comment") or [])
    return (
        template
        .replace("{title}", title)
        .replace("{text}", text)
        .replace("{comments}", comments_text or "(无评论)")
    )


def analyze_one_story(
    client: LLMClient,
    story_prompt_template: str,
    story: dict[str, Any],
    story_index: int,
    total: int,
) -> dict[str, Any]:
    user_prompt = build_story_user_prompt(story_prompt_template, story)
    logger.info(
        "[story %d/%d] 开始: %s",
        story_index, total,
        truncate(story.get("title") or "", 60),
    )
    start = time.perf_counter()
    result = client.chat_json(
        system_prompt="你是产品经理与创业研究员，严格按 JSON 结构输出，不要输出 JSON 以外的文字。",
        user_prompt=user_prompt,
    )
    elapsed = time.perf_counter() - start
    logger.info("[story %d/%d] 完成，耗时 %.1fs", story_index, total, elapsed)
    return {
        "story_title": story.get("title"),
        "story_index": story_index,
        "analysis": result,
    }


def analyze_stories_concurrent(
    client: LLMClient,
    story_prompt_template: str,
    stories: list[dict[str, Any]],
    max_workers: int,
) -> tuple[list[dict[str, Any]], list[tuple[int, str, str]]]:
    """并发分析多个 story。

    Parameters
    ----------
    max_workers:
        同时在跑的 LLM 请求数。过大可能触发 API 速率限制，
        建议 3-5；过小则失去并发意义。

    Returns
    -------
    (results, failures)
        results — 按 ``story_index`` 升序排列的成功结果
        failures — ``(index, title, error_msg)`` 列表
    """
    total = len(stories)
    indexed_results: dict[int, dict[str, Any]] = {}
    failures: list[tuple[int, str, str]] = []

    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as executor:
        future_to_idx = {
            executor.submit(
                analyze_one_story,
                client, story_prompt_template, story, idx, total,
            ): idx
            for idx, story in enumerate(stories, start=1)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                indexed_results[idx] = future.result()
            except LLMAPIError as exc:
                logger.error("[story %d/%d] 失败: %s", idx, total, exc)
                failures.append((idx, stories[idx - 1].get("title", ""), str(exc)))
            except Exception as exc:  # noqa: BLE001
                logger.error("[story %d/%d] 未预期异常: %s", idx, total, exc)
                failures.append((idx, stories[idx - 1].get("title", ""), str(exc)))

    ordered = [indexed_results[i] for i in sorted(indexed_results)]
    return ordered, failures


# ----------------------------------------------------------------------
# 4) 聚合
# ----------------------------------------------------------------------
def build_aggregation_user_prompt(template: str, per_story: list[dict[str, Any]]) -> str:
    # 把每个 story 的分析压成紧凑 JSON 字符串喂给聚合 prompt
    serialized = json.dumps(per_story, ensure_ascii=False, indent=2)
    return template.replace("{story_analysis_results}", serialized)


# ----------------------------------------------------------------------
# 5) 主流程
# ----------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="HN 创业需求挖掘分析器")
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    p.add_argument("--story-prompt", type=Path, default=DEFAULT_STORY_PROMPT)
    p.add_argument("--agg-prompt", type=Path, default=DEFAULT_AGG_PROMPT)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="只处理前 N 个 story；不传则全部处理",
    )
    p.add_argument(
        "--model",
        default=None,
        help="覆盖 config.json 里的 model（若配置中有的话）",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="只生成 prompt，不调用 LLM，输出到 dry_run_story_0.txt",
    )
    p.add_argument(
        "--skip-aggregate",
        action="store_true",
        help="只跑 story 级分析，跳过最后聚合",
    )
    p.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="并行分析的 story 数，建议 3-5，过大可能触发 API 限流",
    )
    p.add_argument(
        "--run-id",
        default=None,
        help=(
            "自定义本次运行的子目录名（默认 run_YYYYMMDD_HHMMSS）。"
            "仅允许字母、数字、下划线、连字符；同名目录已存在会报错以保护历史结果。"
        ),
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = create_run_subdir(args.output_dir, args.run_id)
    setup_logging(run_dir)
    logger.info("本次运行输出目录: %s", run_dir)
    logger.info("配置: %s", {k: v for k, v in vars(args).items() if k != "input"})

    cfg = load_config(args.config)
    stories = load_stories(args.input)
    if args.limit is not None:
        stories = stories[: args.limit]
    logger.info("共加载 %d 个 story", len(stories))

    story_prompt_template = load_prompt(args.story_prompt)
    if args.dry_run:
        for idx, s in enumerate(stories):
            user_prompt = build_story_user_prompt(story_prompt_template, s)
            out = run_dir / f"dry_run_story_{idx}.txt"
            out.write_text(user_prompt, encoding="utf-8")
            logger.info("[dry-run] story %d → %s (%d chars)", idx, out, len(user_prompt))
        logger.info("dry-run 完成，未调用 LLM")
        return 0

    model = args.model or cfg.get("model") or "MiniMax-Text-01"
    client = LLMClient(
        api_url=cfg["ai_api_url"],
        api_key=cfg["ai_api_key"],
        model=model,
    )

    per_story_results: list[dict[str, Any]] = []
    failed: list[tuple[int, str, str]] = []  # (idx, title, error)
    total_start = time.perf_counter()
    with client:
        logger.info(
            "并发分析 %d 个 story，并发度 %d", len(stories), args.concurrency,
        )
        per_story_results, failed = analyze_stories_concurrent(
            client=client,
            story_prompt_template=story_prompt_template,
            stories=stories,
            max_workers=args.concurrency,
        )
        # 单个 story 结果落盘，便于断点续跑/人工抽查
        for result in per_story_results:
            idx = result["story_index"]
            (run_dir / f"story_{idx}.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        # 写汇总
        (run_dir / "all_stories_analysis.json").write_text(
            json.dumps(per_story_results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if args.skip_aggregate:
            logger.info("已跳过聚合（--skip-aggregate）")
            return 0

        if not per_story_results:
            logger.error("没有成功的 story 分析，无法聚合")
            return 1

        logger.info("开始聚合分析，共 %d 个 story 结果", len(per_story_results))
        agg_template = load_prompt(args.agg_prompt)
        agg_user = build_aggregation_user_prompt(agg_template, per_story_results)
        start = time.perf_counter()
        try:
            aggregation = client.chat_json(
                system_prompt=(
                    "你是创业趋势分析师，严格按 JSON 结构输出，不要输出 JSON 以外的文字。"
                ),
                user_prompt=agg_user,
                temperature=0.4,
            )
        except LLMAPIError as exc:
            logger.error("聚合分析失败: %s", exc)
            return 2
        elapsed = time.perf_counter() - start
        logger.info("聚合完成，耗时 %.1fs", elapsed)
        (run_dir / "aggregation_result.json").write_text(
            json.dumps(aggregation, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    total_elapsed = time.perf_counter() - total_start
    logger.info(
        "全部完成：%d 成功，%d 失败，总耗时 %.1fs",
        len(per_story_results), len(failed), total_elapsed,
    )
    if failed:
        logger.warning("失败明细: %s", failed)
    return 0


if __name__ == "__main__":
    sys.exit(main())