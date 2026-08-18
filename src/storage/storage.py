from pathlib import Path
import aiofiles
import asyncpg
from util.util import *
import asyncio
import subprocess
class Storage:

    def __init__(self, raw_data_path: str, dump_path: str):

        self._raw_data_path = Path(raw_data_path)
        if not self._raw_data_path.exists():
            self._raw_data_path.mkdir(parents=True, exist_ok=True)
        
        dump_dir_path = Path(dump_path)
        if not dump_dir_path.exists():
            dump_dir_path.mkdir(parents=True, exist_ok=True)
        self._db_dump_path = dump_dir_path / "backup.dump"
        self._pool:asyncpg.Pool

    async def init(self, user:str = "demand_mining", database:str = "demand_mining") -> None:
        try:
            self._pool = await asyncpg.create_pool(host="127.0.0.1", port=5432, user = user, database = database)
            async with self._pool.acquire() as conn, conn.transaction():
                exists = await conn.fetchval("SELECT EXISTS (SELECT 1 FROM information_schema.tables Where table_name = $1);",
                                             "storyhwm")
                print(f"init")
                if not exists:
                    await conn.execute("CREATE TABLE story (story_id BIGINT PRIMARY KEY, time BIGINT, title TEXT, type TEXT, Url TEXT, summary TEXT);")
                    await conn.execute("CREATE TABLE comment (comment_id BIGINT PRIMARY KEY, story_id BIGINT, time BIGINT, text TEXT, parent_id BIGINT NULL, "
                                       "FOREIGN KEY (story_id) REFERENCES story(story_id),"
                                       "FOREIGN KEY (parent_id) REFERENCES comment(comment_id));")
                    
                    await conn.execute("CREATE TABLE storyhwm (item_max_id BIGINT, ai_parse_time BIGINT);")
                    await conn.execute("INSERT INTO storyhwm VALUES(49300000, 0);")

        except Exception as e:
            await self._pool.close()
            logger.error(f"create postgres failed {type(e).__name__}: {e}")
            raise e
        
    async def destory(self) -> None:
        if hasattr(self, "_pool"):
            await self._pool.close()
            subprocess.run(["pg_dump",
                            "-h", "localhost",
                            "-p", "5432",
                            "-U", "postgres",
                            "-d", "demand_mining",
                            "-F", "c",
                            "-f", f"{self._db_dump_path}",
                        ], check=True)

    async def update_item_id_hwm(self, item_max_id:int) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("Update storyhwm Set item_max_id = $1 WHERE item_max_id < $1;", item_max_id)

    async def update_ai_parse_time(self, ai_parse_time:int) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("Update storyhwm Set ai_parse_time = $1 WHERE ai_parse_time < $1;", ai_parse_time)

    async def get_item_id_hwm(self) -> int:
        async with self._pool.acquire() as conn:
            return await conn.fetchval("Select item_max_id From storyhwm;")
        
    async def get_story_ids(self) -> list:
        async with self._pool.acquire() as conn, conn.transaction():
            hwm =  await conn.fetchrow("Select item_max_id, ai_parse_time From storyhwm;")
            new_ai_parse_time = conn.fetch("Select time From story Where id =$1;", hwm["item_max_id"])

            rows = await conn.fetch("Select story_id From story Where time > $1 And time <= $2;", 
                                    hwm["ai_parse_time"], new_ai_parse_time)
            if rows is None:
                return []
            result = [row["story_id"] for row in rows]
            return result
    
    """
    返回格式：
    {
        "text":"",
        "comment":[""]
    }
    """
    async def get_story(self, story_id:int) -> dict:
        async with self._pool.acquire() as conn:
            result = {}
            story_info = await conn.fetchrow("Select title, summary From story Where story_id = $1", story_id)
            if len(story_info) == 0:
                return result
            
            result["text"] = story_info["title"] + "," + story_info["summary"]
            
            rows = await conn.fetch("Select text From comment Where story_id = $1 ", story_id)
            if len(story_info) == 0:
                return result
            result["comment"] = [row["text"] for row in rows]
            return result
        
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
            logger.error(f"{item_id} text save failed, error = {type(e).__name__}:'{e}'")

    """
    story 格式:
    {
        id: int,
        time: int,
        title: str,
        type: str,
        url: str,
        summary: str
    }
    """
    async def save_story(self, story: dict) -> None:
        sql_args = (story["id"], story["time"], story["title"], story["type"], story["url"], story["summary"])
        async with self._pool.acquire() as conn:
            await conn.execute("INSERT INTO story (story_id, time, title, type, Url, summary) VALUES ($1, $2, $3, $4, $5, $6);", *sql_args)

    """
    comment 格式:
    {
        "id": int,
        "parent": int,
        "text": str,
        "time": int
    }
    """
    async def save_comment(self, comment: dict) -> None:
        parent_id = comment["parent"]
        async with self._pool.acquire() as conn, conn.transaction():
            story_id = await self._search_story_id(conn, parent_id)
            if parent_id == story_id:
                sql_args = (comment["id"], story_id, comment["time"], comment["text"], None)
            else:
                sql_args = (comment["id"], story_id, comment["time"], comment["text"], parent_id)
            try:
                await conn.execute("INSERT INTO comment (comment_id, story_id, time, text, parent_id) "
                                "VALUES ($1, $2, $3, $4, $5);", *sql_args)
                await conn.execute("Update story Set time = $1 Where story_id = $2;", comment["time"], story_id)
            except asyncpg.UniqueViolationError:
                logger.info(f"pg unique violation, item_id = f{comment['id']}")

    async def _search_story_id(self, conn, parent_id: int) -> int:
        id = await conn.fetchval("SELECT story_id FROM story WHERE story_id = $1;", parent_id)
        if id is not None:
            return id
        # 插入到数据库中评论一定有story_id, 否则就报异常了
        id = await conn.fetchval("SELECT story_id FROM comment WHERE comment_id = $1;", parent_id)
        if id is not None:
            return id
        
        raise ParentException

    async def _get_ai_parse_time(self) -> int:
        async with self._pool.acquire() as conn:
            return await conn.fetchval("Select ai_parse_time From storyhwm;")
