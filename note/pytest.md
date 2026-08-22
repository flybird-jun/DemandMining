# pytest执行流程
```
pytest启动
    |
    |
    +-- pytest_configure
    |
    +-- pytest_collection
    |       |
    |       +-- 找测试文件
    |       +-- 找test函数
    |
    |
    +-- 每个test:
            |
            +-- pytest_runtest_setup
            |
            +-- fixture setup
            |
            +-- test执行
            |
            +-- fixture teardown
            |
            +-- pytest_runtest_teardown
```
# 各功能函数详解
- pytest_configure:pytest启动后，配置初始化
```
def pytest_configure(config):
    shutil.copy("config.json", "run/config.json")
```
- pytest_runtest_setup:适合：清理环境,初始化测试数据,删除缓存
```
def pytest_runtest_setup(item):
    from storage import clean
    clean()
```
- pytest_runtest_teardown: 用例执行结束后调用
```
def pytest_runtest_teardown(item):
    cleanup()
```
- @pytest.fixture / @pytest_asyncio.fixture
```
@pytest.fixture(scope="module")
def db():
    xxx # setup
    yield xxx
    xxx # teardown
```
scope参数如下:
| scope    | 生命周期     |
| -------- | -------- |
| function | 每个测试     |
| class    | 每个class  |
| module   | 每个文件     |
| package  | 包        |
| session  | 整个pytest |
params参数:参数化fixture。
```
@pytest.fixture(
    params = ["mysql", "sqlite", "postgres"]
)
def database(request): # 参数名固定为request
    return request.param
```
autouse 参数:True时, 测试函数会执行这个函数，为False时，必须显示声明才会执行，不是全局无限制，它受 fixture scope 和位置影响

name 参数: 修改传给用例的参数名字

loop_scope 参数: 
| `loop_scope` | 含义                              | event loop 生命周期        |
| ------------ | ------------------------------- | ---------------------- |
| `"function"` | 每个测试函数一个 event loop             | 一个 test 创建一个，结束销毁      |
| `"class"`    | 每个测试类一个 event loop              | 一个 class 内所有 test 共用   |
| `"module"`   | 每个测试文件一个 event loop             | 一个 `.py` 文件内所有 test 共用 |
| `"package"`  | 每个 Python package 一个 event loop | 一个 package 目录共用        |
| `"session"`  | 整个 pytest 运行一个 event loop       | 全部测试共用                 |

- @pytest.mark.parametrize 参数化测试

```
@pytest.mark.parametrize(
    "x,y",
    [(1,2), (3,4)]
)
def test_add(x,y):
    pass
```

# 用例执行
pytest -v 全量跑
pytest tests/test_collector.py 跑单个文件
pytest tests/test_collector.py::TestHackerNewsCollector 跑单个测试套
pytest tests/test_collector.py::TestHackerNewsCollector::test_collect 跑单个用例