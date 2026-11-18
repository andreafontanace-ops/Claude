"""Scaricamento delle pagine con un browser vero (Playwright), a ritmo umano.

Scelte deliberate:
- browser visibile di default e profilo persistente (cookie e preferenze restano tra un'esecuzione e l'altra);
- nessuna tecnica per nascondere l'automazione e nessuna rotazione di IP: se Amazon chiede un
  captcha, il crawler si ferma e aspetta che lo risolva tu nella finestra del browser;
- pausa casuale tra le pagine e tetto al numero di pagine per esecuzione.
"""

from __future__ import annotations

import logging
import random
import time
from pathlib import Path
from urllib.parse import quote_plus

from .config import Config
from .parser import RESULT_SELECTOR, detect_block

log = logging.getLogger(__name__)


class BlockedError(RuntimeError):
    pass


class BrowserFetcher:
    def __init__(self, cfg: Config, profile_dir: Path, headless: bool | None = None, interactive: bool = True):
        self.cfg = cfg
        self.profile_dir = Path(profile_dir)
        self.headless = cfg.crawl.headless if headless is None else headless
        self.interactive = interactive and not self.headless
        self._pw = None
        self._ctx = None
        self._page = None
        self._last_fetch = 0.0
        self.pages_fetched = 0

    # -- ciclo di vita
    def __enter__(self) -> "BrowserFetcher":
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover - dipende dall'installazione
            raise SystemExit(
                "Playwright non è installato. Esegui:\n  pip install -e '.[browser]'\n  playwright install chromium"
            ) from exc
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._pw = sync_playwright().start()
        kwargs = dict(
            user_data_dir=str(self.profile_dir),
            headless=self.headless,
            locale="it-IT",
            viewport={"width": 1366, "height": 900},
        )
        if self.cfg.crawl.browser_channel and self.cfg.crawl.browser_channel != "chromium":
            kwargs["channel"] = self.cfg.crawl.browser_channel
        self._ctx = self._pw.chromium.launch_persistent_context(**kwargs)
        self._page = self._ctx.pages[0] if self._ctx.pages else self._ctx.new_page()
        return self

    def __exit__(self, *exc) -> None:
        if self._ctx:
            self._ctx.close()
        if self._pw:
            self._pw.stop()

    # -- utilità
    def _pause(self) -> None:
        lo, hi = self.cfg.crawl.delay_seconds
        wait = random.uniform(lo, hi) - (time.monotonic() - self._last_fetch)
        if self._last_fetch and wait > 0:
            time.sleep(wait)

    def _dismiss_cookie_banner(self) -> None:
        for selector in ("#sp-cc-rejectall-link", "#sp-cc-accept"):
            try:
                button = self._page.query_selector(selector)
                if button and button.is_visible():
                    button.click()
                    return
            except Exception:  # il banner non è essenziale
                return

    def _wait_for_human(self, reason: str) -> str:
        if not self.interactive:
            raise BlockedError(f"Amazon ha mostrato una verifica ({reason}). Riprova più tardi o con headless = false.")
        input(
            f"\n>>> Amazon ha mostrato una verifica ({reason}).\n"
            ">>> Risolvila nella finestra del browser, aspetta che compaiano i risultati, poi premi Invio qui… "
        )
        return self._page.content()

    def _get(self, url: str, wait_selector: str | None) -> str:
        if self.pages_fetched >= self.cfg.crawl.max_pages_total:
            raise BlockedError(f"Raggiunto il tetto di {self.cfg.crawl.max_pages_total} pagine (crawl.max_pages_total)")
        self._pause()
        log.info("GET %s", url)
        self._page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        self._last_fetch = time.monotonic()
        self.pages_fetched += 1
        self._dismiss_cookie_banner()
        if wait_selector:
            try:
                # la pagina di verifica di Amazon si risolve da sola in un browser normale: aspettiamo i risultati
                self._page.wait_for_selector(wait_selector, timeout=20_000)
            except Exception:
                pass
        html = self._page.content()
        block = detect_block(html)
        if block:
            html = self._wait_for_human(block)
            if detect_block(html):
                raise BlockedError(f"Pagina ancora bloccata ({block}): {url}")
        return html

    # -- pagine
    def search_url(self, keyword: str, page: int) -> str:
        url = f"https://{self.cfg.domain}/s?k={quote_plus(keyword)}"
        return url + (f"&page={page}" if page > 1 else "")

    def fetch_search(self, keyword: str, page: int) -> str:
        return self._get(self.search_url(keyword, page), RESULT_SELECTOR)

    def fetch_product(self, asin: str) -> str:
        return self._get(f"https://{self.cfg.domain}/dp/{asin}", "#bylineInfo, #productTitle")
