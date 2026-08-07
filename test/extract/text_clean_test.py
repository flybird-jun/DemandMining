"""冒烟测试: 调用 TextClean.extract_article 并打印结果。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from collector.extract.text_clean import TextClean


def main() -> None:
    samples = {
        "article": (
            "<html><body>"
            "<nav>nav noise</nav>"
            "<article><p>Hello world</p><p>Second paragraph</p></article>"
            "<aside>aside noise</aside>"
            "</body></html>"
        ),
        "main": (
            "<html><body><main>"
            "Just a <script>var a=1</script> test."
            "</main></body></html>"
        ),
        "body_fallback": (
            "<html><body>just body content here</body></html>"
        ),
    }
    for name, html in samples.items():
        print(f"=== TextClean.extract_article ({name}) ===")
        out = TextClean.extract_article(html)
        print(repr(out))


if __name__ == "__main__":
    main()
