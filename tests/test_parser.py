"""
Offline parser tests. Requires HTML fixtures saved to tests/fixtures/.

To add a fixture:
    1. Open the listing in a browser (logged out)
    2. Save the full page HTML: browser DevTools → Sources → right-click → Save as...
    3. Place in tests/fixtures/sale_listing.html or new_dev_listing.html
"""
import os
from pathlib import Path

import pytest

from separser.models import ListingData
from separser.parser import detect_listing_type, parse

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    path = FIXTURES / name
    if not path.exists():
        pytest.skip(f"Fixture not found: {path}. Save HTML from a live listing first.")
    return path.read_text(encoding="utf-8")


class TestSaleListing:
    def setup_method(self):
        self.html = _load("sale_listing.html")
        self.url = "https://streeteasy.com/building/123-main-st-new_york/4a"

    def test_detect_type(self):
        assert detect_listing_type(self.html, self.url) == "sale"

    def test_returns_listing_data(self):
        result = parse(self.html, self.url)
        assert isinstance(result, ListingData)

    def test_listing_type_field(self):
        result = parse(self.html, self.url)
        assert result.listing_type == "sale"

    def test_address_not_empty(self):
        result = parse(self.html, self.url)
        assert result.address

    def test_price_is_int_or_none(self):
        result = parse(self.html, self.url)
        assert result.price is None or isinstance(result.price, int)

    def test_beds_is_float_or_none(self):
        result = parse(self.html, self.url)
        assert result.beds is None or isinstance(result.beds, float)

    def test_price_per_sqft_computed(self):
        result = parse(self.html, self.url)
        if result.price and result.sqft:
            assert result.price_per_sqft == result.price // result.sqft

    def test_open_house_dates_is_list(self):
        result = parse(self.html, self.url)
        assert isinstance(result.open_house_dates, list)

    def test_scraped_at_set(self):
        result = parse(self.html, self.url)
        assert result.scraped_at is not None

    def test_url_preserved(self):
        result = parse(self.html, self.url)
        assert result.url == self.url


class TestNewDevListing:
    def setup_method(self):
        self.html = _load("new_dev_listing.html")
        self.url = "https://streeteasy.com/building/some-new-dev-building"

    def test_detect_type(self):
        assert detect_listing_type(self.html, self.url) == "new_dev"

    def test_returns_listing_data(self):
        result = parse(self.html, self.url)
        assert isinstance(result, ListingData)

    def test_listing_type_field(self):
        result = parse(self.html, self.url)
        assert result.listing_type == "new_dev"

    def test_address_not_empty(self):
        result = parse(self.html, self.url)
        assert result.address

    def test_price_is_int_or_none(self):
        result = parse(self.html, self.url)
        assert result.price is None or isinstance(result.price, int)
