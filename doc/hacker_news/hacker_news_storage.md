# HackerNewsStorage 外部接口文档

## 枚举类型

# HackerNewsTable
## 描述
HackerNews 流水线所有主表的枚举, 枚举定义顺序即流水线阶段顺序: hacker_news → filter → demand_object → score

## 成员
| 名称 | schema | 含义 |
|---|---|---|
| hacker_news | (data JSONB) | 原始 HN item (story / comment) 的 JSONB 数据 |
| filter | (id BIGSERIAL PK, story_id BIGINT NULL, comment_id BIGINT UNIQUE) | 通过规则 + 语义过滤后的评论 |
| demand_object | (id BIGSERIAL PK, data JSONB, embedding VECTOR(1024)) | 抽取出的需求对象, 含 1024 维向量 |
| score | (id BIGSERIAL PK, item_id BIGINT, score INT) | 需求对应的产品评分 |

## 属性
- `schema: str` — 建表语句的字段定义部分
- `values: str` — INSERT 语句的 `Values ($1, ...)` 部分
- `low_hwm: str` — hwm 表中该表的低水位线列名, 形如 `{name}_low`
- `high_hwm: str` — hwm 表中该表的高水位线列名, 形如 `{name}_high`
- `previous: HackerNewsTable | None` — 枚举中的前一个成员 (即流水线上一阶段的输出表), hacker_news 为 None

---

# HackerNewsAuxTable
## 描述
辅助表枚举, 不参与流水线阶段推进

## 成员
| 名称 | schema | 含义 |
|---|---|---|
| story_summary | (item_id BIGINT PK, summary Text) | story 正文摘要 |
| hwm | (每个主表各一对 `{name}_low BIGINT, {name}_high BIGINT`) | 全局水位线单行表 |

## 属性
- `schema: str` — 建表语句的字段定义部分
- `values: str` — INSERT 语句的 `Values ($1, ...)` 部分

---

## HackerNewsStorage 类

# def __init__(self)
## 描述
构造实例: 按 config 中的 `raw_data_path` / `solution_path` 创建本地目录 (不存在则递归创建), 并构造 Dbms 客户端 (此时尚未连接数据库)
## input
无
## output
None

---

# async def init(self) -> None
## 描述
- 初始化底层 Dbms 连接池
- 在同一事务内检查 `hwm` 表是否存在: 不存在则创建所有 HackerNewsTable 表、为 demand_object.embedding 创建 hnsw (vector_cosine_ops) 索引, 并向 hwm 插入一行初始水位
- 初始水位除 `hacker_news_high` 预置为 49300000 外其余均为 0, 避免从 0 起步触发全量拉取
- 已存在则直接复用
- 失败时记录日志并抛出原异常
## input
无
## output
None

---

# async def destroy(self) -> None
## 描述
关闭底层 Dbms 连接池
## input
无
## output
None

---

# async def fetch_hwm(self, table:HackerNewsTable, is_low:bool) -> int
## 描述
从 hwm 表读取指定表的当前水位线值
## input
- table: HackerNewsTable 枚举, 目标表
- is_low: bool, True 取低水位线 (`{name}_low`), False 取高水位线 (`{name}_high`)
## output
int, 当前水位线值

---

# async def update_hwm(self, table:HackerNewsTable, is_low:bool, new_hwm:int) -> None
## 描述
- 将 hwm 表中指定水位线字段更新为 new_hwm
- **仅当原值 < new_hwm 时才生效**, 即水位线只能向前推进, 不会回退
## input
- table: HackerNewsTable 枚举, 要更新的表
- is_low: bool, True 更新低水位线, False 更新高水位线
- new_hwm: int, 新的水位线值
## output
None

---

