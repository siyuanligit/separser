import re
from datetime import datetime, timezone

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


def _cls(soup, prefix: str) -> Tag | None:
    return soup.find(class_=re.compile(r"^" + re.escape(prefix)))


def _cls_all(soup, prefix: str) -> list[Tag]:
    return soup.find_all(class_=re.compile(r"^" + re.escape(prefix)))


# --- field extractors ---

def _extract_listing_type(url: str) -> str:
    if "/new-development/" in url:
        return "new_dev"
    if "/for-rent/" in url or "/rental/" in url:
        return "rental"
    return "sale"


def _extract_price(soup: BeautifulSoup) -> int | None:
    el = _cls(soup, "PriceInfo_price__")
    return _int(el.get_text(strip=True)) if el else None


def _extract_property_details(soup: BeautifulSoup) -> dict:
    beds: float | None = None
    baths: float | None = None
    sqft: int | None = None
    price_per_sqft: int | None = None

    for item in _cls_all(soup, "PropertyDetails_item__"):
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
    h1 = soup.find("h1")
    return h1.get_text(strip=True) if h1 else ""


def _extract_location(soup: BeautifulSoup) -> tuple[str | None, str | None]:
    BOROUGHS = {"Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"}
    breadcrumb = soup.find(attrs={"data-testid": "breadcrumbs"}) or soup.find(
        class_=re.compile(r"breadcrumb", re.I)
    )
    neighborhood: str | None = None
    borough: str | None = None
    if breadcrumb:
        for crumb in [a.get_text(strip=True) for a in breadcrumb.find_all("a")]:
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
    agent_el = _cls(soup, "AgentCard_title__")
    agent = agent_el.get_text(strip=True) or None if agent_el else None

    brokerage: str | None = None
    listing_by = soup.find(attrs={"data-testid": "listing-by"})
    if listing_by:
        m = re.match(r"Listing by\s+([^,]+)", listing_by.get_text(strip=True), re.I)
        if m:
            brokerage = m.group(1).strip()

    return agent, brokerage


def _extract_costs(soup: BeautifulSoup) -> dict:
    common_charges: int | None = None
    taxes: int | None = None
    tax_abatement: str | None = None

    for item in _cls_all(soup, "SaleListingSpecSection_costsSpecItem__"):
        title_el = _cls(item, "SaleListingSpec_title__")
        if not title_el:
            continue
        label = title_el.get_text(strip=True).lower()
        value = item.get_text(strip=True)[len(title_el.get_text(strip=True)):].strip()

        if "common charge" in label:
            common_charges = _int(value)
        elif label == "taxes":
            taxes = _int(value)
        elif "abatement" in label:
            tax_abatement = re.sub(r"\s*\$[\d,]+/mo.*$", "", value).strip() or None

    return {"common_charges": common_charges, "taxes": taxes, "tax_abatement": tax_abatement}


def _extract_list_items(section: Tag) -> list[str]:
    """Extract items from a ListItem_item__ section, merging sub-items as 'Item: sub'."""
    results = []
    for item in section.find_all(class_=re.compile(r"^ListItem_item_")):
        sub = item.find(class_=re.compile(r"^ListItem_subItemTitle_"))
        if sub:
            sub_txt = sub.get_text(strip=True)
            main_txt = item.get_text(strip=True).replace(sub_txt, "").strip()
            results.append(f"{main_txt}: {sub_txt}" if main_txt else sub_txt)
        else:
            txt = item.get_text(strip=True)
            if txt:
                results.append(txt)
    return results


def _extract_feature_sections(soup: BeautifulSoup) -> dict:
    policies: list[str] = []
    home_features: list[str] = []
    building_amenities: list[str] = []

    # Policies lives in a ListOfLists_section_ without a data-testid
    for section in soup.find_all(class_=re.compile(r"^ListOfLists_section_")):
        header_el = section.find(class_=re.compile(r"^ListOfLists_header_"))
        if not header_el:
            continue
        label = header_el.get_text(strip=True).lower()
        items = _extract_list_items(section)
        if "polic" in label:
            policies = items
        elif "home feature" in label:
            home_features = items

    # Home features and building amenities have reliable data-testid
    hf = soup.find(attrs={"data-testid": "home-features-section"})
    if hf:
        home_features = _extract_list_items(hf)

    ba = soup.find(attrs={"data-testid": "building-amenities-section"})
    if ba:
        building_amenities = _extract_list_items(ba)

    return {"policies": policies, "home_features": home_features, "building_amenities": building_amenities}


def _extract_building_url(soup: BeautifulSoup) -> str | None:
    about = soup.find(attrs={"data-testid": "about-building-section"})
    if about:
        for a in about.find_all("a", href=True):
            href = a["href"]
            # "Learn more about X" link goes directly to the building page
            if re.match(r"^https?://streeteasy\.com/building/[^/?]+$", href):
                return href
    # fallback: derive from canonical URL by stripping unit segment
    canonical = soup.find("link", rel="canonical")
    if canonical and canonical.get("href"):
        m = re.match(r"(https?://streeteasy\.com/building/[^/]+)/", canonical["href"])
        if m:
            return m.group(1)
    return None


