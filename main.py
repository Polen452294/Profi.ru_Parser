import random
import time
import logging

from playwright.sync_api import sync_playwright

from config import Settings
from auth import ensure_auth_state
from client import ProfiClient
from parser import parse_order_snippet
from storage import load_seen_ids, save_seen_ids, append_jsonl
from filters import order_matches_filter


logger = logging.getLogger("parser")

# 🔧 Включай на короткое время для отладки фильтра
DEBUG_FILTER = False


def sleep_human(base: int, jitter: int):
    time.sleep(base + random.uniform(0, jitter))


def _get_poll_params(s: Settings):
    base = getattr(s, "poll_base_sec", getattr(s, "poll_base", 45))
    jitter = getattr(s, "poll_jitter_sec", getattr(s, "poll_jitter", 25))
    return int(base), int(jitter)


def _start_client(p, s: Settings) -> ProfiClient:
    """
    Создаём новый клиент, стартуем его и открываем доску.
    """
    client = ProfiClient(p, s).start()
    client.open_board()

    logger.info(
        "Page after open_board: title=%r url=%s",
        client.page.title(),
        client.page.url
    )
    return client


def main():
    s = Settings()

    with sync_playwright() as p:
        ensure_auth_state(p, s)

        # 2) Загружаем seen_ids и параметры опроса
        seen_ids = load_seen_ids(s.seen_ids_path)
        poll_base, poll_jitter = _get_poll_params(s)

        logger.info("Starting parser monitoring...")
        logger.info(
            "Settings: page_url=%s, poll_base=%s, poll_jitter=%s",
            s.page_url, poll_base, poll_jitter
        )
        logger.info("Loaded seen_ids: %d", len(seen_ids))

        client: ProfiClient | None = None
        net_errors = 0

        try:
            client = _start_client(p, s)

            if not client.wait_cards():
                logger.warning("No cards on first load. Will keep trying...")

            while True:
                try:
                    client.soft_refresh()
                    net_errors = 0

                except Exception as e:
                    msg = str(e)

                    if "ERR_NAME_NOT_RESOLVED" in msg or "ERR_INTERNET_DISCONNECTED" in msg:
                        net_errors += 1
                        logger.warning("Network/DNS error #%d: %s", net_errors, e)

                        if net_errors >= 3:
                            logger.warning("Too many network errors подряд -> restarting client")

                            try:
                                client.close()
                            except Exception:
                                logger.exception("Failed to close client on restart")

                            client = _start_client(p, s)
                            net_errors = 0

                        time.sleep(20)
                        continue

                    logger.exception("Unexpected error in main loop (refresh). Sleeping and continuing.")
                    time.sleep(10)
                    continue

                ok = client.wait_cards()
                if not ok:
                    title = client.page.title()
                    url = client.page.url

                    if ("вход" in title.lower()) or ("login" in title.lower()):
                        logger.warning(
                            "Seems logged out (TITLE=%r, URL=%s). Re-authenticating...",
                            title, url
                        )
                        ensure_auth_state(p, s)
                        client.open_board()
                        sleep_human(5, 5)
                        continue

                    logger.warning(
                        "Cards not found within %sms. Re-opening board. URL=%s TITLE=%r",
                        s.selector_timeout_ms, url, title
                    )
                    client.open_board()
                    sleep_human(10, 10)
                    continue

                cards = client.cards_locator()
                new_orders = []

                for i in range(cards.count()):
                    data = parse_order_snippet(cards.nth(i))
                    oid = data.get("order_id")

                    if not oid:
                        continue
                    if oid in seen_ids:
                        continue

                    match = order_matches_filter(data)

                    if DEBUG_FILTER:
                        t = data.get("title", "")
                        d = data.get("description", "")
                        text = f"{t} {d}".lower()
                        logger.info(
                            "FILTER oid=%s match=%s | title=%r | desc_len=%d | text_has_бот=%s",
                            oid, match, t, len(d), ("бот" in text)
                        )

                    if not match:
                        continue

                    seen_ids.add(oid)
                    new_orders.append(data)

                if new_orders:
                    for order in new_orders:
                        append_jsonl(s.out_jsonl_path, order)

                    save_seen_ids(s.seen_ids_path, seen_ids)
                    logger.info(
                        "Saved %d new orders. seen_ids=%d",
                        len(new_orders), len(seen_ids)
                    )

                sleep_human(poll_base, poll_jitter)

        except KeyboardInterrupt:
            logger.info("Stopped by user.")

        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    logger.exception("Failed to close client in finally.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    main()
