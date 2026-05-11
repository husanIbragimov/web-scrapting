import logging
from typing import List, Optional

from playwright.async_api import Page
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from models.product import Product

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.temu.com/search_result.html?search_key={query}"

class TemuScraper(BaseScraper):
    DELAY = 2.5

    async def goto_search(self, page: Page, query: str) -> None:
        url = SEARCH_URL.format(query=query.replace(" ", "+"))
        await page.goto(url, wait_until="networkidle", timeout=45000)
        await page.wait_for_selector("a[data-type='productCard']", timeout=20000)

    async def get_product_urls(self, page: Page) -> List[str]:
        links = await page.query_selector_all("a[data-type='productCard']")
        urls = []
        for link in links:
            href = await link.get_attribute("href")
            if href:
                full = href if href.startswith("http") else f"https://www.temu.com{href}"
                urls.append(full.split("?")[0])
        return list(dict.fromkeys(urls))

    async def scrape_product_page(self, page: Page, url: str) -> Optional[Product]:
        await page.goto(url, wait_until="networkidle", timeout=45000)
        try:
            await page.wait_for_function(
                "() => !!document.querySelector('h1[class*=\"goodsName\"]') || "
                "!!document.querySelector('h1[class*=\"GoodsName\"]')",
                timeout=15000
            )
        except Exception:
            logger.warning(f"[temu] Timeout at {url}")
            return None
        html = await page.content()
        raw = self.parse_product_html(html, url)
        return Product(url=url, source_site="temu", currency="USD", **raw)

    async def go_to_next_page(self, page: Page) -> bool:
        btn = await page.query_selector("button[aria-label='Next']:not([disabled])")
        if not btn:
            return False
        await btn.click()
        await page.wait_for_load_state("networkidle")
        return True

    @staticmethod
    def parse_product_html(html: str, url: str) -> dict:
        soup = BeautifulSoup(html, "lxml")

        def text_partial(partial_class: str) -> Optional[str]:
            el = soup.find(attrs={"class": lambda c: c and partial_class in c})
            return el.get_text(strip=True) if el else None

        def text(selector: str) -> Optional[str]:
            el = soup.select_one(selector)
            return el.get_text(strip=True) if el else None

        img = soup.find("div", attrs={"class": lambda c: c and "swiper-slide-active" in c})
        img_tag = img.find("img") if img else None
        image_url = img_tag.get("src") if img_tag else None

        crumbs = soup.select("nav[aria-label='breadcrumb'] a")
        category = crumbs[-1].get_text(strip=True) if crumbs else None

        add_btn = soup.find("button", attrs={"class": lambda c: c and "addToCart" in c})
        in_stock = add_btn is not None and not add_btn.get("disabled")

        return {
            "name": text_partial("goodsName") or text_partial("GoodsName"),
            "price": text_partial("priceNum") or text_partial("PriceNum"),
            "original_price": text_partial("oriPrice") or text_partial("OriPrice"),
            "rating": text_partial("ratingText") or text_partial("rating-number"),
            "review_count": text_partial("reviewNum") or text_partial("review-count"),
            "category": category,
            "brand": text_partial("brandName"),
            "description": text_partial("description") or text("[data-testid='product-desc']"),
            "image_url": image_url,
            "in_stock": in_stock,
        }
