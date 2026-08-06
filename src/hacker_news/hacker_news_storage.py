from pathlib import Path
from enum import Enum
from datetime import date
import logging
import aiofiles
import asyncpg

from common.config import settings
from common.dbms import Dbms

logger = logging.getLogger(__name__)
class HackerNewsTable(Enum):
    def __init__(self, schema:str, values:str) -> None:
        self.schema = schema
        self.values = values
    @property
    def low_hwm(self):
        return f"{self.name}_low"
    @property
    def high_hwm(self):
        return f"{self.name}_high"
    @property
    def previous(self):
        members = list(type(self))
        index = members.index(self)
        if index == 0:
            return None
        return members[index - 1]
    @property
    def next(self):
        members = list(type(self))
        index = members.index(self)
        if index == len(members) - 1:
            return None
        return members[index + 1]
    
    hacker_news = ("(data JSONB)", "Values ($1)")
    # filter = ("(id BIGSERIAL PRIMARY KEY, story_id BIGINT NULL, comment_id BIGINT UNIQUE)", "Values ($1, $2)")
    filter = ("(item_id BIGINT, text Text, id BIGSERIAL PRIMARY KEY)", "Values ($1, $2)")
    demand_object = ("(data JSONB, embedding VECTOR(1024), id BIGSERIAL PRIMARY KEY)", "Values ($1, $2)")
    # demand_object = ("(item_id BIGINT PRIMARY KEY, data JSONB, embedding VECTOR(1024))", "Values ($1, $2, $3)")
    score = ("(item_id BIGINT, score INT, id BIGSERIAL PRIMARY KEY)", "Values ($1, $2)")
    #score = ("(item_id BIGINT, score INT)", "Values ($1, $2)")
    solution = ("(item_id BIGINT, demand_id BIGINT, id BIGSERIAL PRIMARY KEY)", "Values ($1, $2)")

class HackerNewsAuxTable(Enum):
    def __init__(self, schema:str, values:str) -> None:
        self.schema = schema
        self.values = values
    story_summary = ("(item_id BIGINT PRIMARY KEY, summary Text)", "Values ($1, $2)")
    hwm = (f"({', '.join( f'{table.low_hwm} BIGINT, {table.high_hwm} BIGINT' for table in HackerNewsTable)})",
            "Values (" + ", ".join(f"${i}" for i in range(1, len(HackerNewsTable) * 2 + 1)) + ")")
