
import asyncio
import json
from collector.extract.hacker_news_collector import HackerNewsCollector
from storage.storage import storage
from util import util

async def run():
    # 初始化日志
    
    with open("src/config/config.json", "r", encoding="utf-8") as fd:
        config = json.load(fd)

    util.log_init(config["log_path"])

    collector = HackerNewsCollector()
    await collector.init()

    ids_producer = asyncio.create_task(collector.producer_item_ids())

    item_queue = asyncio.Queue(10)

    item_producers_count = 20
    item_producers = [asyncio.create_task(collector.producer_item(item_queue)) for i in range(item_producers_count)]

    storage_ = storage(config["raw_data_path"])

    storage_customer_count = 4
    item_customers = [asyncio.create_task(storage_.save_article(item_queue)) for i in range(storage_customer_count)]

    await asyncio.gather(ids_producer, *item_producers)
    # item生产完毕, 设置终结
    await item_queue.put(None)
    await asyncio.gather(*item_customers)

    await collector.destroy()

if __name__ == "__main__":
    asyncio.run(run())