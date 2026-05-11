import json
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
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(8000)  # Vue.js SPA hydration
        if "captcha" in page.url.lower() or "showcaptcha" in page.url.lower():
            logger.error("[uzum] CAPTCHA detected — site is blocking this session")
            return
        await page.wait_for_selector("a[href*='/ru/product/']", timeout=15000)

    async def get_product_urls(self, page: Page) -> List[str]:
        if "captcha" in page.url.lower() or "showcaptcha" in page.url.lower():
            return []
        links = await page.query_selector_all("a[href*='/ru/product/']")
        urls = []
        for link in links:
            href = await link.get_attribute("href")
            if href:
                # strip skuId param but keep base product URL
                base = href.split("?")[0]
                full = base if base.startswith("http") else f"https://uzum.uz{base}"
                urls.append(full)
        return list(dict.fromkeys(urls))

    async def scrape_product_page(self, page: Page, url: str) -> Optional[Product]:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(5000)  # wait for product data to render
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
        await page.wait_for_timeout(5000)
        return True

    @staticmethod
    def parse_product_html(html: str, url: str) -> dict:
        soup = BeautifulSoup(html, "lxml")

        def text(selector: str) -> Optional[str]:
            el = soup.select_one(selector)
            return el.get_text(strip=True) if el else None

        def og_meta(prop: str) -> Optional[str]:
            el = soup.find("meta", attrs={"property": prop}) or \
                 soup.find("meta", attrs={"name": prop})
            return el.get("content") if el else None

        # OG/product meta tags are SSR — always available without JS wait
        price = og_meta("product:price:amount")
        original_price = og_meta("product:original_price:amount")
        brand = og_meta("product:brand")
        image_url = og_meta("og:image")
        availability = og_meta("product:availability")
        in_stock = (availability or "").strip().lower() == "in stock" if availability is not None else None

        crumbs = soup.select("nav.breadcrumb ol li a")
        category = crumbs[-1].get_text(strip=True) if crumbs else None

        # Description from JSON-LD structured data
        description = None
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.get_text())
                graph = data.get("@graph", [data])
                for item in graph:
                    if item.get("@type") == "Product" and item.get("description"):
                        raw_desc = item["description"]
                        # Strip HTML tags if any
                        desc_soup = BeautifulSoup(raw_desc, "lxml")
                        description = desc_soup.get_text(separator=" ", strip=True)[:500] or None
                        break
            except Exception:
                pass

        return {
            "name": text("h1"),
            "price": price,
            "original_price": original_price,
            "rating": text("div.rating span.value"),
            "review_count": text("a.reviews-count span"),
            "category": category,
            "brand": brand,
            "description": description,
            "image_url": image_url,
            "in_stock": in_stock,
        }
