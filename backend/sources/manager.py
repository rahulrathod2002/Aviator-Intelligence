from __future__ import annotations

import asyncio

from backend.config import settings
from backend.logging_config import logger
from backend.models import FrameEnvelope, SourceStatus, utc_now
from backend.sources.adb import AdbFrameSource
from backend.sources.browser import BrowserFrameSource


class SourceManager:
    def __init__(self) -> None:
        self._adb = AdbFrameSource()
        self._browser = BrowserFrameSource()
        self._current_status = SourceStatus.NO_SIGNAL

    @property
    def current_status(self) -> SourceStatus:
        return self._current_status

    async def next_frame(self) -> FrameEnvelope | None:
        for source, status in ((self._adb, SourceStatus.ADB), (self._browser, SourceStatus.BROWSER)):
            try:
                if not await source.is_available():
                    continue
                image_bytes = await source.capture_frame()
                self._current_status = status
                return FrameEnvelope(timestamp=utc_now(), image_bytes=image_bytes, source=source.name)
            except Exception as error:
                logger.warning("%s source failed: %s", source.name, error)
                if hasattr(source, "close"):
                    await source.close()
                continue
        self._current_status = SourceStatus.NO_SIGNAL
        await asyncio.sleep(settings.source_poll_interval)
        return None

    async def close(self) -> None:
        await self._browser.close()
