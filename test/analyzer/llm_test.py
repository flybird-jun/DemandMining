"""analyzer.llm 的冒烟测试, 直接调用 public 接口 print 结果。

需要 LLM_API_KEY, 缺则用 fake mode 验证 prompt 装载。
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from analyzer.ai_client import AiClient


async def main() -> None:
    api_key = os.environ.get("LLM_API_KEY", "")
    api_url = os.environ.get("LLM_API_URL", "https://api.openai.com/v1")

    # 1) 验证 prompt 装载
    fake = AiClient.__new__(AiClient)
    AiClient.__init__(fake, "http://unused", "unused")
    print("=== prompt 装载 ===")
    print("article_prompt 前 80 字符:", fake._article_prompt[:80].replace("\n", " "))
    print("article_agg_prompt 前 80 字符:", fake._article_agg_prompt[:80].replace("\n", " "))
    print("占位符 article:", "{article}" in fake._article_prompt)
    print("占位符 articles:", "{articles}" in fake._article_agg_prompt)

    if not api_key:
        print()
        print("=== LLM_API_KEY 未设置, 跳过真实调用 ===")
        print("设置方式: export LLM_API_KEY=sk-... LLM_API_URL=https://api.openai.com/v1")
        return

    llm = AiClient(api_url, api_key)

    sample = (
        "我们是一家小团队, 用 SQLite + Flask 做了内部工具, 但每次 schema 变更都要"
        "手动改 ORM 模型, 担心大厂员工会因为这种\"无聊工作\"而离职。"
    )
    print()
    print("=== article_parse ===")
    try:
        out = await llm.article_parse(sample)
        print(out)
    except Exception as e:
        print("article_parse 失败:", repr(e))

    print()
    print("=== article_aggregation_parse (3 篇) ===")
    try:
        out = await llm.article_aggregation_parse([sample, sample, sample])
        print(out)
    except Exception as e:
        print("article_aggregation_parse 失败:", repr(e))


if __name__ == "__main__":
    asyncio.run(main())
