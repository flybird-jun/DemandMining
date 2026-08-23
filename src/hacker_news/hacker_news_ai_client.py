from common.ai_client import AiClient
from util.util import *
class HackerNewsAiClient:
    def __init__(self):
        self._slm_client = AiClient(config['ai_api_url'], config['ai_api_key'])
        self._llm_client = AiClient(config['ai_api_url'], config['ai_api_key'])

        prompt_dir = Path(__file__).resolve().parents[1] / "prompt"
        self._semantic_prompt = (prompt_dir/ "semantic_value_analyzer_en.prompt").read_text(encoding="utf-8")
        self._summary_text_prompt = (prompt_dir/ "summary_text.prompt").read_text(encoding="utf-8")
    # 抽取有效评论
    async def extract_comments(self, article: str) -> str:
        if not article:
            logger.warning("article_parse called with empty article")
            return ""
        return await self._slm_client.chat(self._semantic_prompt, article, 0.3)
    # 总结正文
    async def summary_text(self, text:str) -> str:
        if not text or text == "":
            logger.warning("main text is empty")
        return await self._llm_client.chat(self._summary_text_prompt, text)
