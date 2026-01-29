import re
from typing import Dict, Any


BOT_RE = re.compile(
    r'(?i)(?:^|[^0-9a-zа-яё])(?:[a-zа-яё]{1,20}-)?бот(?:[a-zа-яё]{0,10})?(?:[^0-9a-zа-яё]|$)'
)

def order_matches_filter(order: dict) -> bool:
    text = f"{order.get('title','')} {order.get('description','')}"
    text = text.replace("—", "-").replace("–", "-")  # чтобы разные тире не ломали дефисы
    return bool(BOT_RE.search(text))