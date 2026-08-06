import json
import logging
from pathlib import Path
from jsonschema import Draft202012Validator

from common.ai_client import AiClient
from common.config import settings

logger = logging.getLogger(__name__)
class HackerNewsAiClient:
    def __init__(self):
        self._slm_client = AiClient(settings.SLM_API_URL, settings.SLM_API_KEY, settings.SLM_MODEL)
        self._llm_client = AiClient(settings.LLM_API_URL, settings.LLM_API_KEY, settings.LLM_MODEL)
        self._embedding_client = AiClient(settings.EMBEDDING_API_URL, settings.EMBEDDING_API_KEY, settings.EMBEDDING_MODEL)

        prompt_dir = Path(__file__).resolve().parents[0] / "prompt"
        prompt = (prompt_dir/ "hacker_news_filter_semantic.md").read_text(encoding="utf-8")
        self._semantic_prompt = prompt.replace("{DEBUG}", settings.DEBUG)
        schema = {
            "type": "object",
            "properties":{
                "output": {
                    "type": "array",
                    "items": {
                        "type":"object",
                        "properties": {
                            "item_id": {
                                "type":"integer"
                            },
                            "text": {
                                "type":"string"
                            }
                        },
                        "required":["item_id", "text"]
                    }
                },
            },
            "required":["output"]
        }
        if settings.DEBUG == "ON":
            schema["properties"]["reason"] = {
                "type": "array",
                "items": {
                    "type":"string"
                }
            }
        self._semantic_validator = Draft202012Validator(schema)
        
        prompt = (prompt_dir/ "hacker_news_demand_object.md").read_text(encoding="utf-8")
        self._demand_object_prompt = prompt.replace("{DEBUG}", settings.DEBUG)
        one_item_schema = {
            "type": "object",
            "properties": {
                "item_id": {
                    "type":"integer"
                },
                "demand_type": {
                    "type": "string",
                    "enum": ["pain_point", "missing_product", "feature_request", "replacement"]
                },
                "persona": {
                    "type": "string"
                },
                "problem": {
                    "type": "string"
                },
                "context": {
                    "type": "string"
                },
                "job_to_be_done": {
                    "type": "string"
                },
                "current_solution": {
                    "type": "string"
                },
                "severity": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100
                }
            },
            "required": ["item_id", "demand_type", "persona", "problem", "context", "job_to_be_done", "current_solution",
                    "severity"],
            "additionalProperties": False
        }
        schema = {
            "type":"object",
            "properties":{
                "output": {
                    "type": "array",
                    "items": one_item_schema
                }
            },
            "required":["output"]
        }
        if settings.DEBUG == "ON":
            schema["properties"]["reason"] = {
                "type": "array",
                "items": {
                    "type":"string"
                }
            }
        self._demand_object_validator = Draft202012Validator(schema)

        prompt = (prompt_dir/ "hacker_news_product_score.md").read_text(encoding="utf-8")
        self._product_score_prompt = prompt.replace("{DEBUG}", settings.DEBUG)
        one_item_schema = {
            "type": "object",
            "properties": {
                "score": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100
                },
                "funds": {
                    "type": "integer"
                },
                "person_month": {
                    "type": "integer"
                }
            },
            "required":["score", "funds", "person_month"],
            "additionalProperties": False
        }
        schema = {
            "type": "object",
            "properties": {
                "output": one_item_schema
            },
            "required":["output"]
        }
        if settings.DEBUG == "ON":
            schema["properties"]["sub_score"] = {
                "type": "array",
                "items": {
                    "type":"integer"
                }
            }
            schema["properties"]["reason"] = {
                "type": "array",
                "items": {
                    "type":"string"
                }
            }
        self._product_score_validator = Draft202012Validator(schema)

        self._product_solution_prompt = (prompt_dir/ "hacker_news_product_solution.md").read_text(encoding="utf-8")

        self._summary_text_prompt = (prompt_dir/ "hacker_news_summary_text.md").read_text(encoding="utf-8")


    async def destroy(self):
        await self._slm_client.destroy()
        await self._llm_client.destroy()
        await self._embedding_client.destroy()

    # step1.layer2 抽取有效评论
    async def extract_valuable_comments(self, story_info:dict) -> list:
        try:
            result = await self._slm_client.chat(self._semantic_prompt, json.dumps(story_info), self._semantic_validator, 0.2)
            if not isinstance(result["output"], list):
                logger.warning(f"extract_valuable_comments failed {result}")
            return result["output"]
        except Exception as e:
            logger.exception(f"extract_valuable_comments failed {type(e).__name__}: {e}")
            raise

    # 评论结构化抽取
    async def extract_demand_object(self, comments:list) -> dict:
        try:    
            result =  await self._llm_client.chat(self._demand_object_prompt, json.dumps(comments), self._demand_object_validator, 0.3)
            assert isinstance(result, dict)
            return result["output"]
        except Exception as e:
            logger.exception(f"extract_demand_object failed {type(e).__name__}")
            raise

    async def product_score(self, demand_object:dict) -> dict:
        try:
            result =  await self._llm_client.chat(self._product_score_prompt, json.dumps(demand_object), self._product_score_validator, 0.3)
            assert isinstance(result, dict)
            return result['output']
        except Exception as e:
            logger.exception(f"product_score failed")
            raise

    async def output_solution(self, demand_info:dict) -> str:
        try:    
            response =  await self._llm_client.simple_chat(self._product_solution_prompt, json.dumps(demand_info), 0.3)
            return response
        except Exception as e:
            logger.exception(f"output_solution failed")
            raise

    async def embedding(self, text:str) -> list:
        return await self._embedding_client.embedding(text)

    # 总结正文
    async def summary_text(self, text:str) -> str:
        if not text:
            logger.warning("main text is empty")
            return ""
        return await self._llm_client.simple_chat(self._summary_text_prompt, text)

    def _compose_story_info_helper(self, story_info:dict) -> str:
        content = f"title:{story_info['title']}\ntext:{story_info['text']}\n"
        for comment in story_info["comments"]:
            content += f"{comment['item_id']}:{comment['text']}\n"
        return content

