import re

BOT_RE = re.compile(
    r"(?iu)"   
    r"(?<![а-яёa-z0-9])" 
    r"("
    r"(?:чат|chat|tg|telegram|телеграм)[\s\-]*бот(?:а|ы|ов|ом|у|е)?"
    r"|"
    r"бот(?:а|ы|ов|ом|у|е)?"
    r")"
    r"(?![а-яёa-z0-9])"
)

FALSE_POSITIVE_RE = re.compile(r"(?iu)\bработ(?:а|у|ы|е|ой)\b")

def order_matches_filter(text: str) -> bool:
    t = (text or "").lower()
    if BOT_RE.search(t):
        if FALSE_POSITIVE_RE.search(t) and not re.search(r"(?iu)\b(чат|телеграм|tg|telegram)[\s\-]*бот\b", t) and not re.search(r"(?iu)\bбот\b", t):
            return False
        return True

    return False
