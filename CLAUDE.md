# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

StreetEasy listing parser — extracts structured property data from StreetEasy URLs for a buyer-side real estate salesperson in NYC. She pastes listing URLs into Claude Desktop (Mac); gets structured JSON her Claude agent reformats as needed.

**Output delivery:** JSON via MCP tool (`parse_listing`) in Claude Desktop. CLI (`--output json|table`) for dev/test on Windows.

## PRD Triggers

PRD required before building:
- Any new module
- Any new CLI flag or command
- Structural changes to `ListingData` schema (breaking, reordering, type changes)
- Any new output format

**No PRD needed:** Bugfixes and changes under ~20 lines. Additive `ListingData` field additions where the field is obviously present in the HTML and the type is unambiguous.

## Tech Stack

- **Python 3.10+**
- **Playwright + playwright-stealth** — headless browser with Cloudflare bypass
- **Pydantic v2** — typed listing models
- **MCP** — stdio server for Claude Desktop integration
- **Rich** — CLI table output
- **BeautifulSoup4** — HTML parsing
- **hatchling** — build backend (`pyproject.toml`)

## Setup (Windows dev)

```bash
pip install -e .
playwright install chromium
pytest
python -m separser "https://streeteasy.com/..." --output json
python -m separser "https://streeteasy.com/..." --output table
```

## Setup (Mac — end user)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "separser": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/siyuanligit/separser", "separser-mcp"]
    }
  }
}
```
Restart Claude Desktop. Chromium installs automatically on first use.

## Architecture

```
separser/
  __init__.py
  __main__.py      # CLI entry: python -m separser <url> [--output json|table]
  browser.py       # Playwright + stealth, retry/backoff, error detection
  parser.py        # HTML → ListingData; single parse() function, no branching
  models.py        # Pydantic: ListingData, PriceHistoryEntry, ParseError
  output.py        # to_json(), to_table()
  mcp_server.py    # MCP stdio server; parse_listing(url) tool
tests/
  fixtures/        # Saved HTML snapshots for offline testing
  test_parser.py   # 20 tests; fixture: tests/fixtures/sale_listing.html
pyproject.toml     # uvx-compatible; entry point: separser-mcp
```

**Rule:** Tests must use local HTML fixtures — never hit live StreetEasy. When a new page layout is encountered, save HTML to `tests/fixtures/` first, then write tests.

**Rule:** Do not replace Playwright with `requests`/`httpx` — Cloudflare blocks them.

**Rule:** `models.py::ListingData` is the canonical schema. Add fields there first — never touch parser or output code first.

## Output Model

```python
class PriceHistoryEntry(BaseModel):
    date: str
    price: int | None
    event: str | None

class ListingData(BaseModel):
    url: str
    address: str
    neighborhood: str | None
    borough: str | None
    listing_type: Literal["sale", "rental", "new_dev"]
    price: int | None                  # dollars, no commas
    beds: float | None                 # 0.0 = studio
    baths: float | None
    sqft: int | None
    price_per_sqft: int | None
    days_on_market: int | None
    listing_agent: str | None
    listing_brokerage: str | None
    common_charges: int | None         # $/mo
    taxes: int | None                  # $/mo
    tax_abatement: str | None          # e.g. "421a expires in 2032"
    policies: list[str]                # e.g. ["Pets allowed: Cats and dogs"]
    home_features: list[str]           # e.g. ["Central air", "View: Water"]
    building_amenities: list[str]      # e.g. ["Doorman: Full-time", "Gym"]
    building_url: str | None           # https://streeteasy.com/building/...
    building_type: str | None          # e.g. "Condo building"
    building_units: int | None
    building_stories: int | None
    year_built: int | None
    nearby_transit: list[str]          # e.g. ["L at Bedford Av", "JMZ at Marcy Av"]
    price_history: list[PriceHistoryEntry]
    open_house_dates: list[str]
    description: str | None
    scraped_at: datetime
```

## Selector Strategy

StreetEasy uses CSS modules with hashed class names (`ComponentName_property__hash`). Match by prefix:

```python
soup.find(class_=re.compile(r"^PriceInfo_price_"))
soup.find_all(class_=re.compile(r"^PropertyDetails_item_"))
```

Prefer `data-testid` attributes where available — they're more stable than class names.

## Known Failure Modes

| Failure | Symptom | Handling |
|---|---|---|
| Cloudflare 403/JS | 403 or JS challenge page | `playwright-stealth` + retry 3x with 2s/4s/8s backoff |
| Login wall | Redirect to `/register` | Detect URL change; return `{"error": "login_wall"}` |
| Rate limiting | 429 | Exponential backoff, max 3 retries; return `{"error": "rate_limited"}` |
| Parse failure | Missing fields | Return partial data with `null` fields — no crash |
| `days_on_market: null` | New dev listings don't show DOM | Expected; field stays null |
| `tax_abatement: "No info"` | Literal page text when no abatement | Expected; not a parse error |

## Note-Taking

Write decisions and open questions to `the project memory folder in .claude/`. Checkpoint when a feature ships, a PRD is signed off, or the conversation switches domains.
