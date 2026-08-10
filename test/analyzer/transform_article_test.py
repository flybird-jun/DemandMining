
import asyncio
import json
import logging
import sys
import aiofiles
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from analyzer.ai_client import AiClient

# ---- 路径与可调参数 ----------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = _PROJECT_ROOT / "data" / "raw_data" / "2026_08_10"
OUTPUT_DIR = _PROJECT_ROOT / "data" / "raw_data" / "2026_08_10_cn"
CONFIG_PATH = _PROJECT_ROOT / "src" / "config" / "config.json"
_PROMPT_PATH = _PROJECT_ROOT/ "test" / "analyzer" / "trans.prompt"
# 同时向 LLM 端发起的请求数; 调到 1 = 完全串行
CONCURRENCY = 10

# ---- 日志 --------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def transform_raw_data(client:AiClient, file_name:str, prompt:str, sem:asyncio.Semaphore):
    async with sem:
        async with aiofiles.open(INPUT_DIR/file_name, "r", encoding='utf-8') as input:
            contents = await input.read()
            
            output = await client._chat(prompt, contents)
            async with aiofiles.open(OUTPUT_DIR/file_name, "w", encoding='utf-8') as fd:
                await fd.write(output)

async def main() -> None:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    client = AiClient(cfg["ai_api_url"], cfg["ai_api_key"])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    src_files = list(INPUT_DIR.glob("*.json"))
    sem = asyncio.Semaphore(CONCURRENCY)

    prompt = _PROMPT_PATH.read_text(encoding="utf-8")
    await asyncio.gather(*(transform_raw_data(client, p.name, prompt, sem) for p in src_files))

if __name__ == "__main__":
    asyncio.run(main())