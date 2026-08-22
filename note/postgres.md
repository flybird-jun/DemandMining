
# pg接口
```
# 单连接
conn = await asyncpg.connect(host="localhost", port=5432, user="postgres", password="password", database="mydb")
conn.close()
# 单行数据
row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", 123,)
print(row)
print(row["name"])
row_data = dict(row)

# 多行数据
rows = await conn.fetch("SELECT * FROM users WHERE status = $1", "active")
for row in rows:
    print(row["id"], row["name"])

# 其他DML
result = await conn.execute("""UPDATE usersSET name = $1 WHERE id = $2""", "Jack", 123)
print(result)

# prepare语句
stmt = await conn.prepare("""SELECT * FROM users WHERE id = $1""")
row = await stmt.fetchrow(123)

# 事务
async with conn.transaction():
    await conn.execute("UPDATE accounts SET balance = balance - $1 WHERE id = $2", 100, 1)
    await conn.execute("UPDATE accounts SET balance = balance + $1 WHERE id = $2", 100, 2)

# 连接池
pool = await asyncpg.create_pool(host="localhost", port=5432, user="postgres", password="password", database="mydb", min_size=5, max_size=20)

async with pool.acquire() as conn:
    row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", 123)

# 批量数据
await conn.executemany("""INSERT INTO users(name, age) VALUES($1, $2) """, [("Alice", 20), ("Bob", 30), ("Charlie", 25)])
await conn.copy_records_to_table("users", records=[("Alice", 20), ("Bob", 30)], columns=["name", "age"])

```
# pg服务进程
拉起服务:sudo systemctl start postgresql
停止服务:sudo systemctl stop postgresql
查看状态:sudo systemctl status postgresql

拉起指定cluster:sudo pg_ctlcluster 14 demand_mining start
关闭指定cluster:sudo pg_ctlcluster 14 demand_mining stop
重启指定cluster:pg_ctlcluster 14 demand_mining restart
查看指定cluster状态:pg_ctlcluster 14 demand_mining status
查看所有cluster状态:pg_lsclusters
创建cluster:sudo pg_createcluster 14 demand_mining

导出数据库:pg_dump -U postgres -d demand_mining -Fc -f demand_mining.dump
数据库恢复:pg_restore -U postgres -d demand_mining ./data/database/demand_mining.dump

# 14是版本号，main是cluster名称

进入postgres: sudo -u postgres psql
创建用户: CREATE USER demand_mining WITH PASSWORD 'xxx';
创建Db:CREATE DATABASE demand_mining;
更改db权限:postgres=# ALTER DATABASE demand_mining OWNER TO demand_mining;
使用用户登录pg:psql -h localhost -p 5432 -U demand_mining -d demand_mining
