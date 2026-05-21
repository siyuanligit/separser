from rich.console import Console
from rich.table import Table

from .models import ListingData


def to_json(listing: ListingData) -> str:
    return listing.model_dump_json(indent=2)


def to_table(listing: ListingData) -> None:
    console = Console()
    table = Table(title=listing.address, show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold cyan", no_wrap=True)
    table.add_column("Value")

    rows = [
        ("Type", listing.listing_type),
        ("Price", f"${listing.price:,}" if listing.price else "—"),
        ("Beds", ("Studio" if listing.beds == 0 else str(int(listing.beds) if listing.beds == int(listing.beds) else listing.beds)) if listing.beds is not None else "—"),
        ("Baths", (str(int(listing.baths) if listing.baths == int(listing.baths) else listing.baths)) if listing.baths is not None else "—"),
        ("Sqft", f"{listing.sqft:,}" if listing.sqft else "—"),
        ("$/sqft", f"${listing.price_per_sqft:,}" if listing.price_per_sqft else "—"),
        ("Neighborhood", listing.neighborhood or "—"),
        ("Borough", listing.borough or "—"),
        ("DOM", str(listing.days_on_market) if listing.days_on_market is not None else "—"),
        ("Agent", listing.listing_agent or "—"),
        ("Brokerage", listing.listing_brokerage or "—"),
        ("Common Charges", f"${listing.common_charges:,}/mo" if listing.common_charges else "—"),
        ("Taxes", f"${listing.taxes:,}/mo" if listing.taxes else "—"),
        ("Tax Abatement", listing.tax_abatement or "—"),
        ("Open Houses", ", ".join(listing.open_house_dates) if listing.open_house_dates else "—"),
        ("URL", listing.url),
        ("Scraped", listing.scraped_at.strftime("%Y-%m-%d %H:%M UTC")),
    ]

    for field, value in rows:
        table.add_row(field, value)

    console.print(table)
