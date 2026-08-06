"""LLM API 客户端。

封装 OpenAI 兼容的 ``/v1/chat/completions`` 接口（MiniMax、OpenAI、
DeepSeek、Moonshot 等都遵循此格式），返回 JSON 解析结果。

设计要点：
- 自动注入 ``response_format={"type": "json_object"}`` 强制返回合法 JSON
- 解析失败时按 ``max_retries`` 自动重试
- 网络层错误、5xx 也走重试；4xx 立即抛 ``LLMAPIError``
- 支持 ``timeout`` 和 ``temperature`` 参数
"""

from __future__ import annotations

import json
import re
from typing import Any

import requests


class LLMAPIError(Exception):
    """LLM API 调用失败时抛出。"""


class LLMClient:
    """OpenAI 兼容 Chat Completions 客户端。

    Parameters
    ----------
    api_url:
        API 根地址，例如 ``https://api.minimaxi.com/v1``。
    api_key:
        Bearer Token。
    model:
        模型名，例如 ``MiniMax-Text-01``、``gpt-4o-mini`` 等。
    timeout:
        单次请求超时（秒），默认 60。
    max_retries:
        失败重试次数，默认 2（共 3 次尝试）。
    """

    def __init__(
        self,
        api_url: str,
        api_key: str,
        model: str,
        timeout: float = 60.0,
        max_retries: int = 2,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self._session = requests.Session()

    # ------------------------------------------------------------------
    # 公共 API
    # ------------------------------------------------------------------
    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """发起一次对话，返回解析后的 JSON dict。

        Raises
        ------
        LLMAPIError
            网络错误、状态码非 2xx、或返回内容无法解析为 JSON。
        """
        url = f"{self.api_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        # 仅在子类显式启用时附带 response_format（部分 API 如 MiniMax 不支持）
        if getattr(self, "use_response_format", False):
            payload["response_format"] = {"type": "json_object"}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._session.post(
                    url, headers=headers, json=payload, timeout=self.timeout
                )
                if response.status_code >= 400:
                    self._raise_for_status(response, attempt)
                content = self._extract_content(response.json())
                return self._parse_json(content)
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_exc = exc
            except LLMAPIError as exc:
                last_exc = exc
                if not getattr(exc, "_retryable", False):
                    raise
            if attempt < self.max_retries:
                continue
        raise LLMAPIError(
            f"LLM 调用在 {self.max_retries + 1} 次尝试后仍失败: {last_exc}"
        ) from last_exc

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "LLMClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        # 协议参数；当前实现不消费异常信息
        _ctx_exit_info = (exc_type, exc, tb)
        del _ctx_exit_info
        self.close()

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_content(data: dict[str, Any]) -> str:
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMAPIError(
                f"LLM 响应缺少 message.content: {data!r}"
            ) from exc

    @staticmethod
    def _parse_json(content: str) -> dict[str, Any]:
        """容错解析 JSON：

        1. 剥离 markdown 代码块围栏（```json ... ```）
        2. 直接 ``json.loads``
        3. 失败则尝试修复（转义字符串值里未转义的引号）
        4. 再失败则提取首个 ``{...}`` 块（非贪婪 → 贪婪）
        """
        cleaned = LLMClient._strip_code_fence(content)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        repaired = LLMClient._repair_json(cleaned)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass

        # 非贪婪：第一个 {...} 块
        match = re.search(r"\{.*?\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        # 贪婪：第一个 { 到最后一个 }
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError as exc:
                raise LLMAPIError(
                    f"LLM 返回内容无法解析为 JSON:\n{content[:500]}"
                ) from exc

        raise LLMAPIError(
            f"LLM 返回内容中找不到 JSON 对象:\n{content[:500]}"
        )

    @staticmethod
    def _strip_code_fence(content: str) -> str:
        """剥离 markdown 代码块围栏 `` ```json `` / `` ``` ``。"""
        text = content.strip()
        if text.startswith("```"):
            # 去掉首行围栏（如 ````json` 或 `````）
            newline = text.find("\n")
            if newline > 0:
                text = text[newline + 1 :]
        if text.endswith("```"):
            text = text[: -3]
        return text.strip()

    @staticmethod
    def _repair_json(content: str) -> str:
        """修复 LLM 常见的 JSON 错误：字符串值里出现未转义的 ``"``。

        状态机：维护 ``in_string``，遇到 ``"`` 时向前看——
        - 若下一个非空白字符是 ``,`` / ``}`` / ``]`` / ``:`` → 视为闭合引号
        - 否则 → 视为字符串内部的引号，转义为 ``\\"``

        同时：移除对象/数组末尾的尾随逗号。
        """
        out: list[str] = []
        in_string = False
        i = 0
        n = len(content)
        while i < n:
            c = content[i]
            if in_string:
                if c == "\\" and i + 1 < n:
                    out.append(c)
                    out.append(content[i + 1])
                    i += 2
                    continue
                if c == '"':
                    # 看后面：跳过空白后是不是 , } ] :
                    j = i + 1
                    while j < n and content[j] in " \t\n\r":
                        j += 1
                    if j >= n or content[j] in ",}]]:":
                        # 闭合
                        in_string = False
                        out.append(c)
                    else:
                        # 内部引号 → 转义
                        out.append('\\"')
                    i += 1
                    continue
                out.append(c)
                i += 1
                continue
            # 不在字符串中
            if c == '"':
                in_string = True
                out.append(c)
                i += 1
                continue
            out.append(c)
            i += 1

        text = "".join(out)
        # 去掉尾随逗号：, 空格? } 或 , 空格? ]
        text = re.sub(r",(\s*[}\]])", r"\1", text)
        return text

    @staticmethod
    def _raise_for_status(response: requests.Response, attempt: int) -> None:
        status = response.status_code
        body = response.text[:300]
        # 5xx 可重试
        if 500 <= status < 600 and attempt < 2:
            err = LLMAPIError(f"LLM 5xx (status={status}): {body}")
            err._retryable = True  # type: ignore[attr-defined]
            raise err
        # 4xx 直接抛
        raise LLMAPIError(f"LLM 4xx (status={status}): {body}")