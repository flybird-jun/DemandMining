import pytest
import pytest_asyncio
import json
from pathlib import Path
import jsonschema
from hacker_news.hacker_news_ai_client import HackerNewsAiClient
@pytest.mark.asyncio(loop_scope="class")
class TestHackerNewsAiClient:
    @pytest_asyncio.fixture(scope="class", loop_scope="class", autouse = True, name = "client")
    async def setup(self):
        client = HackerNewsAiClient()
        yield client
        await client.destroy()

    @pytest.fixture(scope="class", name = "test_data")
    def test_data(self):
        file_path = Path(__file__).resolve().parent / "test_data.json"

        with open(file_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        return result["hacker_news_ai_client_test"]
    async def test_extract_valuable_comments(self, client, test_data):
        data_set = test_data['test_extract_valuable_comments']
        result = await client.extract_valuable_comments(data_set['data'])
        count = 0
        expect = data_set["expect"]
        for comment in result:
            for match in expect:
                if comment['item_id'] == match['item_id']:
                    count+=1
                    break
            # if comment['item_id'] == expect[i]['item_id']: # and comment['text'] == expect[i]['text']:
            #     count+=1
            # else:
                # print(f"fail {comment} expect = {expect[i]}")
        assert count / len(result) > 0.8

    async def test_extract_demand_object(self, client, test_data):
        data_set = test_data['test_extract_demand_object']
        result = await client.extract_demand_object(data_set['data'])

        expect = data_set["expect"]
        assert len(result) == len(expect)
        count = 0
        for i, demand_object in enumerate(result):
            
            if (demand_object["demand_type"] == expect[i]["demand_type"] 
                and demand_object["persona"] == expect[i]["persona"] 
                and (demand_object["severity"] - 1) // 20 == (expect[i]["severity"] - 1) // 20):
                count+=1
            else:
                print(f"{demand_object['item_id']} unsucc, {demand_object['demand_type'], {demand_object['persona']}, {demand_object['severity']}}")
        assert count / len(result) > 0.6
        
    async def test_product_score(self, client, test_data):
        data_set = test_data['test_product_score']
        count = 0
        for i, data in enumerate(data_set['data']):
            result = await client.product_score(data)
            if result["score"] > data_set["expect"][i] - 15 and result["score"] < data_set["expect"][i] + 15:
                count+=1
        assert count / len(data_set['data']) >= 0.8
    async def test_output_solution(self, client, test_data):
        file_path = Path(__file__).resolve().parent / "output"
        data_set = test_data['test_output_solution']
        for data in data_set:
            result = await client.output_solution(data)
            with open(file_path / f"{data['item_id']}", "w", encoding="utf-8") as f:
                f.write(result)
            break

    async def test_embedding(self, client):
        test_texts = [
            "今天天气很好，适合出去散步。",
            "今天阳光明媚，非常适合到户外走走。",
            "北京今天下着大雨，出门最好带一把伞。",
            "我喜欢吃苹果和香蕉。",
            "苹果是一种常见的水果。"]
        for text in test_texts:
            vec = await client.embedding(text)
            assert len(vec) == 1024
    async def test_summary_text(self, client, test_data):
        data_set = test_data['test_summary_text']
        for item in data_set:
            resp = await client.summary_text(item)
            assert len(resp) < 150