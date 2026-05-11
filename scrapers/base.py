import asyncio
import logging
from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Optional

from playwright.async_api import Page, BrowserContext
from bs4 import BeautifulSoup

from models.product import Product
from utils.retry import async_retry
from utils.stealth import apply_stealth

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    DELAY: float = 1.5

    def __init__(
        self,
        context: BrowserContext,
        query: str,
        max_products: int,
        db,
    ) -> None:
        self.context = context
        self.query = query
        self.max_products = max_products
        self.db = db
        self.collected: int = 0
        self.site_name: str = self.__class__.__name__.replace("Scraper", "").lower()

    async def run(self) -> List[Product]:
        page = await self.context.new_page()
        await apply_stealth(page)
        products: List[Product] = []
        try:
            logger.info(f"[{self.site_name}] Starting search: '{self.query}'")
            await self.goto_search(page, self.query)
            async for product in self._paginate(page):
                await self.db.upsert_product(product)
                products.append(product)
        except Exception as exc:
            logger.error(f"[{self.site_name}] Fatal error: {exc}")
        finally:
            await page.close()
        logger.info(f"[{self.site_name}] Done. Collected {len(products)} products.")
        return products

    async def _paginate(self, page: Page) -> AsyncGenerator[Product, None]:
        while self.collected < self.max_products:
            urls = await self.get_product_urls(page)
            logger.info(f"[{self.site_name}] Found {len(urls)} product URLs on page")
            for url in urls:
                if self.collected >= self.max_products:
                    return
                product = await async_retry(
                    self.scrape_product_page,
                    args=(page, url),
                    retries=3,
                    backoff_base=2.0,
                )
                if product:
                    self.collected += 1
                    logger.info(f"[{self.site_name}] [{self.collected}/{self.max_products}] {product.name}")
                    yield product
                await asyncio.sleep(self.DELAY)
            if not await self.go_to_next_page(page):
                break

    def _soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    async def _get_html(self, page: Page) -> str:
        return await page.content()

    @abstractmethod
    async def goto_search(self, page: Page, query: str) -> None:
        ...

    @abstractmethod
    async def get_product_urls(self, page: Page) -> List[str]:
        ...

    @abstractmethod
    async def scrape_product_page(self, page: Page, url: str) -> Optional[Product]:
        ...

    @abstractmethod
    async def go_to_next_page(self, page: Page) -> bool:
        ...
