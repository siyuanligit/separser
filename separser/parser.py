import re
from datetime import datetime, timezone
from typing import Literal

from bs4 import BeautifulSoup

from .models import ListingData


def _int(text: str | None) -> int | None:
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def _float(text: str | None) -> float | None:
    if not text:
        return None
    text = text.strip().lower()
    if "studio" in text:
        return 0.0
    m = re.search(r"[\d.]+", text)
    return float(m.group()) if m else None


def _text(el) -> str | None:
    return el.get_text(strip=True) if el else None


def detect_listing_type(html: str, url: str) -> Literal["sale", "new_dev"]:
    if "/building/" in url or "/new-development/" in url:
        return "new_dev"
    soup = BeautifulSoup(html, "html.parser")
    # New dev pages often have a "residences" or "availability" section
    if soup.find(attrs={"data-testid": "new-development-detail"}):
        return "new_dev"
    if soup.find(class_=re.compile(r"NewDev|new-dev|newdev", re.I)):
        return "new_dev"
    return "sale"


def _parse_common(soup: BeautifulSoup, url: str, listing_type: Literal["sale", "new_dev"]) -> dict:
    """Extract fields shared between sale and new_dev layouts."""

    # Address — most reliable selector
    address_el = (
        soup.find(attrs={"data-testid": "listing-title"})
        or soup.find(class_=re.compile(r"listingDetailAddress|address", re.I))
        or soup.find("h1")
    )
    address = _text(address_el) or ""

    # Neighborhood / borough from breadcrumb or meta
    neighborhood: str | None = None
    borough: str | None = None
    breadcrumb = soup.find(attrs={"data-testid": "breadcrumbs"}) or soup.find(
        class_=re.compile(r"breadcrumb", re.I)
    )
    if breadcrumb:
        crumbs = [a.get_text(strip=True) for a in breadcrumb.find_all("a")]
        BOROUGHS = {"Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"}
        for crumb in crumbs:
            if crumb in BOROUGHS:
                borough = crumb
            elif borough:
                neighborhood = crumb
                break

    # Price
    price_el = soup.find(attrs={"data-testid": "price"}) or soup.find(
        class_=re.compile(r"price", re.I)
    )
    price = _int(_text(price_el))

    # Beds / baths / sqft from detail summary bar
    beds: float | None = None
    baths: float | None = None
    sqft: int | None = None

    detail_items = soup.find_all(attrs={"data-testid": re.compile(r"bed|bath|sqft|size", re.I)})
    for item in detail_items:
        label = item.get("data-testid", "").lower()
        val = _text(item)
        if "bed" in label:
            beds = _float(val)
        elif "bath" in label:
            baths = _float(val)
        elif "sqft" in label or "size" in label:
            sqft = _int(val)

    # Fallback: scan summary facts
    if beds is None or baths is None or sqft is None:
        facts = soup.find_all(class_=re.compile(r"Detail_|listingFact|DetailsTable", re.I))
        for fact in facts:
            txt = _text(fact) or ""
            if re.search(r"\d+\s*bed", txt, re.I) and beds is None:
                beds = _float(re.search(r"[\d.]+", txt).group() if re.search(r"[\d.]+", txt) else None)
            if re.search(r"\d+\s*bath", txt, re.I) and baths is None:
                baths = _float(re.search(r"[\d.]+", txt).group() if re.search(r"[\d.]+", txt) else None)
            if re.search(r"[\d,]+\s*ft", txt, re.I) and sqft is None:
                sqft = _int(re.sub(r"[^\d]", "", txt) or None)

    price_per_sqft = int(price / sqft) if price and sqft else None

    # Days on market
    dom_el = soup.find(string=re.compile(r"days?\s+on\s+market", re.I))
    days_on_market: int | None = None
    if dom_el:
        parent = dom_el.parent
        m = re.search(r"\d+", _text(parent) or "")
        days_on_market = int(m.group()) if m else None

    # Agent / brokerage
    agent_el = soup.find(attrs={"data-testid": "agent-name"}) or soup.find(
        class_=re.compile(r"agentName|agent-name|listingAgent", re.I)
    )
    listing_agent = _text(agent_el)

    broker_el = soup.find(attrs={"data-testid": "brokerage-name"}) or soup.find(
        class_=re.compile(r"brokerageName|brokerage-name", re.I)
    )
    listing_brokerage = _text(broker_el)

    # Open house dates
    oh_els = soup.find_all(attrs={"data-testid": re.compile(r"open-house", re.I)}) or soup.find_all(
        class_=re.compile(r"openHouse|open-house", re.I)
    )
    open_house_dates = [_text(el) for el in oh_els if _text(el)]

    # Description
    desc_el = (
        soup.find(attrs={"data-testid": "listing-description"})
        or soup.find(class_=re.compile(r"description|listingDescription", re.I))
    )
    description = _text(desc_el)

    return dict(
        url=url,
        address=address,
        neighborhood=neighborhood,
        borough=borough,
        listing_type=listing_type,
        price=price,
        beds=beds,
        baths=baths,
        sqft=sqft,
        price_per_sqft=price_per_sqft,
        days_on_market=days_on_market,
        listing_agent=listing_agent,
        listing_brokerage=listing_brokerage,
        open_house_dates=open_house_dates,
        description=description,
        scraped_at=datetime.now(timezone.utc),
    )


def parse_sale(html: str, url: str) -> ListingData:
    soup = BeautifulSoup(html, "html.parser")
    data = _parse_common(soup, url, "sale")
    return ListingData(**data)


def parse_new_dev(html: str, url: str) -> ListingData:
    soup = BeautifulSoup(html, "html.parser")
    data = _parse_common(soup, url, "new_dev")
    # New dev pages may list price as a range — take the lower bound
    if data["price"] is None:
        price_text_el = soup.find(class_=re.compile(r"price|Price", re.I))
        if price_text_el:
            first_num = re.search(r"[\d,]+", _text(price_text_el) or "")
            data["price"] = _int(first_num.group()) if first_num else None
    return ListingData(**data)


def parse(html: str, url: str) -> ListingData:
    listing_type = detect_listing_type(html, url)
    if listing_type == "new_dev":
        return parse_new_dev(html, url)
    return parse_sale(html, url)
