
import json
from pathlib import Path
from collector.extract.hacker_news_collector import HackerNewsCollector

def main() -> None:
    dir = Path(__file__).resolve().parents[0]
    article_file =  dir / "article.json"
    with article_file.open("r", encoding = "utf-8") as fd:
        input = json.load(fd)
    body = HackerNewsCollector.get_text(input)
    comments = HackerNewsCollector.get_comments(input)
    print(f"body is:\n{body}\n")
    print(f"comments is:\n{comments}\n")
if __name__ == "__main__":
    main()
