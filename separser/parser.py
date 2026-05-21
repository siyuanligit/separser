import re
from datetime import datetime, timezone
from typing import Literal

from bs4 import BeautifulSoup, Tag

from .models import ListingData


# --- helpers ---

def _int(text: str | None) -> int | None:
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def _float_beds(text: str | None) -> float | None:
    if not text:
        return None
    text = text.strip().lower()
    if "studio" in text:
        return 0.0
    m = re.search(r"[\d.]+", text)
    return float(m.group()) if m else None


def _cls(soup: BeautifulSoup, prefix: str) -> Tag | None:
    """Find first element whose class list contains a class starting with prefix."""
    return soup.find(class_=re.compile(r"^" + re.escape(prefix)))


def _cls_all(soup: BeautifulSoup, prefix: str) -> list[Tag]:
    return soup.find_all(class_=re.compile(r"^" + re.escape(prefix)))


# --- type detection ---

def detect_listing_type(html: str, url: str) -> Literal["sale", "new_dev"]:
    if "/new-development/" in url:
        return "new_dev"
    soup = BeautifulSoup(html, "html.parser")
    if soup.find(attrs={"data-testid": "new-development-detail"}):
        return "new_dev"
    return "sale"


# --- field extractors ---

def _extract_price(soup: BeautifulSoup) -> int | None:
    el = _cls(soup, "PriceInfo_price__")
    return _int(el.get_text(strip=True)) if el else None


def _extract_property_details(soup: BeautifulSoup) -> dict:
    """Parse the PropertyDetails block: sqft, price_per_sqft, beds, baths."""
    beds: float | None = None
    baths: float | None = None
    sqft: int | None = None
    price_per_sqft: int | None = None

    items = _cls_all(soup, "PropertyDetails_item__")
    for item in items:
        txt = item.get_text(strip=True)
        if re.search(r"per\s*ft", txt, re.I):
            price_per_sqft = _int(txt)
        elif re.search(r"ft[²2]|sq\s*ft", txt, re.I):
            sqft = _int(txt)
        elif re.search(r"bed", txt, re.I):
            beds = _float_beds(txt)
        elif re.search(r"bath", txt, re.I):
            baths = _float_beds(txt)

    return {"beds": beds, "baths": baths, "sqft": sqft, "price_per_sqft": price_per_sqft}


def _extract_address(soup: BeautifulSoup) -> str:
    # H1 is most reliable for the full address line
    h1 = soup.find("h1")
    return h1.get_text(strip=True) if h1 else ""


def _extract_location(soup: BeautifulSoup) -> tuple[str | None, str | None]:
    """Return (neighborhood, borough) from breadcrumb."""
    BOROUGHS = {"Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"}
    breadcrumb = soup.find(attrs={"data-testid": "breadcrumbs"}) or soup.find(
        class_=re.compile(r"breadcrumb", re.I)
    )
    neighborhood: str | None = None
    borough: str | None = None
    if breadcrumb:
        crumbs = [a.get_text(strip=True) for a in breadcrumb.find_all("a")]
        for crumb in crumbs:
            if crumb in BOROUGHS:
                borough = crumb
            elif borough and not neighborhood:
                neighborhood = crumb
    return neighborhood, borough


def _extract_dom(soup: BeautifulSoup) -> int | None:
    match = soup.find(string=re.compile(r"Days on market:\s*\d+", re.I))
    if match:
        m = re.search(r"\d+", str(match))
        return int(m.group()) if m else None
    return None


def _extract_agent(soup: BeautifulSoup) -> tuple[str | None, str | None]:
    """Return (listing_agent, listing_brokerage)."""
    agent: str | None = None
    brokerage: str | None = None

    # Agent name: first AgentCard title
    agent_el = _cls(soup, "AgentCard_title__")
    if agent_el:
        agent = agent_el.get_text(strip=True) or None

    # Brokerage: data-testid="listing-by" → "Listing by Corcoran, ..."
    listing_by = soup.find(attrs={"data-testid": "listing-by"})
    if listing_by:
        txt = listing_by.get_text(strip=True)
        m = re.match(r"Listing by\s+([^,]+)", txt, re.I)
        if m:
            brokerage = m.group(1).strip()

    return agent, brokerage


