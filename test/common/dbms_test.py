import pytest
import pytest_asyncio
from common.dbms import Dbms
@pytest.mark.asyncio(loop_scope="class")
class TestDbms:
    @pytest_asyncio.fixture(scope="function", loop_scope="class", autouse = True, name = "dbms")
    async def setup(self):
        dbms = Dbms()
        await dbms.init()
        yield dbms
        await dbms.destory()
    async def test_pg_pool_test(self, dbms):
        conn = await dbms.pg_pool.acquire()
        tr = conn.transaction()
        try:
            await tr.start()
            conn.execute("CREATE TABLE T0 (id INT)")
            conn.execute("DROP TABLE T0")
            await tr.commit()
        except Exception as e:
            await tr.rollback()
        await dbms.pg_pool.release(conn)
    