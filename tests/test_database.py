import pytest
from db.database import AsyncDatabase
from models.product import Product

@pytest.mark.asyncio
async def test_insert_and_retrieve_product():
    db = AsyncDatabase(":memory:")
    await db.init()
    p = Product(url="https://amazon.com/dp/B001", source_site="amazon", name="Test Laptop", price=999.99)
    inserted = await db.upsert_product(p)
    assert inserted is True
    all_products = await db.get_all()
    assert len(all_products) == 1
    assert all_products[0]["name"] == "Test Laptop"
    assert all_products[0]["price"] == 999.99
    await db.close()

@pytest.mark.asyncio
async def test_duplicate_url_not_inserted():
    db = AsyncDatabase(":memory:")
    await db.init()
    p = Product(url="https://amazon.com/dp/B001", source_site="amazon", name="Laptop")
    await db.upsert_product(p)
    inserted_again = await db.upsert_product(p)
    assert inserted_again is False
    all_products = await db.get_all()
    assert len(all_products) == 1
    await db.close()

@pytest.mark.asyncio
async def test_get_all_returns_dicts():
    db = AsyncDatabase(":memory:")
    await db.init()
    p = Product(url="https://ebay.com/itm/123", source_site="ebay", price=49.99, currency="USD")
    await db.upsert_product(p)
    rows = await db.get_all()
    assert isinstance(rows[0], dict)
    assert rows[0]["source_site"] == "ebay"
    await db.close()