# async def insert(self, table:HackerNewsTable|HackerNewsAuxTable, *args) -> None
## 描述
- 向指定表插入一行数据, 参数顺序需与该表 schema 占位符一一对应
- 命中 UNIQUE 约束 (asyncpg.UniqueViolationError) 时仅记录日志, 不抛异常; 其他异常记录日志后抛出
## input
- table: HackerNewsTable 或 HackerNewsAuxTable 枚举, 目标表
- *args: 与表 schema 顺序一致的字段值
  + `HackerNewsTable.hacker_news` 传入一个 dict (JSONB), 格式为:
    ```python
    {
      'id':int,
      'time':int,
      'title':str,
      'type':str,   # 'story'
      'url':str
    }
    # 或
    {
      'id':int,
      'time':int,
      'text':str,
      'type':str,   # 'comment'
      'parent':int
    }
    ```
  + `HackerNewsTable.filter` 按顺序传入 story_id:int、comment_id:int
  + `HackerNewsTable.demand_object` 按顺序传入 item_id:int、dict、embedding (1024 维 list[float]), 其中 dict 格式为:
    ```python
    {
        "item_id": int,
        "demand_type": [str],
        "persona": str,
        "problem": str,
        "context": str,
        "job_to_be_done": str,
        "current_solution": str,
        "severity": int,
        "confidence": float,
        "evidence": str,
        "demand_type_reason": [str]
    }
    ```
  + `HackerNewsTable.score` 按顺序传入 item_id:int、score:int
  + `HackerNewsAuxTable.story_summary` 按顺序传入 item_id:int、summary:str
  + `HackerNewsAuxTable.hwm` 不应使用该接口插入数据 (由 init 建表时写入唯一一行, 之后只用 update_hwm 更新)
## output
None

---

# async def fetch(self, table:HackerNewsTable, min_id:int, max_id:int) -> list
## 描述
通用拉取入口, 按 `table.name` 反射派发到对应的私有实现 `_fetch_from_{table.name}`; 返回结构随 table 不同而不同

## input
- table: HackerNewsTable 枚举, 要拉取的表
- min_id: int, 区间下界 (不含)
- max_id: int, 区间上界 (含)
  + hacker_news 表按 `data->>'id'` 过滤, 且为闭区间 `BETWEEN min_id AND max_id`
  + 其余表按自增主键 id 过滤, `id > min_id And id <= max_id`

## output (按 table 分述)

### table = HackerNewsTable.hacker_news
区间内所有 type = 'comment' 的评论, 按所属 story 分组。story_id 通过递归回溯 parent 链得到, 回溯不到 story 时为 None (孤儿评论)。
```python
[
    {
        "story_id": int | None,
        "comments": [
            {"item_id": int, "text": str},   # 评论 id 与正文
            ...
        ]
    },
    ...
]
```

### table = HackerNewsTable.filter
区间内已过滤评论, 按所属 story 分组, 并补齐 story 标题与 story 摘要。
```python
[
    {
        "title": str,      # story 标题, 取自 hacker_news 表
        "text": str,       # story 摘要, 取自 story_summary 表
        "comments": [
            {"item_id": int, "text": str},   # 评论 id 与正文
            ...
        ]
    },
    ...
]
```

### table = HackerNewsTable.demand_object
区间内需求对象的 data 字典列表。
```python
[
    dict,   # 格式同 insert 中 demand_object 的 dict
    ...
]
```

### table = HackerNewsTable.score
区间内 score >= 70 的记录, 用其 item_id 反查 demand_object 后返回需求对象列表。
```python
[
    dict,   # 格式同 insert 中 demand_object 的 dict
    ...
]
```

---

# async def fetch_sequence_id(self, table:HackerNewsTable) -> int
## 描述
- 查询指定表 id 列所绑定序列的 `last_value`, 即当前已分配的最大自增 id
- 用于流水线推进高水位线; 仅适用于带 BIGSERIAL id 的表 (filter / demand_object / score), hacker_news 表无 id 列
## input
- table: HackerNewsTable 枚举, 目标表
## output
int, 该表 id 序列的当前 last_value

---

# async def save_story_text(self, item_id:int, story_text:str) -> None
## 描述
- 将 story 正文以 item_id 为文件名写入 raw_data_path 目录
- story_text 为空字符串时跳过写入
- 写入失败只记录日志, 不抛异常
## input
- item_id: int, 作为文件名
- story_text: str, 要写入的正文
## output
None

---

# async def get_story_text(self, item_id:int) -> str
## 描述
读取 `raw_data_path/{item_id}` 文件内容; 文件不存在时返回空字符串, 读取失败记录日志并抛出异常
## input
- item_id: int, 文件名
## output
str, 文件内容; 文件不存在返回 ""

---

# async def check_demand_repeat(self, embedding:list) -> bool
## 描述
- 用向量余弦距离在 demand_object 表中查重, 距离阈值 < 0.1
- 命中 demand_object.embedding 上的 hnsw 索引
## input
- embedding: list[float], 1024 维向量
## output
bool, True 表示已存在相似需求 (应跳过写入), False 表示可写入

---

# async def save_solution(self, item_id:int, solution:str) -> None
## 描述
将产品方案文本以 item_id 为文件名写入 solution_path 目录; 失败时记录日志并抛出异常
## input
- item_id: int, 作为文件名
- solution: str, 产品方案文本
## output
None
