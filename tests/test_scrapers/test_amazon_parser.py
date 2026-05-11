import pathlib
from scrapers.amazon import AmazonScraper

FIXTURE = pathlib.Path("tests/fixtures/amazon_product.html").read_text()

def test_parse_name():
    result = AmazonScraper.parse_product_html(FIXTURE, "https://amazon.com/dp/B001")
    assert result["name"] == "Sony WH-1000XM5 Wireless Headphones"

def test_parse_price():
    result = AmazonScraper.parse_product_html(FIXTURE, "https://amazon.com/dp/B001")
    assert result["price"] == "$279.99"

def test_parse_original_price():
    result = AmazonScraper.parse_product_html(FIXTURE, "https://amazon.com/dp/B001")
    assert result["original_price"] == "$349.99"

def test_parse_rating():
    result = AmazonScraper.parse_product_html(FIXTURE, "https://amazon.com/dp/B001")
    assert result["rating"] == "4.4 out of 5 stars"

def test_parse_review_count():
    result = AmazonScraper.parse_product_html(FIXTURE, "https://amazon.com/dp/B001")
    assert result["review_count"] == "14,532 ratings"

def test_parse_in_stock():
    result = AmazonScraper.parse_product_html(FIXTURE, "https://amazon.com/dp/B001")
    assert result["in_stock"] is True

def test_parse_image():
    result = AmazonScraper.parse_product_html(FIXTURE, "https://amazon.com/dp/B001")
    assert result["image_url"] == "https://example.com/img.jpg"
