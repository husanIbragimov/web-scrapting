import pytest
from models.product import Product

def test_price_parsed_from_string():
    p = Product(url="https://example.com/p/1", source_site="amazon", price="$1,299.99")
    assert p.price == 1299.99

def test_price_parsed_from_rubles():
    p = Product(url="https://example.com/p/2", source_site="wildberries", price="1 299 ₽")
    assert p.price == 1299.0

def test_review_count_parsed_from_string():
    p = Product(url="https://example.com/p/3", source_site="ebay", review_count="(4,567)")
    assert p.review_count == 4567

def test_rating_parsed_from_sentence():
    p = Product(url="https://example.com/p/4", source_site="amazon", rating="4.5 out of 5 stars")
    assert p.rating == 4.5

def test_missing_optional_fields_are_none():
    p = Product(url="https://example.com/p/5", source_site="temu")
    assert p.name is None
    assert p.price is None
    assert p.rating is None

def test_url_is_required():
    with pytest.raises(Exception):
        Product(source_site="amazon")

def test_in_stock_bool():
    p = Product(url="https://example.com/p/6", source_site="ebay", in_stock=True)
    assert p.in_stock is True
