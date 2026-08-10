"""analyzer 阶段冒烟测试: 把 data/raw_data/2026_08_10_cn/ 下的 raw article
批量喂给 AiClient.article_parse, 结果写到 data/raw_data/2026_08_10_ai/。

输入:  data/raw_data/2026_08_10_cn/<timestamp>.json
       每条是 {"item_id","title","url","text","comment"}, 取 title+text 组装
输出:  data/raw_data/2026_08_10_ai/<同名>.json
       写 article_parse 返回的字符串

并发:  asyncio.Semaphore 控制, 默认 10 路并发

使用:
    python3 test/analyzer/article_analyzer_test.py

注: api_url / api_key 从 src/config/config.json 读 (跟 pipeline.py 一致)。
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from analyzer.ai_client import AiClient

# ---- 路径与可调参数 ----------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = _PROJECT_ROOT / "data" / "raw_data" / "2026_08_10_cn"
OUTPUT_DIR = _PROJECT_ROOT / "data" / "raw_data" / "2026_08_10_ai"
CONFIG_PATH = _PROJECT_ROOT / "src" / "config" / "config.json"

# 同时向 LLM 端发起的请求数; 调到 1 = 完全串行
CONCURRENCY = 20

# ---- 日志 --------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ---- 核心逻辑 ----------------------------------------------------------------

def build_article(record: dict) -> str:
    """把 raw 记录拼成 LLM 输入: 标题 + 正文。"""
    title = (record.get("title") or "").strip()
    text = (record.get("text") or "").strip()
    return f"{title}\n\n{text}" if title else text


async def analyze_one(
    client: AiClient, src_path: Path, sem: asyncio.Semaphore
) -> None:
    """读一个 raw 文件 -> 调一次 article_parse -> 结果写到同名 ai 文件。"""
    async with sem:
        out_path = OUTPUT_DIR / src_path.name
        try:
            record = json.loads(src_path.read_text(encoding="utf-8"))
            article = build_article(record)
            if not article:
                logger.warning("empty article, skip: %s", src_path.name)
                out_path.write_text("", encoding="utf-8")
                return
            analysis = await client.article_parse(article)
            out_path.write_text(analysis, encoding="utf-8")
            logger.info("wrote: %s", out_path.name)
        except Exception as exc:
            logger.exception("analyze failed: %s", src_path.name)
            out_path.write_text(
                json.dumps(
                    {"error": f"{type(exc).__name__}: {exc}"},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )


async def main() -> None:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    client = AiClient(cfg["ai_api_url"], cfg["ai_api_key"])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    src_files = sorted(INPUT_DIR.glob("*.json"))
    logger.info("found %d raw articles in %s", len(src_files), INPUT_DIR)

    sem = asyncio.Semaphore(CONCURRENCY)
    await asyncio.gather(
        *(analyze_one(client, p, sem) for p in src_files)
    )
    logger.info("done: output=%s", OUTPUT_DIR)


if __name__ == "__main__":
    asyncio.run(main())
