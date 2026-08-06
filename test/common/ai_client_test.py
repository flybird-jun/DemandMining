import pytest
import pytest_asyncio
from common.config import settings
from common.ai_client import AiClient
@pytest.mark.asyncio(loop_scope="class")
class TestDbms:
    @pytest_asyncio.fixture(scope="function", loop_scope="class", autouse = True, name = "client")
    async def setup(self):
        client = AiClient(settings.LLM_API_URL, settings.LLM_API_KEY, settings.LLM_MODEL)
        yield client
        await client.destroy()
    async def test_simple_chat(self, client):
        prompt = "你是一个专业的中文助手。简洁回答用户的问题。"
        content = "Python 中 list 和 tuple 有什么区别？"
        result = await client.simple_chat(prompt, content, None)
        print(result)
    async def test_chat(self, client):
        prompt = """
                从用户输入中提取姓名和年龄。

                你必须：
                1. 生成 JSON
                2. 调用 validate_json Tool 校验生成的 JSON
                3. 如果校验失败，根据错误信息重新生成
                4. 只有校验成功后，才返回最终 JSON

                JSON 格式：
                {
                    "name": "string",
                    "age": 0
                }
                """
        content = "张三今年25岁。"
        schema = {
            "name": str,
            "age": int,
        }
        result = await client.chat(prompt, content, schema)
        assert isinstance(result['name'], str)
        assert isinstance(result['age'], int)
    async def test_embedding(self):
        client = AiClient(settings.EMBEDDING_API_URL, settings.EMBEDDING_API_KEY, settings.EMBEDDING_MODEL)
        vector = await client.embedding("张三今年25岁")
        assert isinstance(vector, list)
        assert len(vector) == 1024
        await client.destroy()