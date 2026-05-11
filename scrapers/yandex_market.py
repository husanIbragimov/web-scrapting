import logging
from typing import List, Optional

from playwright.async_api import Page
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from models.product import Product

logger = logging.getLogger(__name__)

SEARCH_URL = "https://market.yandex.ru/search?text={query}"

class YandexMarketScraper(BaseScraper):
    DELAY = 2.0

    async def goto_search(self, page: Page, query: str) -> None:
        url = SEARCH_URL.format(query=query.replace(" ", "+"))
        await page.goto(url, wait_until="networkidle", timeout=45000)
        if "captcha" in page.url.lower():
            logger.error("[yandex] CAPTCHA detected — site is blocking this session")
            return
        await page.wait_for_selector(
            "article[data-zone-name='snippet']", timeout=20000
        )

    async def get_product_urls(self, page: Page) -> List[str]:
        if "captcha" in page.url.lower():
            return []
        links = await page.query_selector_all(
            "article[data-zone-name='snippet'] a[data-auto='snippet-link']"
        )
        urls = []
        for link in links:
            href = await link.get_attribute("href")
            if href:
                full = href if href.startswith("http") else f"https://market.yandex.ru{href}"
                urls.append(full.split("?")[0])
        return list(dict.fromkeys(urls))

    async def scrape_product_page(self, page: Page, url: str) -> Optional[Product]:
        await page.goto(url, wait_until="networkidle", timeout=45000)
        if "captcha" in page.url.lower():
            logger.warning(f"[yandex] CAPTCHA at {url}")
            return None
        try:
            await page.wait_for_selector("h1[data-auto='productCardTitle']", timeout=12000)
        except Exception:
            logger.warning(f"[yandex] Timeout at {url}")
            return None
        html = await page.content()
        raw = self.parse_product_html(html, url)
        return Product(url=url, source_site="yandex", currency="RUB", **raw)

    async def go_to_next_page(self, page: Page) -> bool:
        btn = await page.query_selector("a[aria-label='Следующая страница']")
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

        img = soup.select_one("div[data-auto='product-photo'] img")
        image_url = img.get("src") if img else None

        crumbs = soup.select("ol[aria-label='breadcrumbs'] li a")
        category = crumbs[-1].get_text(strip=True) if crumbs else None

        brand_el = soup.select_one("a[data-auto='brand-link']")
        brand = brand_el.get_text(strip=True) if brand_el else None

        return {
            "name": text("h1[data-auto='productCardTitle']"),
            "price": text("span[data-auto='price-value']"),
            "original_price": text("span[data-auto='oldprice-value']"),
            "rating": text("span[data-auto='rating-value']"),
            "review_count": text("span[data-auto='reviews-count']"),
            "category": category,
            "brand": brand,
            "description": text("div[data-auto='product-full-specs-list']"),
            "image_url": image_url,
            "in_stock": None,
        }
