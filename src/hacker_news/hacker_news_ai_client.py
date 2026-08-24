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
    async def extract_comments(self, story_info:dict) -> list:
        # 组装成字符串
        try:
            content = json.dumps(story_info, ensure_ascii = True)
            response =  await self._slm_client.chat(self._semantic_prompt, content, 0.3)
            return json.loads(response)
        except Exception as e:
            logger.exception("extract_comments failed, response = f{response}")
    # 评论分类
    async def classify_comment(self, story_info:dict) -> list:
        pass
    # 评论结构化抽取
    async def compose_struct_comment(self, story_info:dict) -> list:
        pass
    # 需求分析
    async def requirements_analysis(self) -> str:
        pass
    # 输出解决方案
    async def output_solution(self) -> str:
        pass
    # 总结正文
    async def summary_text(self, text:str) -> str:
        if not text or text == "":
            logger.warning("main text is empty")
        return await self._llm_client.chat(self._summary_text_prompt, text)
    
