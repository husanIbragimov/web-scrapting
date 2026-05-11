import logging
from typing import List, Optional

from playwright.async_api import Page
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from models.product import Product

logger = logging.getLogger(__name__)

SEARCH_URL = "https://uzum.uz/ru/search?query={query}"

class UzumScraper(BaseScraper):
    DELAY = 1.5

    async def goto_search(self, page: Page, query: str) -> None:
        url = SEARCH_URL.format(query=query.replace(" ", "+"))
        await page.goto(url, wait_until="networkidle", timeout=45000)
        await page.wait_for_selector("a[data-cy='product-card'], a.catalog-grid-item", timeout=20000)

    async def get_product_urls(self, page: Page) -> List[str]:
        selectors = ["a[data-cy='product-card']", "a.catalog-grid-item"]
        links = []
        for sel in selectors:
            found = await page.query_selector_all(sel)
            links.extend(found)
            if links:
                break
        urls = []
        for link in links:
            href = await link.get_attribute("href")
            if href:
                full = href if href.startswith("http") else f"https://uzum.uz{href}"
                urls.append(full.split("?")[0])
        return list(dict.fromkeys(urls))

    async def scrape_product_page(self, page: Page, url: str) -> Optional[Product]:
        await page.goto(url, wait_until="networkidle", timeout=45000)
        try:
            await page.wait_for_selector("h1", timeout=12000)
        except Exception:
            logger.warning(f"[uzum] Timeout at {url}")
            return None
        html = await page.content()
        raw = self.parse_product_html(html, url)
        return Product(url=url, source_site="uzum", currency="UZS", **raw)

    async def go_to_next_page(self, page: Page) -> bool:
        btn = await page.query_selector("button[aria-label='Next page']:not([disabled])")
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

        img = soup.select_one("div.product-gallery img")
        image_url = img.get("src") if img else None

        crumbs = soup.select("nav.breadcrumb ol li a")
        category = crumbs[-1].get_text(strip=True) if crumbs else None

        add_btn = soup.select_one("button.add-to-cart:not([disabled])")
        in_stock = add_btn is not None

        return {
            "name": text("h1"),
            "price": text("span[data-cy='price-current'], div.product-price span.current"),
            "original_price": text("span[data-cy='price-old']"),
            "rating": text("div.rating span.value"),
            "review_count": text("a.reviews-count span"),
            "category": category,
            "brand": None,
            "description": text("div[data-cy='product-description'] p"),
            "image_url": image_url,
            "in_stock": in_stock,
        }
