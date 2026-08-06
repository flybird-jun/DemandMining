from pathlib import Path
import json
import logging
from common.config import settings
import asyncpg
from pgvector.asyncpg import register_vector

import subprocess

logger = logging.getLogger(__name__)
class Dbms:
    def __init__(self):
        dump_dir_path = Path(settings.DATA_PATH) / "database"
        if not dump_dir_path.exists():
            dump_dir_path.mkdir(parents=True, exist_ok=True)
        self._db_dump_path = dump_dir_path / "backup.dump"
        self.pg_pool:asyncpg.Pool

    async def init(self) -> None:
        async def init_connection(conn):
            await register_vector(conn)
            await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
        try:
            self.pg_pool = await asyncpg.create_pool(host=settings.PG_HOST, port=settings.PG_PORT,
                                                     user=settings.PG_USER,
                                                     password = settings.PG_USER_PASSWD,
                                                     database=settings.PG_DATABASE,
                                                     init=init_connection)
        except Exception as e:
            logger.error(f"create postgres failed {type(e).__name__}: {e}")
            raise

    async def destroy(self) -> None:
        if hasattr(self, "pg_pool"):
            await self.pg_pool.close()
            # subprocess.run(["pg_dump",
            #                 "-h", "localhost",
            #                 "-p", "5432",
            #                 "-U", "postgres",
            #                 "-d", "demand_mining",
            #                 "-F", "c",
            #                 "-f", f"{self._db_dump_path}",
            #             ], check=True)
    