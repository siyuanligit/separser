# SEParser

StreetEasy listing parser for Claude Desktop (Mac). Paste a listing URL; get structured JSON.

## Setup (Mac — one time)

### 1. Install uv
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Add to Claude Desktop config

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

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

### 3. Restart Claude Desktop

Chromium installs automatically on first use.

### Usage

Ask Claude:
> "Can you parse this listing for me: https://streeteasy.com/..."

---

## Dev Setup (Windows)

```bash
pip install -e .
playwright install chromium
```

```bash
python -m separser "https://streeteasy.com/..." --output json
python -m separser "https://streeteasy.com/..." --output table
pytest
```

---

## Adding Test Fixtures

Tests run offline against saved HTML. To add or update the fixture:

1. Open a listing in a browser (logged out of StreetEasy)
2. DevTools → right-click page → Save as... → Webpage, HTML Only
3. Save to `tests/fixtures/sale_listing.html`
4. Run `pytest`

---

## Error Responses

All errors return JSON, not crashes:

| Error | Cause |
|---|---|
| `cloudflare_block` | 403 or JS challenge after 3 retries |
| `login_wall` | Page redirected to /register |
| `rate_limited` | 429 after 3 retries |
| `parse_failed` | HTML parsed but extraction failed |
