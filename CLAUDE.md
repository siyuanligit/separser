# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

StreetEasy listing parser — extracts structured property data from StreetEasy URLs for a buyer-side real estate agent, a buyer-side real estate salesperson in NYC. She inputs listing links; gets structured data she can use directly in her workflow.

**Output delivery:** TBD — confirm before building output module: CSV/Excel, Google Sheets, formatted CLI table, or other?

## PRD Triggers

PRD required before building:
- Any new module
- Any new CLI flag or command
- Any change to `ListingData` schema
- Any new output format

Bugfixes and changes under ~20 lines: no PRD needed.

## Tech Stack

- **Python 3.11+**
- **Playwright** — headless browser (StreetEasy blocks requests-based scrapers via Cloudflare)
- **Pydantic** — typed listing models
- **Rich** — CLI output

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
```

## Commands

> Not yet implemented. Target CLI interface:

```bash
python -m separser "https://streeteasy.com/..."     # single URL
python -m separser --batch urls.txt                 # batch (one URL per line)
python -m separser "..." --output json              # JSON output
pytest                                              # all tests
pytest tests/test_parser.py::test_listing_parse -v # single test
ruff check . && ruff format .                       # lint
```

## Target Architecture

```
separser/
  __main__.py      # CLI entry point
  browser.py       # Playwright session management (stealth, cookies, retries)
  parser.py        # HTML → ListingData extraction logic
  models.py        # Pydantic models (ListingData, AgentInfo, etc.)
  output.py        # Formatters: JSON, CSV, Rich table
tests/
  fixtures/        # Saved HTML snapshots for offline testing
  test_parser.py   # Tests run against fixtures, not live site
```

**Rule:** Tests must use local HTML fixtures — never hit live StreetEasy. When a new page layout is encountered, save HTML to `tests/fixtures/` first, then write tests.

**Rule:** Do not replace Playwright with `requests`/`httpx` — Cloudflare blocks them.

## Output Model

`models.py::ListingData` is the canonical schema. All parsers and formatters depend on it. Add fields here first — never touch parser or output code first.

```python
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
    open_house_dates: list[str]
    description: str | None
    scraped_at: datetime
```

## Known Failure Modes

| Failure | Symptom | Handling |
|---|---|---|
| Cloudflare challenge | 403 or JS challenge page | Retry with longer delay; rotate user-agent |
| Login wall | Redirect to `/register` | Detect URL change; raise `AuthWallError` |
| Rental vs. sale structure | Missing price/sqft fields | Detect `listing_type` first; branch parser |
| New dev listings | Different DOM layout | Separate parser path; requires new fixture |
| Rate limiting | Repeated 429s | Exponential backoff; max 3 retries then fail |

## Note-Taking

Write decisions and open questions to `the project memory folder in .claude/`. Checkpoint when a feature ships, a PRD is signed off, or the conversation switches domains.
