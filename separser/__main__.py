import asyncio
import sys

from .browser import CloudflareError, LoginWallError, RateLimitError, fetch_page
from .models import ParseError
from .output import to_json, to_table
from .parser import parse


def _error_json(error: str, url: str, detail: str | None = None) -> str:
    return ParseError(error=error, url=url, detail=detail).model_dump_json(indent=2)


async def _run(url: str, output: str) -> int:
    try:
        html = await fetch_page(url)
    except LoginWallError as e:
        print(_error_json("login_wall", url, str(e)))
        return 1
    except CloudflareError as e:
        print(_error_json("cloudflare_block", url, str(e)))
        return 1
    except RateLimitError as e:
        print(_error_json("rate_limited", url, str(e)))
        return 1

    try:
        listing = parse(html, url)
    except Exception as e:
        print(_error_json("parse_failed", url, str(e)))
        return 1

    if output == "table":
        to_table(listing)
    else:
        print(to_json(listing))

    return 0


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Parse a StreetEasy listing URL")
    ap.add_argument("url", help="StreetEasy listing URL")
    ap.add_argument(
        "--output",
        choices=["json", "table"],
        default="json",
        help="Output format (default: json)",
    )
    args = ap.parse_args()

    sys.exit(asyncio.run(_run(args.url, args.output)))


if __name__ == "__main__":
    main()
