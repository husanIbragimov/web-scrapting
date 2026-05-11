import logging
from typing import List, Optional

from playwright.async_api import Page
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from models.product import Product

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.wildberries.ru/catalog/0/search.aspx?search={query}"

class WildberriesScraper(BaseScraper):
    DELAY = 1.5

    async def goto_search(self, page: Page, query: str) -> None:
        url = SEARCH_URL.format(query=query.replace(" ", "+"))
        await page.goto(url, wait_until="networkidle", timeout=45000)
        await page.wait_for_selector("article.product-card", timeout=20000)

    async def get_product_urls(self, page: Page) -> List[str]:
        links = await page.query_selector_all("article.product-card a.product-card__link")
        urls = []
        for link in links:
            href = await link.get_attribute("href")
            if href:
                full = href if href.startswith("http") else f"https://www.wildberries.ru{href}"
                urls.append(full.split("?")[0])
        return list(dict.fromkeys(urls))

    async def scrape_product_page(self, page: Page, url: str) -> Optional[Product]:
        await page.goto(url, wait_until="networkidle", timeout=45000)
        try:
            await page.wait_for_selector("h1.product-page__title", timeout=12000)
        except Exception:
            logger.warning(f"[wildberries] Timeout at {url}")
            return None
        html = await page.content()
        raw = self.parse_product_html(html, url)
        return Product(url=url, source_site="wildberries", currency="RUB", **raw)

    async def go_to_next_page(self, page: Page) -> bool:
        btn = await page.query_selector("button.pagination-next:not([disabled])")
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

        img = soup.select_one("img.photo-zoom__preview")
        image_url = img.get("data-src") or img.get("src") if img else None

        crumbs = soup.select("ul.breadcrumbs__list li a")
        category = crumbs[-1].get_text(strip=True) if crumbs else None

        brand_el = soup.select_one("a.product-page__header-brand")
        brand = brand_el.get_text(strip=True) if brand_el else None

        order_btn = soup.select_one("button.order__button")
        in_stock = order_btn is not None

        return {
            "name": text("h1.product-page__title"),
            "price": text("ins.price-block__final-price"),
            "original_price": text("del.price-block__old-price"),
            "rating": text("span.product-review__rating"),
            "review_count": text("span.product-review__count-review"),
            "category": category,
            "brand": brand,
            "description": text("p.product-details__text"),
            "image_url": image_url,
            "in_stock": in_stock,
        }
