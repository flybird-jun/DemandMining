# async def extract_valuable_comments(self, story_info:dict) -> list
## 描述
- 抽取有效评论
## input:story_info
{
    "title":"",
    "text": "",
    "comments": [
        {
            "item_id": xxx,
            "text":""
            "parent":""
        }, {
            ...
        }
        ...
    ]
}
## output:
[item_id_1, item_id_2, ...]

# async def extract_demand_object(self, story_info:dict) -> list[dict]:
## 描述
将有效评论中有需求属性的评论转化成结构化数据
## input:story_info
同extract_comments函数的输入input
## output
[
    {
        "item_id": int,
        "demand_type": [""],
        "persona": [""],
        "problem": "",
        "context": "",
        "job_to_be_done": "",
        "current_solution": "",
        "severity": int,
        "confidence": "",
        "evidence": ""
    }
]

# async def output_solution(self, demand_info:dict) -> str
## 描述
分析评论的结构化数据, 输出解决方案
## input:demand_info
同extract_demand_object的output
## output
产品文档字符串

# async def embedding(self, text:str) -> list
## 描述
文本向量化
## input:text
需要进行向量化的文本字符串
## output:list[float]
输出1024维的向量列表

# async def summary_text(self, text:str) -> str
## 描述
长文本进行总结
## input:text
需要总结的长文本
## output:str
小于200字的总结字符串