def _extract_nearby_transit(soup: BeautifulSoup) -> list[str]:
    results = []
    for el in soup.find_all(attrs={"data-testid": "station-info"}):
        # Line badges are in child spans; station name is the trailing text node
        badges = [s.get_text(strip=True) for s in el.find_all("span") if s.get_text(strip=True)]
        line = "".join(badges)
        # Get text after stripping badge text, then strip "at" prefix
        full = el.get_text(strip=True)
        station = re.sub(r"^" + re.escape(line) + r"\s*at\s*", "", full).strip()
        if line and station:
            results.append(f"{line} at {station}")
        elif full:
            results.append(full)
    return results


def _extract_building_info(soup: BeautifulSoup) -> dict:
    building_type: str | None = None
    building_units: int | None = None
    building_stories: int | None = None
    year_built: int | None = None

    icons = soup.find(attrs={"data-testid": "building-description-icons"})
    if icons:
        txt = icons.get_text(strip=True)
        m = re.search(r"([\d,]+)\s*units?", txt, re.I)
        if m:
            building_units = _int(m.group(1))
        m = re.search(r"([\d,]+)\s*stor", txt, re.I)
        if m:
            building_stories = _int(m.group(1))
        m = re.search(r"(\d{4})\s*built", txt, re.I)
        if m:
            year_built = int(m.group(1))

    about = soup.find(attrs={"data-testid": "about-building-section"})
    if about:
        m = re.search(r"(condo|co-op|coop|rental|townhouse|multi.family)\s*building", about.get_text(strip=True), re.I)
        if m:
            building_type = m.group(0).strip()

    return {
        "building_type": building_type,
        "building_units": building_units,
        "building_stories": building_stories,
        "year_built": year_built,
    }


def _extract_price_history(soup: BeautifulSoup) -> list:
    from .models import PriceHistoryEntry
    results = []
    for wrapper in soup.find_all(class_=re.compile(r"^PriceHistoryTable_priceEventWrapper__")):
        row = wrapper
        for _ in range(5):
            row = row.parent
            if row and row.name == "tr":
                break
        if not row or row.name != "tr":
            continue
        cells = row.find_all(["td", "th"])
        if len(cells) < 3:
            continue
        date_txt = cells[0].get_text(strip=True)
        price_txt = cells[1].get_text(strip=True)
        # Join multiple <p> elements with " · " to avoid merged text
        paras = [p.get_text(strip=True) for p in cells[2].find_all("p") if p.get_text(strip=True)]
        event_txt = " · ".join(paras) if paras else cells[2].get_text(strip=True)
        event_clean = re.sub(r"This is the number.*$", "", event_txt, flags=re.I).strip() or None
        results.append(PriceHistoryEntry(
            date=date_txt,
            price=_int(price_txt),
            event=event_clean,
        ))
    return results


def _extract_open_houses(soup: BeautifulSoup) -> list[str]:
    results = []
    for slot in _cls_all(soup, "OpenHouseCard_openHouseSlotDate__"):
        date_el = slot.find(class_=re.compile(r"SecondarySmall_|Heading_"))
        time_el = slot.find(class_=re.compile(r"Body_base_"))
        appt_el = slot.find(class_=re.compile(r"OpenHouseCard_appointmentBadge__"))
        parts = [el.get_text(strip=True) for el in [date_el, time_el, appt_el] if el]
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


# --- public API ---

def parse(html: str, url: str) -> ListingData:
    soup = BeautifulSoup(html, "html.parser")
    details = _extract_property_details(soup)
    costs = _extract_costs(soup)
    features = _extract_feature_sections(soup)
    building = _extract_building_info(soup)
    building_url = _extract_building_url(soup)
    nearby_transit = _extract_nearby_transit(soup)
    price = _extract_price(soup)
    agent, brokerage = _extract_agent(soup)
    neighborhood, borough = _extract_location(soup)

    if details["price_per_sqft"] is None and price and details["sqft"]:
        details["price_per_sqft"] = price // details["sqft"]

    return ListingData(
        url=url,
        address=_extract_address(soup),
        neighborhood=neighborhood,
        borough=borough,
        listing_type=_extract_listing_type(url),
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
        policies=features["policies"],
        home_features=features["home_features"],
        building_amenities=features["building_amenities"],
        building_url=building_url,
        building_type=building["building_type"],
        building_units=building["building_units"],
        building_stories=building["building_stories"],
        year_built=building["year_built"],
        nearby_transit=nearby_transit,
        price_history=_extract_price_history(soup),
        open_house_dates=_extract_open_houses(soup),
        description=_extract_description(soup),
        scraped_at=datetime.now(timezone.utc),
    )
