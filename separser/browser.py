import asyncio
from contextlib import asynccontextmanager

from playwright.async_api import async_playwright, Page, Response
from playwright_stealth import Stealth


class CloudflareError(Exception):
    pass


class LoginWallError(Exception):
    pass


class RateLimitError(Exception):
    pass


_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/148.0.0.0 Safari/537.36"
)

_EXTRA_HEADERS = {
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "Upgrade-Insecure-Requests": "1",
}


def _is_cloudflare_page(html: str) -> bool:
    markers = ["cf-browser-verification", "Checking your browser", "Just a moment"]
    return any(m in html for m in markers)


def _is_login_wall(url: str) -> bool:
    return "/register" in url or "/login" in url


async def _fetch(page: Page, url: str) -> str:
    delays = [2, 4, 8]
    last_exc: Exception = CloudflareError("unreachable")

    for attempt, delay in enumerate([0] + delays):
        if delay:
            await asyncio.sleep(delay)

        response: Response | None = await page.goto(url, wait_until="domcontentloaded", timeout=30_000)

        final_url = page.url
        if _is_login_wall(final_url):
            raise LoginWallError(final_url)

        if response and response.status == 429:
            last_exc = RateLimitError(f"429 on attempt {attempt + 1}")
            continue

        html = await page.content()

        if response and response.status == 403:
            last_exc = CloudflareError(f"403 on attempt {attempt + 1}")
            continue

        if _is_cloudflare_page(html):
            last_exc = CloudflareError(f"JS challenge on attempt {attempt + 1}")
            continue

        return html

    raise last_exc


_STEALTH = Stealth(
    navigator_platform_override="MacIntel",
    navigator_user_agent_override=_USER_AGENT,
)


@asynccontextmanager
async def browser_session():
    async with _STEALTH.use_async(async_playwright()) as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = await browser.new_context(
            user_agent=_USER_AGENT,
            extra_http_headers=_EXTRA_HEADERS,
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        page = await context.new_page()
        try:
            yield page
        finally:
            await browser.close()


async def fetch_page(url: str) -> str:
    async with browser_session() as page:
        return await _fetch(page, url)
