from datetime import datetime
from pathlib import Path
import asyncio
import json
import aiofiles
class storage:

    def __init__(self, raw_data_path:str):
        self._raw_data_path = raw_data_path

    async def save_article(self, queue:asyncio.Queue) -> None:
        while True:
            data = await queue.get()
            if data is None:
                await queue.put(None)
                return
            await self._save_article(data)
    
    async def _save_article(self, data:dict) -> None:
        now = datetime.now()
        timestamp = now.strftime("%Y_%m_%d_%H_%M_%S_%f")
        timestamp = timestamp[:-3]
        today = now.strftime("%Y_%m_%d")

        directory = Path(self._raw_data_path) / today
        directory.mkdir(parents=True, exist_ok=True)
        file_path = directory / f"{timestamp}.json"

        json_str = json.dumps(data, ensure_ascii = False, indent = 4)
        async with aiofiles.open(file_path, "w", encoding="utf-8") as fd:
            await fd.write(json_str)