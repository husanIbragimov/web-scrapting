# E-Commerce Web Scraper

A visible-browser, async, multi-site product data collector built with Playwright + Python.

Opens a real Chromium window so you can watch the scraping happen in real time. Collects structured product data from 7 e-commerce sites simultaneously and exports to CSV or Excel.

---

## Supported Sites

| Site | Currency | Notes |
|------|----------|-------|
| Amazon | USD | Sets US ZIP (10001) before searching to get USD prices |
| eBay | USD | Navigates via homepage to avoid bot detection |
| AliExpress | USD | Requires playwright-stealth; heavy JS rendering |
| Uzum | UZS | Uzbekistan marketplace |
| Wildberries | RUB | Russian marketplace; prices in rubles |
| Yandex Market | RUB | Detects and logs CAPTCHA instead of crashing |
| Temu | USD | Uses partial CSS class matching for hashed selectors |

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### 2. Run the scraper

```bash
python main.py
```

You will be prompted for:

```
Search query: wireless headphones
Available sites: 1.amazon  2.ebay  3.aliexpress  4.uzum  5.wildberries  6.yandex  7.temu  0.all
Sites (e.g. 1,3 or 0 for all): 1,2
Max products per site (50): 20
Output format [csv/xlsx]: csv
```

A Chromium browser opens and navigates each chosen site in parallel. Progress is logged to the terminal. When complete, a results table is printed and the output file path is shown.

---

## Output

**File:** `output/products_YYYY-MM-DD_HH-MM.csv` (or `.xlsx`)

**Database:** `products.db` (SQLite) — every run appends to this file; duplicate URLs are silently ignored.

### Columns

| Column | Description |
|--------|-------------|
| `url` | Canonical product URL (deduplication key) |
| `source_site` | Site name (amazon, ebay, etc.) |
| `scraped_at` | UTC timestamp |
| `name` | Product title |
| `price` | Sale price (numeric) |
| `currency` | USD / RUB / UZS |
| `original_price` | Price before discount |
| `discount_percent` | Discount % if shown |
| `rating` | Star rating (0–5) |
| `review_count` | Number of reviews |
| `category` | Breadcrumb category |
| `brand` | Brand name |
| `description` | Short description or bullet points |
| `image_url` | Primary product image URL |
| `in_stock` | Boolean availability |
| `seller` | Seller/store name |

---

## Project Structure

```
WebScrapting/
├── main.py                  # Entry point — CLI prompts + async orchestrator
├── config.py                # Site registry (SITES dict) and global constants
├── requirements.txt
│
├── models/
│   └── product.py           # Pydantic v2 Product model (shared schema)
│
├── scrapers/
│   ├── base.py              # BaseScraper ABC — pagination, retry, stealth
│   ├── amazon.py
│   ├── ebay.py
│   ├── aliexpress.py
│   ├── uzum.py
│   ├── wildberries.py
│   ├── yandex_market.py
│   └── temu.py
│
├── db/
│   └── database.py          # AsyncDatabase — aiosqlite, INSERT OR IGNORE
│
├── exporters/
│   └── exporter.py          # CSV / Excel export via pandas
│
├── utils/
│   ├── retry.py             # async_retry() with exponential backoff
│   └── stealth.py           # playwright-stealth wrapper
│
├── tests/                   # pytest test suite (24 tests)
└── output/                  # Auto-created; holds exported files
```

---

## Architecture

**One browser, concurrent contexts.** A single Chromium instance is launched. Each chosen site gets an isolated `BrowserContext` so cookies never leak between sites. All sites scrape simultaneously via `asyncio.gather()`.

**Parsing flow.** Playwright navigates to each URL and calls `await page.content()` to get the fully-rendered HTML. BeautifulSoup parses the HTML in Python. For sites where the price is rendered after the DOM loads (Amazon), a JavaScript evaluation fallback extracts the live value directly from the rendered page.

**Deduplication.** SQLite uses a `UNIQUE` constraint on `url`. Re-running with the same query never creates duplicate rows (`INSERT OR IGNORE`).

