from scrapers.amazon import AmazonScraper
from scrapers.ebay import EbayScraper
from scrapers.aliexpress import AliExpressScraper
from scrapers.uzum import UzumScraper
from scrapers.wildberries import WildberriesScraper
from scrapers.yandex_market import YandexMarketScraper
from scrapers.temu import TemuScraper

DB_PATH = "products.db"
DEFAULT_MAX_PRODUCTS = 50

SITES: dict = {
    "amazon":      AmazonScraper,
    "ebay":        EbayScraper,
    "aliexpress":  AliExpressScraper,
    "uzum":        UzumScraper,
    "wildberries": WildberriesScraper,
    "yandex":      YandexMarketScraper,
    "temu":        TemuScraper,
}