class HackerNewsStorage:
    def __init__(self):
        self._raw_data_path = Path(settings.DATA_PATH) / "raw_data"
        self._solution_path = Path(settings.DATA_PATH) / "solution"
        if not self._raw_data_path.exists():
            self._raw_data_path.mkdir(parents=True, exist_ok=True)
        if not self._solution_path.exists():
            self._solution_path.mkdir(parents=True, exist_ok=True)
        self._dbms = Dbms()

    async def init(self) -> None:
        try:
            await self._dbms.init()
            async with self._dbms.pg_pool.acquire() as conn, conn.transaction():
                exists = await conn.fetchval("SELECT EXISTS "
                    "(SELECT 1 FROM information_schema.tables Where table_name = 'hwm');")
                if not exists:
                    for table in HackerNewsTable:
                        await conn.execute(f"CREATE TABLE {table.name} {table.schema};")
                    await conn.execute(f"CREATE Index demand_embedding ON {HackerNewsTable.demand_object.name} USING hnsw (embedding vector_cosine_ops);")
                    for table in HackerNewsAuxTable:
                        await conn.execute(f"CREATE TABLE {table.name} {table.schema};")
                    hwms = [0] * (len(HackerNewsTable) * 2)
                    hwms[0] = 49300000
                    hwms[1] = 49300000
                    await conn.execute(f"INSERT INTO {HackerNewsAuxTable.hwm.name} {HackerNewsAuxTable.hwm.values};", *hwms)

                    logger.warning("storage init succ")
                else:
                    logger.warning("storage loaded")

        except Exception as e:
            logger.error(f"create postgres failed {type(e).__name__}: {e}")
            raise

    async def destroy(self) -> None:
        await self._dbms.destroy()

    async def fetch_hwm(self, table:HackerNewsTable, is_low:bool) -> int:
        if is_low:
            hwm_name = table.low_hwm
        else:
            hwm_name = table.high_hwm
        try:
            async with self._dbms.pg_pool.acquire() as conn:
                return await conn.fetchval(f"Select {hwm_name} From hwm;")
        except Exception as e:
            logger.exception(f"fetch_hwm {HackerNewsAuxTable.hwm.name} failed, error = {type(e).__name__}:'{e}'")
            raise

    async def update_hwm(self, table:HackerNewsTable, is_low:bool, new_hwm:int):
        if is_low:
            hwm_name = table.low_hwm
        else:
            hwm_name = table.high_hwm

        try:
            async with self._dbms.pg_pool.acquire() as conn:
                await conn.execute(f"Update hwm Set {hwm_name} = $1 WHERE {hwm_name} < $1;", new_hwm)
        except Exception as e:
            logger.exception(f"update {hwm_name} hwm failed, error = {type(e).__name__}:'{e}'")
            raise

    async def insert(self, table:HackerNewsTable|HackerNewsAuxTable, *args):
        try:
            async with self._dbms.pg_pool.acquire() as conn:
                await conn.execute(f"INSERT INTO {table.name} {table.values};", *args)
        except asyncpg.UniqueViolationError:
            logger.warning(f"insert {table.name} failed for unique violation, {args}")
        except Exception as e:
            logger.exception(f"insert {table.name} failed, error = {type(e).__name__}:'{e}'")
            raise
        
    async def fetch(self, table:HackerNewsTable, min_id:int, max_id:int) -> list:
        method_name = f"_fetch_from_{table.name}"
        fetcher = getattr(self, method_name)
        return await fetcher(min_id, max_id)
    
    async def fetch_sequence_id(self, table:HackerNewsTable) -> int:
        try:
            async with self._dbms.pg_pool.acquire() as conn:
                seq_name = await conn.fetchval("SELECT pg_get_serial_sequence($1, 'id');", table.name)
                result = await conn.fetchval(f"SELECT last_value FROM {seq_name};")
                return result
        except Exception as e:
            logger.exception(f"fetch_sequence_id {table.name} failed, error = {type(e).__name__}:'{e}'")
            raise
        
    async def save_story_text(self, item_id: int, story_text: str) -> None:
        if story_text == "":
            logger.warning(f"{item_id} story text is nullptr")
            return

        file_path = self._raw_data_path / f"{item_id}"
        try:
            async with aiofiles.open(file_path, "w", encoding="utf-8") as fd:
                await fd.write(story_text)
        except Exception as e:
            logger.exception(f"{item_id} text save failed, error = {type(e).__name__}:'{e}'")

    async def get_story_text(self, item_id:int) -> str:
        file_path = self._raw_data_path / f"{item_id}"
        if not file_path.exists():
            return ""
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as fd:
                return await fd.read()
        except Exception as e:
            logger.exception(f"{item_id} get_story_text failed, error = {type(e).__name__}:'{e}'")
            raise

        
    async def fetchrow_from_hacker_news(self, item_id:int) -> dict:
        try:
            async with self._dbms.pg_pool.acquire() as conn:
                result = await conn.fetchval(f"Select data From {HackerNewsTable.hacker_news.name} Where (data->>'id')::BIGINT = $1;", item_id)
                assert result is not None
                return dict(result)
        except Exception as e:
            logger.exception(f"fetch {HackerNewsTable.hacker_news.name} item_id = {item_id} failed, error = {type(e).__name__}:'{e}'")
            raise
        
    # 具体多少算相似
    async def check_demand_repeat(self, embedding:list) -> bool:
        try:
            async with self._dbms.pg_pool.acquire() as conn:
                result = await conn.fetchval(f"SELECT EXISTS (SELECT 1 FROM {HackerNewsTable.demand_object.name} WHERE embedding <=> $1 < 0.1 LIMIT 1);", embedding)
                return bool(result)
        except Exception as e:
            logger.exception(f"fetch_comment_ids_from_filter failed, error = {type(e).__name__}:'{e}'")
            raise
        
    async def save_solution(self, item_id:int, solution:str):
        today = date.today()
        file_path = self._solution_path / f"{today}"
        if not file_path.exists():
            file_path.mkdir(parents=True, exist_ok=True)
        file_path = file_path / f"{item_id}"
        try:
            async with aiofiles.open(file_path, "w", encoding="utf-8") as fd:
                await fd.write(solution)
        except Exception as e:
            logger.exception(f"{item_id} save_solution failed, error = {type(e).__name__}:'{e}'")
            raise
    
    async def _fetch_from_hacker_news(self, min_item_id:int, max_item_id:int) -> list:
        map_item_parent = {}
        try:
            async with self._dbms.pg_pool.acquire() as conn:
                map_helper = {}
                result = []

                rows = await conn.fetch("SELECT data FROM hacker_news WHERE (data->>'id')::BIGINT BETWEEN $1 AND $2 AND data->>'type' = 'comment'",
                    min_item_id,max_item_id)
                for row in rows:
                    map_item_parent[row['data']['id']] = row['data']['parent']

                for row in rows:
                    comment = row["data"]
                    parent_id = comment["parent"]
                    story_id = None
                    
                    while parent_id is not None:
                        if parent_id in map_item_parent.keys():
                            if map_item_parent[parent_id] == 0:
                                story_id = parent_id
                                break
                            parent_id = map_item_parent[parent_id]       
                        else:
                            parent = await conn.fetchrow("SELECT data FROM hacker_news WHERE (data->>'id')::BIGINT = $1", parent_id)
                            if parent is None:
                                break
                            if parent['data']['type'] == "story":
                                story_id = parent['data']['id']
                                map_item_parent[story_id] = 0
                                break
                            map_item_parent[parent_id] = parent['data']['parent']
                            parent_id = parent['data']['parent']
                    
                    if story_id not in map_helper:
                        map_helper[story_id] = len(result)

                        result.append({'story_id':story_id, 'comments':[]})

                    result[map_helper[story_id]]['comments'].append({'item_id': comment['id'], 'text': comment['text'], 'parent': comment['parent']})
                return result
        except Exception as e:
            logger.exception(f"_fetch_from_hacker_news failed, error = {type(e).__name__}:'{e}'")
            raise
            
    async def _fetch_from_filter(self, min_id:int, max_id:int) -> list:
        results = []
        try:
            async with self._dbms.pg_pool.acquire() as conn:
                rows = await conn.fetch(f"Select item_id, text From {HackerNewsTable.filter.name} Where id > $1 And id <= $2", min_id, max_id)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.exception(f"fetch_from_filter failed, error = {type(e).__name__}:'{e}'")
            raise
        
    async def _fetch_from_demand_object(self, min_id:int, max_id:int) -> list:
        try:
            async with self._dbms.pg_pool.acquire() as conn:
                rows = await conn.fetch(f"SELECT data FROM {HackerNewsTable.demand_object.name} WHERE id > $1 And id <= $2", min_id, max_id)
                return [dict(row['data']) for row in rows]
        except Exception as e:
            logger.exception(f"fetch_from_demand failed, error = {type(e).__name__}:'{e}'")
            raise
        
    async def _fetch_from_score(self, min_id:int, max_id:int) -> list:
        try:
            async with self._dbms.pg_pool.acquire() as conn:
                rows = await conn.fetch(f"SELECT item_id FROM {HackerNewsTable.score.name} "
                                        "WHERE id > $1 And id <= $2 And score >= 70", min_id, max_id)
                results = []
                for row in rows:
                    demand_object = await self._fetchrow_from_demand(row['item_id'])
                    results.append(demand_object)
                return results
        except Exception as e:
            logger.exception(f"fetch_from_score failed, error = {type(e).__name__}:'{e}'")
            raise
        
    async def _fetchrow_from_demand(self, item_id:int) -> dict|None:
        try:
            async with self._dbms.pg_pool.acquire() as conn:
                row = await conn.fetchval(f"SELECT data FROM {HackerNewsTable.demand_object.name} WHERE (data->>'item_id')::BIGINT = $1", item_id)
                if row is None:
                    return None
                return dict(row)
        except Exception as e:
            logger.exception(f"fetchrow_from_demand item_id = {item_id} failed, error = {type(e).__name__}:'{e}'")
            raise
    async def fetchrow_from_summary_text(self, item_id) -> str:
        try:
            async with self._dbms.pg_pool.acquire() as conn:
                row = await conn.fetchval(f"SELECT summary FROM {HackerNewsAuxTable.story_summary.name} WHERE item_id = $1", item_id)
                if row is None:
                    return ""
                return str(row)
        except Exception as e:
            logger.exception(f"fetchrow_from_summary_text failed, error = {type(e).__name__}:'{e}'")
            raise