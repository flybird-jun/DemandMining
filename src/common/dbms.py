from pathlib import Path
import aiofiles
import asyncpg
from util.util import *
import asyncio
import subprocess
class Dbms:
    def __init__(self):
        dump_dir_path = Path(config["database_path"])
        if not dump_dir_path.exists():
            dump_dir_path.mkdir(parents=True, exist_ok=True)
        self._db_dump_path = dump_dir_path / "backup.dump"
        self.pg_pool:asyncpg.Pool

    async def init(self) -> None:
        try:
            self.pg_pool = await asyncpg.create_pool(host="127.0.0.1", port=5432,
                                                     user = config["pg_user"],
                                                     database = config["pg_database_name"])
        except Exception as e:
            logger.error(f"create postgres failed {type(e).__name__}: {e}")
            raise e

    async def destory(self) -> None:
        if hasattr(self, "pg_pool"):
            await self.pg_pool.close()
            subprocess.run(["pg_dump",
                            "-h", "localhost",
                            "-p", "5432",
                            "-U", "postgres",
                            "-d", "demand_mining",
                            "-F", "c",
                            "-f", f"{self._db_dump_path}",
                        ], check=True)
    