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
        self._delta_story_sql = (Path(__file__).parent / "group_new_comments_by_story.sql").read_text()
    async def init(self) -> None:
        try:
            await self._dbms.init()
            async with self._dbms.pg_pool.acquire() as conn, conn.transaction():
                exists = await conn.fetchval("SELECT EXISTS "
                    "(SELECT 1 FROM information_schema.tables Where table_name = 'hwm');")
                if not exists:
                    await conn.execute("CREATE TABLE story "
                        "(story_id BIGINT PRIMARY KEY, time BIGINT, title TEXT, type TEXT, Url TEXT);")
                    await conn.execute("CREATE TABLE comment "
                        "(comment_id BIGINT PRIMARY KEY, time BIGINT, text TEXT, parent_id BIGINT);")
                    
                    await conn.execute("CREATE TABLE hwm (item_max_id BIGINT, parsed_item_hwm BIGINT, filter_rule_hwm BIGINT);")

                    await conn.execute("CREATE TABLE filter_rule "
                                       "(id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, story_id BIGINT, comment_id BIGINT UNIQUE);")

                    await conn.execute("INSERT INTO hwm VALUES(49300000, 0, 0);")

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
                x = await conn.execute("Update hwm Set item_max_id = $1 WHERE item_max_id < $1;", item_max_id)
                print(x)
        except Exception as e:
            logger.exception(f"update_item_id_hwm item_id = {item_max_id} failed, error = {type(e).__name__}:'{e}'")
            raise e

    async def get_item_id_hwm(self) -> int:
        try:
            async with self._dbms.pg_pool.acquire() as conn:
                x = await conn.fetchval("Select item_max_id From hwm;")
                return x
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
                await conn.execute("Update hwm Set parsed_item_hwm = $1 WHERE parsed_item_hwm < $1;", parsed_item_hwm)
        except Exception as e:
            logger.exception(f"save parsed_item = {parsed_item_hwm} failed, error = {type(e).__name__}:'{e}'")
            raise e
        
    async def get_parsed_item_hwm(self) -> int:
            try:
                async with self._dbms.pg_pool.acquire() as conn:
                    return await conn.fetchval("Select parsed_item_hwm From hwm;")
            except Exception as e:
                logger.exception(f"get parsed_item failed, error = {type(e).__name__}:'{e}'")
                raise e

    async def save_item(self, item:dict) -> None:
        if item["type"] == "story":
            await self._save_story(item)
        elif item["type"] == "comment":
            await self._save_comment(item)
    # 返回[min_item_id, max_item_id]之间的被改动过的story和评论
    async def get_delta_origin_infos(self, min_item_id:int, max_item_id:int):
        try:
            async with self._dbms.pg_pool.acquire() as conn:
                return await conn.fetch(self._delta_story_sql, min_item_id, max_item_id)
        except Exception as e:
            logger.exception(f"step1_resolve_comment_groups failed, error = {type(e).__name__}:'{e}'")
            raise e
        
    async def get_comment(self, comment_id:int):
        try:
            async with self._dbms.pg_pool.acquire() as conn:
                return await conn.fetchrow("Select * From comment Where comment_id = $1;", comment_id)
        except Exception as e:
            logger.exception(f"get_comment failed, error = {type(e).__name__}:'{e}'")
            raise e
        
    async def get_story(self, story_id:int):
        try:
            async with self._dbms.pg_pool.acquire() as conn:
                return await conn.fetchrow("Select * From story Where story_id = $1;", story_id)
        except Exception as e:
            logger.exception(f"get_story failed, error = {type(e).__name__}:'{e}'")
            raise e
        
    async def save_filter_rule(self, story_id:int | None, comment_id:int) -> None:
        try:
            async with self._dbms.pg_pool.acquire() as conn:
                await conn.execute("INSERT INTO filter_rule (story_id, comment_id) VALUES ($1, $2);", story_id, comment_id)
        except asyncpg.UniqueViolationError:
            logger.info(f"save_filter_rule unique violation, comment_id = {comment_id}")
        except Exception as e:
            logger.exception(f"save_filter_rule failed, error = {type(e).__name__}:'{e}'")
            raise e
        
    async def save_filter_rule_hwm(self) -> None:
        try:
            async with self._dbms.pg_pool.acquire() as conn:
                filter_rule_hwm = await conn.fetchval("SELECT pg_get_serial_sequence('filter_rule', 'id');") # 会消耗一个id
                await conn.execute("Update hwm Set filter_rule_hwm = $1 WHERE filter_rule_hwm < $1;", filter_rule_hwm)
        except Exception as e:
            logger.exception(f"save filter_rule_hwm failed, error = {type(e).__name__}:'{e}'")
            raise e   
        
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
