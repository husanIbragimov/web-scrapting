import asyncio
import logging
from typing import List, Optional

from playwright.async_api import Page
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from models.product import Product

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.amazon.com/s?k={query}"


class AmazonScraper(BaseScraper):
    DELAY = 2.0

    async def goto_search(self, page: Page, query: str) -> None:
        url = SEARCH_URL.format(query=query.replace(" ", "+"))
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_selector(
            "div[data-component-type='s-search-result']", timeout=15000
        )

    async def get_product_urls(self, page: Page) -> List[str]:
        links = await page.query_selector_all(
            "div[data-component-type='s-search-result'] h2 a.a-link-normal"
        )
        urls = []
        for link in links:
            href = await link.get_attribute("href")
            if href and "/dp/" in href:
                full = (
                    href
                    if href.startswith("http")
                    else f"https://www.amazon.com{href}"
                )
                urls.append(full.split("?")[0])
        return list(dict.fromkeys(urls))

    async def scrape_product_page(self, page: Page, url: str) -> Optional[Product]:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        try:
            await page.wait_for_selector("#productTitle", timeout=12000)
        except Exception:
            logger.warning(f"[amazon] Timeout waiting for #productTitle at {url}")
            return None
        html = await page.content()
        raw = self.parse_product_html(html, url)
        return Product(
            url=url,
            source_site="amazon",
            currency="USD",
            **raw,
        )

    async def go_to_next_page(self, page: Page) -> bool:
        next_btn = await page.query_selector(
            "a.s-pagination-next:not(.s-pagination-disabled)"
        )
        if not next_btn:
            return False
        await next_btn.click()
        await page.wait_for_load_state("domcontentloaded")
        return True

    @staticmethod
    def parse_product_html(html: str, url: str) -> dict:
        soup = BeautifulSoup(html, "lxml")

        def text(selector: str) -> Optional[str]:
            el = soup.select_one(selector)
            return el.get_text(strip=True) if el else None

        # Price: first .a-offscreen is sale price, second is original
        price_els = soup.select("span.a-price span.a-offscreen")
        price = price_els[0].get_text(strip=True) if price_els else None
        original = price_els[1].get_text(strip=True) if len(price_els) > 1 else None

        # Description: join bullet points (skip hidden ones)
        bullets = soup.select(
            "#feature-bullets li:not(.aok-hidden) span.a-list-item"
        )
        description = (
            " | ".join(b.get_text(strip=True) for b in bullets) or None
        )

        # Category: last breadcrumb span
        crumbs = soup.select(
            "#wayfinding-breadcrumbs_feature_div ul li span"
        )
        category = crumbs[-1].get_text(strip=True) if crumbs else None

        # Image: prefer data-old-hires, fallback to src
        img = soup.select_one("#landingImage")
        image_url = None
        if img:
            image_url = img.get("data-old-hires") or img.get("src")

        # In stock: check availability text
        avail_el = soup.select_one("#availability span")
        in_stock = bool(
            avail_el and "in stock" in avail_el.get_text(strip=True).lower()
        )

        return {
            "name": text("#productTitle"),
            "price": price,
            "original_price": original,
            "rating": text("span[data-hook='rating-out-of-text']"),
            "review_count": text("span[data-hook='total-review-count']"),
            "category": category,
            "brand": text("#bylineInfo"),
            "description": description,
            "image_url": image_url,
            "in_stock": in_stock,
        }
