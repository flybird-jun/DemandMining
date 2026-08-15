
import asyncio
from pathlib import Path
import json
from analyzer.ai_client import AiClient
from util.util import config
from collector.extract.hacker_news_collector import HackerNewsCollector
async def main() -> None:
    client = AiClient(config["ai_api_url"], config["ai_api_key"])

    dir = Path(__file__).resolve().parents[0]
    # article_file =  dir / "article.json"

    # story = json.loads(article_file.read_text(encoding = "utf-8"))

    # text = HackerNewsCollector.get_text(story)
    # response_text = await client.summary_text(text)
    # print(response_text)
    # comments = HackerNewsCollector.get_comments(story)

    # (dir / "comments.json").write_text(json.dumps(comments))

    # extract_comments = await client.extract_comments(f"{comments}")
    # print(extract_comments)
    # (dir / "extract_comments.json").write_text(extract_comments, encoding = "utf-8")
    # print(type(extract_comments))
    comment_path = dir / "comments.json"
    comment_str = comment_path.read_text(encoding = "utf-8")
    comments = json.loads(comment_str)

    response = await client.aggregation_analyzer(comments)

    out_path = dir / "out.md"

    out_path.write_text(response)
if __name__ == "__main__":
    asyncio.run(main())
