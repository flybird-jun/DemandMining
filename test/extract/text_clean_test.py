from collector.extract.hacker_news_collector import HackerNewsCollector
#import trafilatura
import asyncio
import signal
import json
from pathlib import Path
def dump_tasks(sig, frame):
    print("\n========== asyncio tasks ==========")
    for task in asyncio.all_tasks():
        print("\nTASK:", task)
        task.print_stack()

async def main() -> None:
    collector = HackerNewsCollector(2)
    await collector.init()

    await collector._queue.put(49241679)
    await collector._queue.put(HackerNewsCollector.INVALID_ITEM_ID)
    item_queue = asyncio.Queue(1)
    await collector.producer_item(item_queue)
    item_json = await item_queue.get()
    path = Path(__file__).resolve().parent / "article.json"
    path.write_text(json.dumps(item_json, ensure_ascii=False, indent = 4), encoding = "utf-8")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    print(data)
    await collector.destroy()

if __name__ == "__main__":
    signal.signal(signal.SIGUSR1, dump_tasks)
    asyncio.run(main())
