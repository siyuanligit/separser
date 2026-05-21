import asyncio
import subprocess
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .browser import CloudflareError, LoginWallError, RateLimitError, fetch_page
from .models import ParseError
from .output import to_json
from .parser import parse


def _ensure_chromium() -> None:
    """Install Playwright Chromium browser on first run if missing."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            pw.chromium.launch(headless=True).close()
    except Exception:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
        )


def _error_json(error: str, url: str, detail: str | None = None) -> str:
    return ParseError(error=error, url=url, detail=detail).model_dump_json(indent=2)


async def _parse_listing(url: str) -> str:
    try:
        html = await fetch_page(url)
    except LoginWallError as e:
        return _error_json("login_wall", url, str(e))
    except CloudflareError as e:
        return _error_json("cloudflare_block", url, str(e))
    except RateLimitError as e:
        return _error_json("rate_limited", url, str(e))

    try:
        listing = parse(html, url)
        return to_json(listing)
    except Exception as e:
        return _error_json("parse_failed", url, str(e))


def main() -> None:
    _ensure_chromium()

    app = Server("separser")

    @app.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="parse_listing",
                description=(
                    "Fetch a StreetEasy listing URL and return structured property data as JSON. "
                    "Returns a ListingData object or a ParseError object on failure."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Full StreetEasy listing URL",
                        }
                    },
                    "required": ["url"],
                },
            )
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name != "parse_listing":
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
        url = arguments.get("url", "")
        result = await _parse_listing(url)
        return [TextContent(type="text", text=result)]

    asyncio.run(stdio_server(app))


if __name__ == "__main__":
    main()
