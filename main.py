import json
import random
import time
from playwright.sync_api import sync_playwright

from config import Settings
from auth import ensure_auth_state
from client import ProfiClient
from parser import parse_order_snippet
from storage import load_seen_ids, save_seen_ids, append_jsonl


def sleep_human(base: int, jitter: int):
    time.sleep(base + random.uniform(0, jitter))


def main():
    s = Settings()

    with sync_playwright() as p:
        ensure_auth_state(p, s)
        seen_ids = load_seen_ids(s.seen_ids_path)

        with ProfiClient(p, s) as client:
            client.open_board()
            client.wait_cards()

            print("▶ Мониторинг запущен. Ctrl+C — остановить.")

            try:
                while True:
                    client.soft_refresh()
                    client.wait_cards()

                    cards = client.cards_locator()
                    new_orders = []

                    for i in range(cards.count()):
                        data = parse_order_snippet(cards.nth(i))
                        oid = data.get("order_id")
                        if not oid or oid in seen_ids:
                            continue
                        new_orders.append(data)
                        seen_ids.add(oid)

                    if new_orders:
                        append_jsonl(s.out_new_jsonl, new_orders)
                        save_seen_ids(s.seen_ids_path, seen_ids)
                        print(f"🆕 Новых заказов: {len(new_orders)}")
                        print(json.dumps(new_orders[:3], ensure_ascii=False, indent=2))

                    sleep_human(s.poll_base_sec, s.poll_jitter_sec)

            except KeyboardInterrupt:
                # ✅ корректное завершение по Ctrl+C
                print("\n⏹ Остановлено пользователем (Ctrl+C). Закрываю браузер...")
                save_seen_ids(s.seen_ids_path, seen_ids)
                return


if __name__ == "__main__":
    main()
