from common.text_clean import TextClean
class HackerNewsClean:
    @staticmethod
    def clean(item:dict) -> bool:
        # 无效数据返回false
        if 'dead' in item and item['dead']:
            return False
        if item["type"] == "story":
            HackerNewsClean._story_clean(item)
        elif item["type"] == "comment":
            HackerNewsClean._comment_clean(item)
        else:
            return False
        return True
    
    @staticmethod
    def _story_clean(story:dict) -> None:
        story["text"] = TextClean.clean_html(story["text"])
    @staticmethod
    def _comment_clean(comment:dict) -> None:
        comment["text"] = TextClean.clean_passage(comment["text"])
     
    
    