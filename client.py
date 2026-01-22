from playwright.sync_api import Playwright, TimeoutError as PWTimeoutError
from config import Settings
import os
from datetime import datetime

class ProfiClient:
    def __init__(self, p: Playwright, s: Settings):
        self.p = p
        self.s = s
        self.browser = None
        self.page = None

    def __enter__(self):
        self.browser = self.p.chromium.launch(headless=self.s.headless)
        context = self.browser.new_context(storage_state=self.s.state_path)
        self.page = context.new_page()
        self.page.set_default_navigation_timeout(self.s.selector_timeout_ms)
        self.page.set_default_timeout(self.s.selector_timeout_ms)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.browser:
            try:
                self.browser.close()
            except Exception:
                pass

    def open_board(self):
        assert self.page is not None
        self.page.goto(self.s.page_url, wait_until="domcontentloaded")

    def soft_refresh(self):
        """
        Мягко обновляем страницу. Не ждём networkidle, иначе можно зависнуть.
        """
        assert self.page is not None
        self.page.reload(wait_until="domcontentloaded")

    def wait_cards(self):
        assert self.page is not None
        try:
            self.page.wait_for_selector(self.s.card_selector, timeout=self.s.selector_timeout_ms)
        except PWTimeoutError as e:
            # === DEBUG DUMP ===
            os.makedirs("logs/debug", exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")

            try:
                self.page.screenshot(path=f"logs/debug/no_cards_{ts}.png", full_page=True)
            except Exception:
                pass

            try:
                html = self.page.content()
                with open(f"logs/debug/no_cards_{ts}.html", "w", encoding="utf-8") as f:
                    f.write(html)
            except Exception:
                pass

            try:
                url = self.page.url
                title = self.page.title()
            except Exception:
                url, title = "<unknown>", "<unknown>"

            raise RuntimeError(
                f"Карточки не появились за {self.s.selector_timeout_ms}мс. "
                f"URL={url} TITLE={title}. "
                f"Сохранил logs/debug/no_cards_{ts}.png и .html"
            ) from e

    def cards_locator(self):
        assert self.page is not None
        return self.page.locator(self.s.card_selector)