**Retry.** Every product page request is wrapped in `async_retry()` with exponential backoff (up to 3 attempts: 1 s → 2 s → 4 s). A failed page returns `None` and the scraper moves on.

---

## Adding a New Site

1. Create `scrapers/mysite.py` extending `BaseScraper`:

```python
from scrapers.base import BaseScraper
from models.product import Product
from playwright.async_api import Page
from bs4 import BeautifulSoup
from typing import List, Optional

class MySiteScraper(BaseScraper):
    DELAY = 1.5

    async def goto_search(self, page: Page, query: str) -> None:
        await page.goto(f"https://mysite.com/search?q={query}", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_selector(".product-card", timeout=15000)

    async def get_product_urls(self, page: Page) -> List[str]:
        links = await page.query_selector_all(".product-card a")
        urls = []
        for link in links:
            href = await link.get_attribute("href")
            if href:
                urls.append(href if href.startswith("http") else f"https://mysite.com{href}")
        return list(dict.fromkeys(urls))

    async def scrape_product_page(self, page: Page, url: str) -> Optional[Product]:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        try:
            await page.wait_for_selector("h1.product-title", timeout=12000)
        except Exception:
            return None
        html = await page.content()
        raw = self.parse_product_html(html, url)
        return Product(url=url, source_site="mysite", currency="USD", **raw)

    async def go_to_next_page(self, page: Page) -> bool:
        btn = await page.query_selector("a.next-page")
        if not btn:
            return False
        await btn.click()
        await page.wait_for_load_state("domcontentloaded")
        return True

    @staticmethod
    def parse_product_html(html: str, url: str) -> dict:
        soup = BeautifulSoup(html, "lxml")
        def text(sel): el = soup.select_one(sel); return el.get_text(strip=True) if el else None
        return {
            "name": text("h1.product-title"),
            "price": text(".product-price"),
            "original_price": None,
            "rating": text(".star-rating"),
            "review_count": text(".review-count"),
            "category": None,
            "brand": None,
            "description": text(".product-description"),
            "image_url": None,
            "in_stock": None,
        }
```

2. Register it in `config.py`:

```python
from scrapers.mysite import MySiteScraper

SITES = {
    ...
    "mysite": MySiteScraper,
}
```

That's it — the site appears in the CLI menu on next run.

---

## Running Tests

```bash
pytest tests/ -v
```

24 tests cover: Product model field validation, database insert/deduplication, CSV/Excel export, retry logic, and Amazon HTML parser.

---

## Known Limitations

| Issue | Cause | Workaround |
|-------|-------|------------|
| Amazon shows no price | Non-US IP; geo-restricted products | US ZIP is set automatically; some products are still "See price in cart" |
| eBay "Access Denied" | Direct search URL blocked | Scraper navigates via homepage + search box |
| Yandex Market CAPTCHA | Non-Russian IP | Logged as error; other sites continue unaffected |
| Uzum CAPTCHA | Rapid repeated requests trigger rate-limit | Clears after ~2 min; single runs work fine; handled like Yandex |
| Wildberries CSS selectors | Uses hashed CSS Modules (`productLineName--xxxx`) | Scraper matches stable class prefixes via `[class*="…"]` |
| Temu selectors break | CSS Modules hashes change | Update `parse_product_html` partial class matches in `temu.py` |
| AliExpress slow | Heavy JS SPA, networkidle waits | Normal; `DELAY = 2.0` and 45 s timeout are intentional |

---

## Tech Stack

- **[Playwright](https://playwright.dev/python/)** — browser automation (Chromium, visible mode)
- **[playwright-stealth](https://github.com/AtuboDad/playwright_stealth)** — anti-bot fingerprint masking
- **[BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/)** + **lxml** — HTML parsing
- **[Pydantic v2](https://docs.pydantic.dev/)** — data validation and type coercion
- **[aiosqlite](https://aiosqlite.omnilib.dev/)** — async SQLite
- **[pandas](https://pandas.pydata.org/)** + **openpyxl** — CSV/Excel export
- **[Rich](https://rich.readthedocs.io/)** — terminal UI and progress display
