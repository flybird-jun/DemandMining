from __future__ import annotations
import trafilatura
import unicodedata
import re
from html import unescape
from bs4 import BeautifulSoup
from util import util
logger = util.logger
class TextClean:
    URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.I)
    SPACE_PATTERN = re.compile(r"[ \t]+")
    NEWLINE_PATTERN = re.compile(r"\n{3,}")
    @staticmethod
    def clean_passage(comment:str) -> str:
        soup = BeautifulSoup(
            comment,
            "html.parser",
        )
        # <p> 和 <br> 表示文本结构上的换行
        for tag in soup.find_all(["p", "br"]):
            tag.insert_before("\n")

        return TextClean._normalize_text(soup.get_text())
    
    @staticmethod
    def clean_html(html: str) -> str:
        # 抽取文章主体
        text = trafilatura.extract(
            html,
            include_comments = False,
            include_tables = True,
            output_format = "txt",
            favor_precision = True
        )
        if not text:
            logger.info(f"原文:{html}, 但是没抽取到文章主体")
            return ""
        
        return TextClean._normalize_text(text)
    @staticmethod
    def _normalize_text(text:str) -> str:
        text = unicodedata.normalize("NFKC",text)
        # html的转义字符，比如&lt 转换为正常的符号
        text = unescape(text)
        # 删除不可见字符
        text = TextClean._clean_invisible_chars(text)
        # 处理文本中的 URL。url本身没有意义，统一使用字母URL代替
        text = TextClean.URL_PATTERN.sub("[URL]",text)
        # 把连续空格、tab 统一。
        text = TextClean.SPACE_PATTERN.sub(" ", text)
        # 控制连续空行数量。
        text = TextClean.NEWLINE_PATTERN.sub("\n\n",text)
        
        return text.strip()
    @staticmethod
    def _clean_invisible_chars(text: str) -> str:
        result = []
        for ch in text:
            category = unicodedata.category(ch)
            if category == "Cc":
                if ch in "\n\t":
                    result.append(ch)
                continue
            # Unicode格式字符
            if category == "Cf":
                continue
            # 不换行空格
            if ch == "\u00a0":
                result.append(" ")
                continue
            result.append(ch)

        return "".join(result)