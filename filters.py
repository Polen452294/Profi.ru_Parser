import re
from typing import Dict, Any


EXCEPTION_RE = re.compile(
    r"(?iu)\b(телеграм|telegram|tg)[\s-]*бот\w*\b"
)
MAIN_RE = re.compile(
    r"(?iu)\b[\w-]{0,4}бот\w*\b"
)

def order_matches_filter(data: Dict[str, Any]) -> bool:
    title = data.get("title", "")
    desc = data.get("description", "")
    text = f"{title} {desc}".strip()

    if EXCEPTION_RE.search(text):
        return True

    return bool(MAIN_RE.search(text))