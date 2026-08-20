from pathlib import Path
import aiofiles
import asyncpg
from util.util import *
from common.dbms import Dbms
class HackerNewsStorage:
    def __init__(self):
        self._raw_data_path = Path(config["raw_data_path"])
        if not self._raw_data_path.exists():
            self._raw_data_path.mkdir(parents=True, exist_ok=True)
        self._dbms = Dbms()

    async def init(self) -> None:
        try:
            await self._dbms.init()
            async with self._dbms.pg_pool.acquire() as conn, conn.transaction():
                exists = await conn.fetchval("SELECT EXISTS "
                    "(SELECT 1 FROM information_schema.tables Where table_name = 'storyhwm');")
                if not exists:
                    await conn.execute("CREATE TABLE story "
                        "(story_id BIGINT PRIMARY KEY, time BIGINT, title TEXT, type TEXT, Url TEXT);")
                    await conn.execute("CREATE TABLE comment "
                        "(comment_id BIGINT PRIMARY KEY, time BIGINT, text TEXT, parent_id BIGINT NULL, "
                        "FOREIGN KEY (parent_id) REFERENCES comment(comment_id));")
                    
                    await conn.execute("CREATE TABLE storyhwm (item_max_id BIGINT, parsed_item_hwm BIGINT);")
                    await conn.execute("INSERT INTO storyhwm VALUES(49300000, 0);")

                    logger.info("storage init succ")
                else:
                    logger.info("storage loaded")

        except Exception as e:
            logger.error(f"create postgres failed {type(e).__name__}: {e}")
            raise e

    async def destory(self) -> None:
        await self._dbms.destory()
    
    async def update_item_id_hwm(self, item_max_id:int) -> None:
        try:
            async with self._dbms.pg_pool.acquire() as conn:
                await conn.execute("Update storyhwm Set item_max_id = $1 WHERE item_max_id < $1;", item_max_id)
        except Exception as e:
            logger.exception(f"update_item_id_hwm item_id = {item_max_id} failed, error = {type(e).__name__}:'{e}'")
            raise e

    async def get_item_id_hwm(self) -> int:
        try:
            async with self._dbms.pg_pool.acquire() as conn:
                return await conn.fetchval("Select item_max_id From storyhwm;")
        except Exception as e:
            logger.exception(f"get_item_id_hwm failed, error = {type(e).__name__}:'{e}'")
            raise e
    # 保存原始文本到磁盘
    async def save_story_text(self, item_id: int, story_text: str) -> None:
        if story_text == "":
            logger.info(f"{item_id} story text is nullptr")
            return

        file_path = self._raw_data_path / f"{item_id}"
        try:
            async with aiofiles.open(file_path, "w", encoding="utf-8") as fd:
                await fd.write(story_text)
        except Exception as e:
            logger.exception(f"{item_id} text save failed, error = {type(e).__name__}:'{e}'")


    async def update_parsed_item_hwm(self, parsed_item_hwm:int) -> None:
        try:
            async with self._dbms.pg_pool.acquire() as conn:
                await conn.execute("Update storyhwm Set parsed_item_hwm = $1 WHERE parsed_item_hwm < $1;", parsed_item_hwm)
        except Exception as e:
            logger.exception(f"save parsed_item = {parsed_item_hwm} failed, error = {type(e).__name__}:'{e}'")
            raise e
        
    async def get_parsed_item_hwm(self, parsed_item_hwm:int) -> int:
            try:
                async with self._dbms.pg_pool.acquire() as conn:
                    return await conn.execute("Select parsed_item_hwm From storyhwm;")
            except Exception as e:
                logger.exception(f"save parsed_item = {parsed_item_hwm} failed, error = {type(e).__name__}:'{e}'")
                raise e

    async def save_item(self, item:dict) -> None:
        if item["type"] == "story":
            await self._save_story(item)
        elif item["type"] == "comment":
            await self._save_comment(item)
        
    async def _save_story(self, story: dict) -> None:
        try:
            sql_args = (story["id"], story["time"], story["title"], story["type"], story["url"])
            async with self._dbms.pg_pool.acquire() as conn:
                await conn.execute("INSERT INTO story (story_id, time, title, type, Url) VALUES ($1, $2, $3, $4, $5);", *sql_args)
        except Exception as e:
            logger.exception(f"{story['id']} save story failed, error = {type(e).__name__}:'{e}'")
            raise e
    
    async def _save_comment(self, comment: dict) -> None:
        try:
            async with self._dbms.pg_pool.acquire() as conn, conn.transaction():
                sql_args = (comment["id"], comment["time"], comment["text"], comment["parent"])
                await conn.execute("INSERT INTO comment (comment_id, time, text, parent_id) "
                                "VALUES ($1, $2, $3, $4);", *sql_args)
        except asyncpg.UniqueViolationError:
            logger.info(f"pg unique violation, item_id = f{comment['id']}")
        except Exception as e:
            logger.exception(f"{comment['id']} save comment failed, error = {type(e).__name__}:'{e}'")
            raise e
    