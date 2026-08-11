"""HTML / 文本清洗: 把原始 HTML 转换成主要正文文本。

对外暴露 TextClean.extract_article, 是纯函数 (无状态), 适合在协程外反复调用。
"""
from __future__ import annotations

import re
from typing import ClassVar

from bs4 import BeautifulSoup


class TextClean:
    """静态文本清洗工具集。"""

    NOISE_TAGS: ClassVar[tuple[str, ...]] = (
        "script",
        "style",
        "noscript",
        "nav",
        "footer",
        "header",
        "aside",
    )

    @staticmethod
    def extract_article(html: str) -> str:
        """从 HTML 提取主文本, 优先取 <article>/<main>, 否则 body / 全文。"""
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(TextClean.NOISE_TAGS):
            tag.decompose()

        main = soup.find("article") or soup.find("main")
        if main:
            return TextClean._normalize(main.get_text(separator="\n", strip=True))

        body = soup.find("body")
        if body:
            return TextClean._normalize(body.get_text(separator="\n", strip=True))

        return TextClean._normalize(soup.get_text(separator="\n", strip=True))

    @staticmethod
    def _normalize(text: str) -> str:
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()
# text
#         .replace("\u00a0", " ")
#         .replace("\u200b", "")
#         .strip()