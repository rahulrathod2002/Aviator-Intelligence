from __future__ import annotations

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from backend.config import settings


class BrowserFrameSource:
    name = "BROWSER"

    def __init__(self) -> None:
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    async def is_available(self) -> bool:
        try:
            await self._ensure_page()
            return True
        except Exception:
            await self.close()
            return False

    async def capture_frame(self) -> bytes:
        page = await self._ensure_page()
        await page.wait_for_timeout(40)
        return await page.screenshot(type="png", full_page=False)

    async def _ensure_page(self) -> Page:
        if self._page and not self._page.is_closed():
            return self._page
        self._playwright = await async_playwright().start()
        browser_type = self._playwright.chromium
        try:
            self._browser = await browser_type.launch(channel="chrome", headless=True)
        except Exception:
            self._browser = await browser_type.launch(headless=True)
        self._context = await self._browser.new_context(
            viewport={"width": settings.browser_width, "height": settings.browser_height}
        )
        self._page = await self._context.new_page()
        await self._page.goto(settings.browser_url, wait_until="domcontentloaded", timeout=45000)
        await self._page.wait_for_timeout(2500)
        return self._page

    async def close(self) -> None:
        if self._page and not self._page.is_closed():
            await self._page.close()
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None
