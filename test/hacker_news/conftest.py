import pytest_asyncio
from pathlib import Path
@pytest_asyncio.fixture(scope="class", loop_scope="session", autouse = False, name = "clean_env")
async def environment_clean():
    from common.dbms import Dbms
    from hacker_news.hacker_news_storage import HackerNewsTable, HackerNewsAuxTable
    dbms = Dbms()
    await dbms.init()
    # 执行一遍删除所有数据，防止用例之间的干扰
    try:
        async with dbms.pg_pool.acquire() as conn, conn.transaction():
            for table in HackerNewsTable:
                await conn.execute(f"DROP TABLE IF EXISTS {table.name};")
            for table in HackerNewsAuxTable:
                await conn.execute(f"DROP TABLE IF EXISTS {table.name};")
    except Exception as e:
        raise
    
    await dbms.destroy()

    file_path = Path(__file__).resolve().parent / "output"

    file_path.mkdir(parents=True, exist_ok=True)