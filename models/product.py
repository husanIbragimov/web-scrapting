from pydantic import BaseModel, field_validator, Field
from typing import Optional
from datetime import datetime, timezone
import re

class Product(BaseModel):
    model_config = {"str_strip_whitespace": True}

    url: str
    source_site: str
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    name: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    original_price: Optional[float] = None
    discount_percent: Optional[float] = None

    rating: Optional[float] = None
    review_count: Optional[int] = None

    category: Optional[str] = None
    brand: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    in_stock: Optional[bool] = None
    seller: Optional[str] = None

    @field_validator("price", "original_price", "discount_percent", mode="before")
    @classmethod
    def parse_price(cls, v):
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        cleaned = re.sub(r"[^\d.]", "", str(v).replace(",", ""))
        return float(cleaned) if cleaned else None

    @field_validator("review_count", mode="before")
    @classmethod
    def parse_review_count(cls, v):
        if v is None:
            return None
        if isinstance(v, int):
            return v
        cleaned = re.sub(r"[^\d]", "", str(v))
        return int(cleaned) if cleaned else None

    @field_validator("rating", mode="before")
    @classmethod
    def parse_rating(cls, v):
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        m = re.search(r"[\d.]+", str(v))
        return float(m.group()) if m else None
