
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0] / "src"))

from analyzer.ai_client import AiClient
from util.util import config
async def main() -> None:
    client = AiClient(config["ai_api_url"], config["ai_api_key"])

    dir = Path(__file__).resolve().parents[0]
    article_file =  dir / "article.json"

    article = article_file.read_text(encoding="utf-8")
    response_text = await client.article_parse(article)

    llm_file = dir / "parse.json"
    llm_file.write_text(response_text, encoding="utf-8")
if __name__ == "__main__":
    asyncio.run(main())
