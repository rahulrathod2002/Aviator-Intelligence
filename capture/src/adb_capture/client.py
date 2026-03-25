import asyncio
from asyncio.subprocess import PIPE

from src.utils.config import config
from src.utils.logger import logger


class AdbClient:
    async def _run(self, *args: str, timeout: int = 5) -> tuple[int, bytes, bytes]:
        command = ["adb"]
        if config.device_id:
            command += ["-s", config.device_id]
        command += list(args)
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=PIPE,
                stderr=PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            return process.returncode, stdout, stderr
        except asyncio.TimeoutError:
            try:
                process.kill()
            except:
                pass
            return -1, b"", b"ADB command timed out"

    async def ensure_connected(self) -> None:
        code, stdout, stderr = await self._run("get-state")
        if code == 0 and stdout.decode().strip() == "device":
            return

        logger.warning("ADB device unavailable, attempting reconnect")
        reconnect = await asyncio.create_subprocess_exec("adb", "reconnect", stdout=PIPE, stderr=PIPE)
        await reconnect.communicate()

        code, stdout, stderr = await self._run("get-state")
        if code != 0 or stdout.decode().strip() != "device":
            raise ConnectionError(stderr.decode().strip() or "ADB reconnect failed")

    async def capture_frame(self) -> bytes:
        await self.ensure_connected()
        code, stdout, stderr = await self._run("exec-out", "screencap", "-p")
        if code != 0:
            raise RuntimeError(stderr.decode().strip() or "failed to capture screen")
        return stdout

    async def get_device_id(self) -> str:
        code, stdout, _stderr = await self._run("get-serialno")
        if code != 0:
            return "unknown-device"
        return stdout.decode().strip() or "unknown-device"

    async def discover_single_device(self) -> str | None:
        process = await asyncio.create_subprocess_exec(
            "adb",
            "devices",
            "-l",
            stdout=PIPE,
            stderr=PIPE,
        )
        stdout, _stderr = await process.communicate()
        lines = stdout.decode(errors="ignore").splitlines()
        devices = []
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])
        if len(devices) == 1:
            return devices[0]
        return None

    async def get_foreground_activity(self) -> str:
        code, stdout, _stderr = await self._run("shell", "dumpsys", "window", "windows")
        if code != 0:
            return "unknown-activity"
        text = stdout.decode(errors="ignore")
        for line in text.splitlines():
            if "mCurrentFocus" in line or "mFocusedApp" in line:
                return line.strip()
        return "unknown-activity"
