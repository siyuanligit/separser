"""
Offline parser tests. Requires HTML fixture saved to tests/fixtures/sale_listing.html.

To add/update the fixture:
    1. Open a listing in a browser (logged out of StreetEasy)
    2. DevTools → right-click page → Save as... → Webpage, HTML Only
    3. Save to tests/fixtures/sale_listing.html
"""
from pathlib import Path

import pytest

from separser.models import ListingData
from separser.parser import parse

FIXTURE = Path(__file__).parent / "fixtures" / "sale_listing.html"
FIXTURE_URL = "https://streeteasy.com/building/schaefer-landing-south/7d"


@pytest.fixture(scope="module")
def listing():
    if not FIXTURE.exists():
        pytest.skip(f"Fixture not found: {FIXTURE}. Save HTML from a live listing first.")
    html = FIXTURE.read_text(encoding="utf-8")
    return parse(html, FIXTURE_URL)


def test_returns_listing_data(listing):
    assert isinstance(listing, ListingData)

def test_url_preserved(listing):
    assert listing.url == FIXTURE_URL

def test_address_not_empty(listing):
    assert listing.address

def test_listing_type_is_sale(listing):
    assert listing.listing_type == "sale"

def test_price_is_int(listing):
    assert isinstance(listing.price, int)
    assert listing.price == 949000

def test_beds(listing):
    assert listing.beds == 1.0

def test_baths(listing):
    assert listing.baths == 1.0

def test_sqft(listing):
    assert listing.sqft == 864

def test_price_per_sqft_computed(listing):
    assert listing.price_per_sqft == listing.price // listing.sqft

def test_neighborhood(listing):
    assert listing.neighborhood == "Williamsburg"

def test_borough(listing):
    assert listing.borough == "Brooklyn"

def test_days_on_market(listing):
    assert isinstance(listing.days_on_market, int)

def test_listing_agent(listing):
    assert listing.listing_agent == "Bruce Henderson"

def test_listing_brokerage(listing):
    assert listing.listing_brokerage == "Corcoran"

def test_common_charges(listing):
    assert listing.common_charges == 1227

def test_taxes(listing):
    assert listing.taxes == 5

def test_tax_abatement(listing):
    assert listing.tax_abatement == "421a expires in 2032"

def test_open_house_dates_is_list(listing):
    assert isinstance(listing.open_house_dates, list)

def test_description_not_empty(listing):
    assert listing.description and len(listing.description) > 20

def test_scraped_at_set(listing):
    assert listing.scraped_at is not None
