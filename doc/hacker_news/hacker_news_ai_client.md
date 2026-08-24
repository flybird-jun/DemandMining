# async def extract_comments(self, story_info:dict) -> list
## 描述
- 抽取有效评论
## input:story_info
{
    "text": "",
    "comment": [
        {
            "item_id": xxx,
            "text":""
        }, {
            ...
        }
        ...
    ]
}
## output:
[item_id_1, item_id_2, ...]

# async def classify_comment(self, story_info:dict) -> list:
# 描述
- 对评论进行分类
# input:story_info
{
    "text": "",
    "comment": [
        {
            "item_id": xxx,
            "text":""
        }, {
            ...
        }
        ...
    ]
}
# output
[
    {
        "demand_type": ["pain_point", "workaround"],
        "confidence":0.91,
        "item_id":xxx
    },
    {
        
    }
]