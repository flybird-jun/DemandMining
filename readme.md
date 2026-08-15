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
评论抽取，先抽取原文，后面需要在这一步进行先抽象，但是保留原文

如果多个评论表达的诉求是同一个，只是从不同的角度考虑，将它们罗列到一起进行总结，不要进行抽象总结，按评论的原话进行总结


迭代一、单批次story（200篇）分析, 最后聚合分析

采集 ---> 清洗 ---> 总结正文 ---> 抽取有效评论 ---> 评论聚类 ---> 需求挖掘 ---> 产品分析 ---> 产品分类
                             |               |                         ↑  
                             |               |_________________________|
                             |                                         ↑
                             |_________________________________________|

迭代二、增加存储管理、历史需求搜索

迭代三、增加需求热度分析

迭代四、增加产品关注模块

    def _run_async(self, urls):
        """Asynchronous event loop execution

        Args:
            urls (list): URLs to fetch

        Returns:
            results (obj): All URL requests' responses

        """
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(self._async_loop(urls))
        return results