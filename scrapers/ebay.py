import logging
from typing import List, Optional

from playwright.async_api import Page
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from models.product import Product

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.ebay.com/sch/i.html?_nkw={query}"

class EbayScraper(BaseScraper):
    DELAY = 1.5

    async def goto_search(self, page: Page, query: str) -> None:
        url = SEARCH_URL.format(query=query.replace(" ", "+"))
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_selector("ul.srp-results li.s-item", timeout=15000)

    async def get_product_urls(self, page: Page) -> List[str]:
        links = await page.query_selector_all("ul.srp-results li.s-item a.s-item__link")
        urls = []
        for link in links:
            href = await link.get_attribute("href")
            if href and "ebay.com/itm/" in href:
                urls.append(href.split("?")[0])
        return list(dict.fromkeys(urls))

    async def scrape_product_page(self, page: Page, url: str) -> Optional[Product]:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        try:
            await page.wait_for_selector("h1.x-item-title__mainTitle", timeout=12000)
        except Exception:
            logger.warning(f"[ebay] Timeout at {url}")
            return None
        html = await page.content()
        raw = self.parse_product_html(html, url)
        return Product(url=url, source_site="ebay", currency="USD", **raw)

    async def go_to_next_page(self, page: Page) -> bool:
        btn = await page.query_selector("a.pagination__next:not([aria-disabled='true'])")
        if not btn:
            return False
        await btn.click()
        await page.wait_for_load_state("domcontentloaded")
        return True

    @staticmethod
    def parse_product_html(html: str, url: str) -> dict:
        soup = BeautifulSoup(html, "lxml")

        def text(selector: str) -> Optional[str]:
            el = soup.select_one(selector)
            return el.get_text(strip=True) if el else None

        iframe = soup.select_one("iframe#desc_ifr")
        desc_src = iframe.get("src") if iframe else None

        crumbs = soup.select("nav.breadcrumbs li a")
        category = crumbs[-1].get_text(strip=True) if crumbs else None

        img = soup.select_one("div.ux-image-carousel-item.active img")
        image_url = img.get("data-zoom-src") or img.get("src") if img else None

        avail = text("div.d-quantity__availability span")
        in_stock = avail is not None and "available" in avail.lower() if avail else None

        return {
            "name": text("h1.x-item-title__mainTitle span.ux-textspans--BOLD"),
            "price": text("div.x-price-primary span.ux-textspans"),
            "original_price": text("span.ux-textspans--STRIKETHROUGH"),
            "rating": text("div.x-star-rating span.ux-textspans"),
            "review_count": text("span.ux-summary-with-count a span"),
            "category": category,
            "brand": None,
            "description": f"[iframe: {desc_src}]" if desc_src else None,
            "image_url": image_url,
            "in_stock": in_stock,
        }
