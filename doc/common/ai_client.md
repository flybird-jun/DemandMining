# def __init__(self, api_url:str, api_key:str, model:str) -> None
## 描述
构造一个 AiClient 实例, 内部封装 AsyncOpenAI 客户端, 并预置一个用于校验 JSON 输出的 validate_json 工具函数
## input
- api_url: str, OpenAI 兼容 API 的 base url, 构造时自动去除末尾的 '/'
- api_key: str, 调用 API 使用的密钥
- model: str, 当前客户端默认使用的模型名称(同时用于 chat / responses / embeddings 接口)
## output
None

# async def destroy(self) -> None
## 描述
关闭底层 AsyncOpenAI 客户端, 释放连接资源, 必须在 AiClient 不再使用时调用
## input
无
## output
None

# async def embedding(self, text:str) -> list[float]
## 描述
仅用于向量模型, 调用 embeddings 接口把一段文本转为 1024 维向量
- 遇到 RateLimitError 时自动 sleep 3 秒后重试
- 遇到 APIError / APIConnectionError 时记录日志并向上抛出
- 其他异常直接抛出
## input
- text: str, 需要向量化的输入文本
## output
- list[float], 长度为 1024 的浮点数向量, 即 resp.data[0].embedding

# async def simple_chat(self, prompt:str, content:str, temperature:float = 0.2) -> str
## 描述
调用 OpenAI Responses 接口, 用 prompt 作为 system 指令, content 作为 user 输入, 返回模型直接产出的文本
- 遇到 RateLimitError 时自动 sleep 3 秒后重试
- 其他异常记录日志后向上抛出
## input
- prompt: str, 作为 system / instructions 注入的系统提示词
- content: str, 作为 user 消息内容
- temperature: float, 采样温度, 默认 0.2
## output
- str, 模型直接返回的文本内容, 即 resp.output_text

# async def chat(self, prompt:str, content:str, validator, temperature:float = 0.2) -> dict
## 描述
调用 Chat Completions 接口, 并通过工具调用(validate_json)强制模型输出符合 JSON Schema 的结果, 最终返回通过 validator 校验的 dict
- 最多重试 5 次; 每次调用遇到 RateLimitError 会 sleep 3 秒后重试该次请求
- 模型生成的 JSON 失败(JSON 解析错误或 Schema 校验失败)时, 把错误信息作为 tool 消息回传模型继续生成, 直到成功或超过 5 次
- 5 次仍未通过校验则抛出 "validate json failed" 异常
## input
- prompt: str, 作为 system 消息注入, 用于约束模型输出结构
- content: str, 作为 user 消息内容
- validator: jsonschema 校验器实例, 通常为 jsonschema.Draft202012Validator(schema), 需对外提供 validate(data) 方法
- temperature: float, 采样温度, 默认 0.2 (注意: 当前实现未将该参数传给 chat.completions.create)
## output
- dict, 通过 validator.validate 校验后的 JSON 数据, 即 validate_json 工具成功时 result["data"]; 具体字段含义由调用方传入的 validator schema 决定

# def _validate_json(self, raw_input, validator) -> dict   (内部方法, 不建议外部直接调用)
## 描述
对模型通过 tool call 传入的字符串进行 JSON 解析与 Schema 校验, 返回结构化结果供 chat() 决定是否终止重试
## input
- raw_input: str, 模型在 validate_json 工具的 arguments 中传入的 JSON 字符串
- validator: jsonschema.Draft202012Validator 实例, 用于校验解析后的 dict
## output
- 成功时: {"success": True, "data": <dict>}
- JSON 解析失败: {"success": False, "error": "validate_json的参数格式错误", "details": <异常信息>, "instruction": "请重新生成合法 JSON 的 Tool 参数"}
- Schema 校验失败: {"success": False, "error": "JSON Schema 校验失败", "details": <校验错误信息>, "instruction": "请根据错误信息重新生成符合 Schema 的 JSON"}