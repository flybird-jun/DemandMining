先完成大模型分析，后面再优化 -> 每天可以稳定的分析一波
|
数据存储
|
引入小模型
|
reddit/youtube
{
    "title":xxx, # 帖子标题
    "text":xxx, # 帖子内容
    "comment":[] # 帖子所有评论
}

评论的评论

需求趋势

当前只支持普通帖子, 后面需要开发所有

Demandmining/
    |
    |__ src/
         |
         |____ analyzer/
         |
         |____ api/
    |
    |__ test/
         |
         |___ analyzer/
         |
         |___ api/
