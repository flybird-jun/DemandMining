import pytest_asyncio
@pytest_asyncio.fixture(scope="class", loop_scope="session", autouse = False, name = "clean_env")
async def environment_clean():
    from common.dbms import Dbms

    dbms = Dbms()
    await dbms.init()
    # 执行一遍删除所有数据，防止用例之间的干扰
    try:
        async with dbms.pg_pool.acquire() as conn, conn.transaction():
            await conn.execute("Drop Table comment;")
            await conn.execute("Drop Table story;")
            await conn.execute("Drop Table storyhwm;")
    except Exception as e:
        print(f"{e}")
    
    await dbms.destory()