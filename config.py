from scrapers.aliexpress import AliExpressScraper
from scrapers.amazon import AmazonScraper
from scrapers.ebay import EbayScraper
from scrapers.temu import TemuScraper
from scrapers.uzum import UzumScraper
from scrapers.wildberries import WildberriesScraper
from scrapers.yandex_market import YandexMarketScraper

DB_PATH = "products.db"
DEFAULT_MAX_PRODUCTS = 50

LOG_PATH = "logs"

SITES: dict = {
    "amazon":      AmazonScraper,
    "ebay":        EbayScraper,
    "aliexpress":  AliExpressScraper,
    "uzum":        UzumScraper,
    "wildberries": WildberriesScraper,
    "yandex":      YandexMarketScraper,
    "temu":        TemuScraper,
}
