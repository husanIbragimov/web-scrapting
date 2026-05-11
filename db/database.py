import aiosqlite
import logging
from typing import List, Dict, Any, Optional
from models.product import Product

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS products (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    url              TEXT NOT NULL UNIQUE,
    source_site      TEXT NOT NULL,
    scraped_at       TEXT NOT NULL,
    name             TEXT,
    price            REAL,
    currency         TEXT,
    original_price   REAL,
    discount_percent REAL,
    rating           REAL,
    review_count     INTEGER,
    category         TEXT,
    brand            TEXT,
    description      TEXT,
    image_url        TEXT,
    in_stock         INTEGER,
    seller           TEXT
);
CREATE INDEX IF NOT EXISTS idx_source ON products(source_site);
CREATE INDEX IF NOT EXISTS idx_price  ON products(price);
"""

UPSERT_SQL = """
INSERT OR IGNORE INTO products
    (url, source_site, scraped_at, name, price, currency, original_price,
     discount_percent, rating, review_count, category, brand, description,
     image_url, in_stock, seller)
VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
"""

class AsyncDatabase:
    def __init__(self, db_path: str = "products.db"):
        self.db_path = db_path
        self.conn: Optional[aiosqlite.Connection] = None

    async def init(self) -> None:
        self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.executescript(CREATE_TABLE_SQL)
        await self.conn.commit()
        logger.info(f"Database ready: {self.db_path}")

    async def upsert_product(self, product: Product) -> bool:
        """Returns True if newly inserted, False if URL already existed."""
        in_stock_int = None
        if product.in_stock is not None:
            in_stock_int = 1 if product.in_stock else 0
        async with self.conn.execute(UPSERT_SQL, (
            product.url, product.source_site, product.scraped_at.isoformat(),
            product.name, product.price, product.currency, product.original_price,
            product.discount_percent, product.rating, product.review_count,
            product.category, product.brand, product.description,
            product.image_url, in_stock_int, product.seller,
        )) as cursor:
            await self.conn.commit()
            return cursor.rowcount > 0

    async def get_all(self) -> List[Dict[str, Any]]:
        async with self.conn.execute("SELECT * FROM products ORDER BY scraped_at DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()
