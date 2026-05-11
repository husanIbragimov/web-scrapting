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
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(5000)  # wait for React hydration
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
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(5000)  # wait for React hydration
        try:
            # Wildberries uses CSS modules — no h1; wait for product name container
            await page.wait_for_selector("[class*='productLineName']", timeout=15000)
        except Exception:
            logger.warning(f"[wildberries] Timeout at {url}")
            return None
        html = await page.content()
        raw = self.parse_product_html(html, url)
        if not raw.get("price"):
            raw["price"] = await self._extract_price_js(page)
        return Product(url=url, source_site="wildberries", currency="RUB", **raw)

    @staticmethod
    async def _extract_price_js(page: Page) -> Optional[str]:
        return await page.evaluate("""
            () => {
                const candidates = [
                    '[class*="productLinePriceContainer"]',
                    '[class*="mo-typography_variant_action-accent"]',
                    'ins.price-block__final-price',
                    '[class*="price-block__final"]',
                    '[class*="price__lower-price"]',
                    '[class*="price-block"] ins',
                    '[data-widget="webPrice"] ins',
                ];
                for (const sel of candidates) {
                    const el = document.querySelector(sel);
                    if (el) {
                        const t = (el.innerText || el.textContent || '').trim();
                        if (t) return t;
                    }
                }
                return null;
            }
        """)

    async def go_to_next_page(self, page: Page) -> bool:
        btn = await page.query_selector("button.pagination-next:not([disabled])")
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

        img = soup.select_one("img.photo-zoom__preview")
        image_url = img.get("data-src") or img.get("src") if img else None

        crumbs = soup.select("ul.breadcrumbs__list li a")
        category = crumbs[-1].get_text(strip=True) if crumbs else None

        brand_el = soup.select_one("a.product-page__header-brand")
        brand = brand_el.get_text(strip=True) if brand_el else None

        # Original price: scoped inside the price wrap to avoid matching other description elements
        price_wrap = soup.select_one('[class*="productLinePriceWrap"]') or soup.select_one('[class*="productLinePrice"]')
        original_price = None
        if price_wrap:
            orig_el = price_wrap.select_one('[class*="mo-typography_variant_description"]')
            if orig_el:
                original_price = orig_el.get_text(strip=True)

        # In-stock: look for "В корзину" (Add to basket) button using the new mo-button structure
        buttons = soup.find_all("button", attrs={"class": lambda c: c and "mo-button" in c})
        in_stock = any("корзину" in b.get_text(strip=True).lower() for b in buttons)

        return {
            "name": text('[class*="productLineName"]'),
            "price": text('[class*="productLinePriceContainer"]'),
            "original_price": original_price,
            "rating": text("span.product-review__rating"),
            "review_count": text("span.product-review__count-review"),
            "category": category,
            "brand": brand,
            "description": text("p.product-details__text"),
            "image_url": image_url,
            "in_stock": in_stock,
        }