def _extract_costs(soup: BeautifulSoup) -> dict:
    """Extract common_charges, taxes, tax_abatement from the costs section."""
    common_charges: int | None = None
    taxes: int | None = None
    tax_abatement: str | None = None

    items = _cls_all(soup, "SaleListingSpecSection_costsSpecItem__")
    for item in items:
        title_el = _cls(item, "SaleListingSpec_title__")
        if not title_el:
            continue
        label = title_el.get_text(strip=True).lower()
        # value is the full item text minus the label
        full = item.get_text(strip=True)
        value = full[len(title_el.get_text(strip=True)):].strip()

        if "common charge" in label:
            common_charges = _int(value)
        elif label == "taxes":
            taxes = _int(value)
        elif "abatement" in label:
            # strip trailing month/dollar noise, keep descriptive text
            tax_abatement = re.sub(r"\s*\$[\d,]+/mo.*$", "", value).strip() or None

    return {"common_charges": common_charges, "taxes": taxes, "tax_abatement": tax_abatement}


def _extract_open_houses(soup: BeautifulSoup) -> list[str]:
    """Extract clean open house date strings."""
    slots = _cls_all(soup, "OpenHouseCard_openHouseSlotDate__")
    results = []
    for slot in slots:
        # slot contains: date el + time el + optional appointment badge
        date_el = slot.find(class_=re.compile(r"SecondarySmall_|Heading_"))
        time_el = slot.find(class_=re.compile(r"Body_base_"))
        appt_el = slot.find(class_=re.compile(r"OpenHouseCard_appointmentBadge__"))

        parts = []
        if date_el:
            parts.append(date_el.get_text(strip=True))
        if time_el:
            parts.append(time_el.get_text(strip=True))
        if appt_el:
            parts.append(appt_el.get_text(strip=True))

        entry = " ".join(parts).strip()
        if entry:
            results.append(entry)
    return results


def _extract_description(soup: BeautifulSoup) -> str | None:
    el = _cls(soup, "ListingDescription_shortDescription__") or _cls(
        soup, "ListingDescription_fullDescription__"
    )
    if el:
        txt = el.get_text(strip=True)
        return txt if len(txt) > 10 else None
    return None


# --- main parsers ---

def _build(soup: BeautifulSoup, url: str, listing_type: Literal["sale", "new_dev"]) -> ListingData:
    neighborhood, borough = _extract_location(soup)
    details = _extract_property_details(soup)
    costs = _extract_costs(soup)
    price = _extract_price(soup)
    agent, brokerage = _extract_agent(soup)

    if details["price_per_sqft"] is None and price and details["sqft"]:
        details["price_per_sqft"] = price // details["sqft"]

    return ListingData(
        url=url,
        address=_extract_address(soup),
        neighborhood=neighborhood,
        borough=borough,
        listing_type=listing_type,
        price=price,
        beds=details["beds"],
        baths=details["baths"],
        sqft=details["sqft"],
        price_per_sqft=details["price_per_sqft"],
        days_on_market=_extract_dom(soup),
        listing_agent=agent,
        listing_brokerage=brokerage,
        common_charges=costs["common_charges"],
        taxes=costs["taxes"],
        tax_abatement=costs["tax_abatement"],
        open_house_dates=_extract_open_houses(soup),
        description=_extract_description(soup),
        scraped_at=datetime.now(timezone.utc),
    )


def parse_sale(html: str, url: str) -> ListingData:
    return _build(BeautifulSoup(html, "html.parser"), url, "sale")


def parse_new_dev(html: str, url: str) -> ListingData:
    return _build(BeautifulSoup(html, "html.parser"), url, "new_dev")


def parse(html: str, url: str) -> ListingData:
    listing_type = detect_listing_type(html, url)
    if listing_type == "new_dev":
        return parse_new_dev(html, url)
    return parse_sale(html, url)
