import asyncio
import logging
import json
from typing import cast
from jsonschema import validate, ValidationError
from openai import AsyncOpenAI, APIError, APIConnectionError, RateLimitError
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam
from typing import get_args, get_origin
from common.text_clean import TextClean

logger = logging.getLogger(__name__)
class AiClient:
    def __init__(self, api_url: str, api_key: str, model:str) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=api_url.rstrip("/"), timeout=120)
        self._model = model
        self._tools:list[ChatCompletionToolParam] = [
            {
                "type": "function",
                "function": {
                    "name": "validate_json",
                    "description": "检查输出是否是标准json格式, 并符合输出的字段要求",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "input": {
                                "type": "string",
                                "description": "需要校验的JSON字符串"
                            }
                        },
                        "required": ["input"],
                        "additionalProperties": False
                    }
                }
            }
        ]
    async def destroy(self):
        await self._client.close()
    # 仅支持向量模型操作
    async def embedding(self, text:str) -> list:
        while True:
            try:
                resp = await self._client.embeddings.create(
                        model=self._model,
                        input=text,
                        dimensions = 1024)
                return resp.data[0].embedding
            except RateLimitError:
                await asyncio.sleep(3)
            except (APIError, APIConnectionError) as e:
                logger.error("embedding call failed: %s", e)
                raise
            except Exception as e:
                raise
    async def simple_chat(self, prompt: str, content:str, temperature:float = 0.2) -> str:
        while True:
            try:
                resp = await self._client.responses.create(
                    model=self._model,
                    input=[{"role": "user", "content": content}],
                    instructions = prompt,
                    temperature = temperature
                )
            except RateLimitError as e:
                await asyncio.sleep(3)
            except Exception as e:
                logger.error(f"simple_chat failed: {e}")
                raise
            else:
                return resp.output_text
    # 如果后续该项目有效果，换用更先进的大模型，使用response Api
    async def chat(self, prompt: str, content:str, validator, temperature:float = 0.2) -> dict:
        messages: list[ChatCompletionMessageParam] = [
            {
                "role": "user", 
                "content": content
            }, {
                "role": "system",
                "content":prompt
            }
        ]
        for _ in range(5):
            while True:
                try:
                    response = await self._client.chat.completions.create(
                        model = self._model,
                        messages = messages,
                        tools = self._tools,
                        tool_choice="auto"
                    )
                    break
                except (RateLimitError, APIConnectionError):
                    logger.warning(f"chat rate limit")
                    await asyncio.sleep(60)
                    continue
                except Exception as e:
                    logger.error(f"chat failed: {e}")
                    raise
                
            message = response.choices[0].message
            if not message.tool_calls:
                messages.append({
                    "role":"user",
                    "content": "输出之前必须调用validate_json Tool校验生成的JSON"
                })
                continue
            
            messages.append(cast(ChatCompletionMessageParam, message.model_dump()))
            for tool_call in message.tool_calls:
                if tool_call.type != "function":
                    continue
                tool_name = tool_call.function.name
                raw_arguments = tool_call.function.arguments
                if tool_name == "validate_json":
                    try:
                        result = self._validate_json(json.loads(raw_arguments)['input'], validator)
                        if result["success"]:
                            return result["data"]
                        else:
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": json.dumps(result, ensure_ascii=False)
                            })
                            break
                    except Exception as e:
                        raise
        logger.warning("dont use tool error") 
        raise Exception("validate json failed")
                    
    def _validate_json(self, raw_input, validator) -> dict:
        try:
            data = json.loads(raw_input)
            validator.validate(data)
            return {
                        "success": True,
                        "data":data
                   }
        except json.JSONDecodeError as e:
            return {
                        "success": False,
                        "error": "validate_json的参数格式错误",
                        "details": str(e),
                        "instruction": "请重新生成合法 JSON 的 Tool 参数"
                   }
        except ValidationError as e:
            return {
                        "success": False,
                        "error": "JSON Schema 校验失败",
                        "details": e.message,
                        "instruction": "请根据错误信息重新生成符合 Schema 的 JSON"
                   }