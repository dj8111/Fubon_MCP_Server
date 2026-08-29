import html
import re


class TextSanitizer:
    """公開文本清洗與 Prompt Injection 防護過濾器"""

    FORBIDDEN_PATTERNS = [
        r"ignore\s+previous\s+instructions",
        r"system\s*:\s*override",
        r"<script.*?>.*?</script>",
        r"javascript:",
        r"\{\{.*?\}\}",
        r"\$\{.*?\}",
    ]

    @classmethod
    def sanitize(cls, text: str) -> str:
        if not text:
            return ""
        # 1. HTML Unescape
        clean = html.unescape(text)

        # 2. 移除 HTML 標籤
        clean = re.sub(r"<[^>]+>", "", clean)

        # 3. 移除常見注入特徵
        for pattern in cls.FORBIDDEN_PATTERNS:
            clean = re.sub(pattern, "[FILTERED]", clean, flags=re.IGNORECASE)

        # 4. 正規化空白字元
        clean = re.sub(r"\s+", " ", clean).strip()

        return clean
