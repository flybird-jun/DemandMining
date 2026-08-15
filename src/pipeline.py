
import asyncio
from collector.extract.hacker_news_collector import HackerNewsCollector
from storage.storage import storage
from analyzer.ai_client import AiClient
from util.util import logger, config
import json
import traceback
import signal

loop = None

def dump_signal(signum, frame):
    loop.call_soon_threadsafe(dump_tasks)

def dump_tasks():

    print("==========")

    for task in asyncio.all_tasks(loop):
        print(task)


async def producer_item_ids(collector:HackerNewsCollector):
    item_ids = [49184900, 49241679, 49211821, 49209132, 49183917, 49238050, 49238818, 49202912, 49205082, 49237407, 49206028, 49174017, 49182148, 49238735,
                49241303, 49235697, 49238851, 49205793, 49230891, 49203626, 49231809, 49192633, 49237873, 49240406, 49240828, 49239226, 49235641, 49233448,
                49240718, 49234137, 49235011, 49238561, 49199437, 49235378, 49230022, 49239179, 49230514, 49231586, 49178476, 49238831, 49234271, 49232300,
                49235349, 49227505, 49183291, 49239751, 49180059, 49227718, 49229174, 49232110, 49231777, 49235347, 49229848, 49231397, 49238509, 49235471,
                49232253, 49234279, 49232410, 49233306, 49226742, 49228426, 49229621, 49226563, 49238014, 49239021, 49228663, 49235486, 49188559, 49237844,
                49232318, 49234953, 49234579, 49230477, 49222824, 49230630, 49226923, 49228458, 49226636, 49236541, 49221679, 49232548, 49232221, 49220126,
                49238738, 49228166, 49234506, 49187681, 49230424, 49231154, 49221668, 49236563, 49234675, 49224020, 49236240, 49189457, 49177224, 49223082,
                49221220, 49189618, 49208393, 49225139, 49227365, 49180649, 49238028, 49193666, 49226253, 49237123, 49215786, 49179352, 49232138, 49221711,
                49229412, 49230066, 49223105, 49198464, 49231174, 49214098, 49219508, 49236033, 49232459, 49234393, 49216946, 49213029, 49238670, 49230605,
                49195231, 49203105, 49224294, 49240337, 49233637, 49231484, 49236439, 49234724, 49220609, 49233390, 49232177, 49225676, 49208458, 49214008,
                49222189, 49232857, 49235367, 49238827, 49204352, 49236710, 49214775, 49233493, 49221864, 49211660, 49220313, 49214770, 49227392, 49223079,
                49231860, 49234229, 49235818, 49227652, 49231493, 49209385, 49227657, 49221939, 49226536, 49202690, 49213754, 49237362, 49217993, 49220339,
                49216362, 49232012, 49211921, 49224241, 49209572, 49184355, 49212883, 49233423, 49196174, 49228137, 49238158, 49239057, 49200933, 49232312,
                49202716, 49192566, 49225026, 49238026, 49207236, 49208535, 49233394, 49202852, 49235612, 49231258, 49205461, 49185389, 49214468, 49183017,
                49223475, 49201970, 49235583
                ]

    for item_id in item_ids:
        print(f"start put {item_id}")
        await collector._queue.put(item_id)
    print(f"start put item_id NoNE")
    await collector._queue.put(None)
result_comments = []
# 处理一篇帖子
async def process_story(dbms:storage, client:AiClient, queue:asyncio.Queue) -> None:
    while True:
        story = await queue.get()
        if story is None:
            await queue.put(None)
            return None
        
        print(f'start process story {story["item_id"]}')
        try:
            await dbms.save_article(story)
            text = HackerNewsCollector.get_text(story)
            comments = HackerNewsCollector.get_comments(story)
            text = await client.summary_text(text)
            parsed_story = {
                "text":text,
                "comments":json.dumps(comments)
            }
            comments = await client.extract_comments(json.dumps(parsed_story))
            result_comments.extend(json.loads(comments))
        except Exception as e:
            logger.info(f'story {story["item_id"]} parse error')
        

async def run():

    global loop

    loop = asyncio.get_running_loop()

    signal.signal(
        signal.SIGUSR1,
        dump_signal
    )

    # util 导入即完成日志初始化和 config 加载
    collector = HackerNewsCollector()
    await collector.init()

    ai_client = AiClient(config["ai_api_url"], config["ai_api_key"])
    dbms = storage(config["raw_data_path"])

    ids_producer = asyncio.create_task(producer_item_ids(collector))

    item_queue = asyncio.Queue(10)

    item_producers_count = 20
    item_producers = [asyncio.create_task(collector.producer_item(item_queue), name = f"producer_item_{i}") for i in range(item_producers_count)]

    storage_customer_count = 4
    item_customers = [asyncio.create_task(process_story(dbms, ai_client, item_queue), name = f"process_story_{i}") for i in range(storage_customer_count)]

    await asyncio.gather(ids_producer, *item_producers)
    # item生产完毕, 设置终结
    await item_queue.put(None)
    await asyncio.gather(*item_customers)
    await dbms.save_comments(result_comments)

    await collector.destroy()

if __name__ == "__main__":
    
    asyncio.run(run())