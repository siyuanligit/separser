from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ListingData(BaseModel):
    url: str
    address: str
    neighborhood: str | None
    borough: str | None
    listing_type: Literal["sale", "rental", "new_dev"]
    price: int | None
    beds: float | None
    baths: float | None
    sqft: int | None
    price_per_sqft: int | None
    days_on_market: int | None
    listing_agent: str | None
    listing_brokerage: str | None
    open_house_dates: list[str]
    description: str | None
    scraped_at: datetime


class ParseError(BaseModel):
    error: Literal["cloudflare_block", "login_wall", "rate_limited", "parse_failed"]
    url: str
    detail: str | None = None
