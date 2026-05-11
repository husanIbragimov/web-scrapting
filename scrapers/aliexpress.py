import logging
from typing import List, Optional

from playwright.async_api import Page
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from models.product import Product

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.aliexpress.com/wholesale?SearchText={query}"

class AliExpressScraper(BaseScraper):
    DELAY = 2.0

    async def goto_search(self, page: Page, query: str) -> None:
        url = SEARCH_URL.format(query=query.replace(" ", "+"))
        await page.goto(url, wait_until="networkidle", timeout=45000)
        await page.wait_for_selector("a.search-card-item", timeout=20000)

    async def get_product_urls(self, page: Page) -> List[str]:
        links = await page.query_selector_all("a.search-card-item")
        urls = []
        for link in links:
            href = await link.get_attribute("href")
            if href:
                full = href if href.startswith("http") else f"https:{href}"
                urls.append(full.split("?")[0])
        return list(dict.fromkeys(urls))

    async def scrape_product_page(self, page: Page, url: str) -> Optional[Product]:
        await page.goto(url, wait_until="networkidle", timeout=45000)
        try:
            await page.wait_for_selector("h1.product-title-text", timeout=15000)
        except Exception:
            logger.warning(f"[aliexpress] Timeout at {url}")
            return None
        html = await page.content()
        raw = self.parse_product_html(html, url)
        return Product(url=url, source_site="aliexpress", currency="USD", **raw)

    async def go_to_next_page(self, page: Page) -> bool:
        btn = await page.query_selector("button.comet-pagination-next:not([disabled])")
        if not btn:
            return False
        await btn.click()
        await page.wait_for_load_state("networkidle")
        return True

    @staticmethod
    def parse_product_html(html: str, url: str) -> dict:
        soup = BeautifulSoup(html, "lxml")

        def text(selector: str) -> Optional[str]:
            el = soup.select_one(selector)
            return el.get_text(strip=True) if el else None

        img = soup.select_one("div.slider-item img")
        image_url = img.get("src") if img else None

        crumbs = soup.select("div.breadcrumb a")
        category = crumbs[-1].get_text(strip=True) if crumbs else None

        return {
            "name": text("h1.product-title-text"),
            "price": text("div.product-price-current span.product-price-value"),
            "original_price": text("span.product-price-del"),
            "rating": text("strong.overview-rating-average"),
            "review_count": text("a.overview-rating-reviews"),
            "category": category,
            "brand": text("div.product-brand a"),
            "description": text("div.detailmodule_text"),
            "image_url": image_url,
            "in_stock": None,
        }
