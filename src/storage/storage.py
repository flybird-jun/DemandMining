from datetime import datetime
from pathlib import Path
import asyncio
import json
import aiofiles
class storage:

    def __init__(self, raw_data_path:str):
        self._raw_data_path = raw_data_path

    async def save_article(self, data:dict) -> None:
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
    async def save_comments(self, comments:list) -> None:
        c = Path(self._raw_data_path) / "comments.json"
        async with aiofiles.open(c, "w", encoding="utf-8") as fd:
            await fd.write(json.dumps(comments, ensure_ascii = False, indent = 4))