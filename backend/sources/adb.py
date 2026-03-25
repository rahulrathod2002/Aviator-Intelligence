from __future__ import annotations

import asyncio
import shutil
from asyncio.subprocess import PIPE


class AdbFrameSource:
    name = "ADB"

    def __init__(self) -> None:
        self._device_id: str | None = None

    async def is_available(self) -> bool:
        if shutil.which("adb") is None:
            return False
        code, stdout, _ = await self._run("devices")
        if code != 0:
            return False
        devices = [line for line in stdout.decode(errors="ignore").splitlines()[1:] if "\tdevice" in line]
        if not devices:
            return False
        self._device_id = devices[0].split()[0]
        return True

    async def capture_frame(self) -> bytes:
        code, stdout, stderr = await self._run("exec-out", "screencap", "-p")
        if code != 0 or not stdout:
            raise RuntimeError(stderr.decode(errors="ignore").strip() or "ADB screencap failed")
        return stdout

    async def _run(self, *args: str, timeout: int = 5) -> tuple[int, bytes, bytes]:
        command = ["adb"]
        if self._device_id:
            command.extend(["-s", self._device_id])
        command.extend(args)
        process = await asyncio.create_subprocess_exec(*command, stdout=PIPE, stderr=PIPE)
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            return -1, b"", b"ADB timeout"
        return process.returncode, stdout, stderr
