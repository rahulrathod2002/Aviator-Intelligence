from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import time
from typing import Deque
from collections import deque
from enum import Enum

import cv2
import numpy as np
import websockets

from src.adb_capture.client import AdbClient
from src.ocr.engine import OcrEngine
from src.utils.config import config
from src.utils.logger import logger


class GameState(Enum):
    IDLE = "idle"
    WAITING = "waiting"
    FLYING = "flying"
    CRASHED = "crashed"


@dataclass(slots=True)
class FramePacket:
    timestamp: str
    image_bytes: bytes


class CaptureRunner:
    def __init__(self) -> None:
        self._adb_client = AdbClient()
        self._ocr_engine = OcrEngine()
        self._frame_queue: asyncio.Queue[FramePacket] = asyncio.Queue(maxsize=3)
        self._running = True
        self._last_valid_multiplier: float | None = None
        self._device_id: str = "unknown-device"
        self._game_activity: str = "unknown-activity"
        self._last_no_ocr_log = 0.0
        self._recent_values: Deque[float] = deque(maxlen=config.smoothing_window)
        self._clients: set[websockets.WebSocketServerProtocol] = set()
        self._last_debug_dump = 0.0
        self._last_roi_scan = 0.0

        self._state = GameState.IDLE
        self._last_state_change = time.time()
        self._current_round_max = 1.0
        self._round_history: list[float] = []

    async def _init_device(self) -> None:
        detected = await self._adb_client.discover_single_device()
        if detected and config.device_id != detected:
            config.device_id = detected
        self._device_id = await self._adb_client.get_device_id()
        self._game_activity = await self._adb_client.get_foreground_activity()

    async def _producer(self) -> None:
        while self._running:
            try:
                frame = await self._adb_client.capture_frame()
                timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
                packet = FramePacket(timestamp=timestamp, image_bytes=frame)
                if self._frame_queue.full():
                    _ = self._frame_queue.get_nowait()
                    self._frame_queue.task_done()
                await self._frame_queue.put(packet)
                await asyncio.sleep(config.poll_interval_ms / 1000)
            except Exception as error:
                logger.warning("capture loop error: %s", error)
                await asyncio.sleep(2)

    def _update_state(self, multiplier: float, color: str) -> None:
        prev_state = self._state
        now = time.time()

        if color == "red":
            if self._state != GameState.CRASHED:
                self._state = GameState.CRASHED
                self._current_round_max = max(self._current_round_max, multiplier)
                if self._current_round_max > 1.01:
                    self._round_history.append(self._current_round_max)
            self._last_state_change = now
            return

        if self._state == GameState.FLYING and abs(multiplier - self._current_round_max) < 0.001:
            if now - self._last_state_change > 2.0:
                self._state = GameState.CRASHED
                self._current_round_max = max(self._current_round_max, multiplier)
                if self._current_round_max > 1.01:
                    self._round_history.append(self._current_round_max)
                self._last_state_change = now
                return

        if self._state != GameState.IDLE and now - self._last_state_change > 45.0:
            self._state = GameState.IDLE
            self._current_round_max = 1.0
            self._recent_values.clear()
            self._last_state_change = now
            return

        if multiplier <= 1.01:
            if self._state != GameState.WAITING:
                self._state = GameState.WAITING
                self._current_round_max = 1.0
                self._last_state_change = now
            return

        if multiplier > self._current_round_max + 0.001:
            self._state = GameState.FLYING
            self._current_round_max = multiplier

        if self._state != prev_state:
            self._last_state_change = now

    async def _consumer(self) -> None:
        while self._running:
            packet = await self._frame_queue.get()
            try:
                now = time.time()
                if now - self._last_roi_scan > config.auto_roi_scan_sec:
                    self._last_roi_scan = now
                    roi = self._ocr_engine.locate_multiplier_roi(packet.image_bytes)
                    if roi:
                        config.roi_x, config.roi_y, config.roi_width, config.roi_height = roi
                        logger.info("auto ROI scan updated to x=%s y=%s w=%s h=%s", *roi)

                if config.debug_roi:
                    frame_np = cv2.imdecode(np.frombuffer(packet.image_bytes, np.uint8), cv2.IMREAD_COLOR)
                    if frame_np is not None:
                        self._debug_dump_roi(frame_np)

                result = self._ocr_engine.extract(packet.image_bytes)
                if result.multiplier is None:
                    if now - self._last_no_ocr_log > 5:
                        self._last_no_ocr_log = now
                        logger.warning(
                            "no multiplier detected (ROI x=%s y=%s w=%s h=%s)",
                            config.roi_x,
                            config.roi_y,
                            config.roi_width,
                            config.roi_height,
                        )
                    continue

                candidate = result.multiplier
                if candidate < 1 or candidate > config.max_multiplier:
                    continue

                self._update_state(candidate, result.color)

                if self._state == GameState.FLYING:
                    self._recent_values.append(candidate)
                    if len(self._recent_values) >= 3:
                        smoothed = float(np.median(np.array(self._recent_values)))
                    else:
                        smoothed = candidate
                else:
                    smoothed = candidate
                    self._recent_values.clear()

                self._last_valid_multiplier = smoothed

                message = {
                    "type": "multiplier",
                    "value": round(smoothed, 2),
                    "confidence": round(result.confidence, 4),
                    "state": self._state.value,
                    "roundMax": round(self._current_round_max, 2),
                    "timestamp": int(time.time() * 1000),
                    "deviceId": self._device_id,
                    "rawText": result.raw_text,
                    "engine": result.engine,
                    "roi": {
                        "x": config.roi_x,
                        "y": config.roi_y,
                        "w": config.roi_width,
                        "h": config.roi_height,
                    },
                    "history": self._round_history[-10:],
                }

                await self._broadcast(message)
                logger.info("broadcast multiplier=%s confidence=%.3f", smoothed, result.confidence)
            except Exception as error:
                logger.warning("consumer error: %s", error)
            finally:
                self._frame_queue.task_done()

    async def _broadcast(self, message: dict) -> None:
        if not self._clients:
            return
        payload = json.dumps(message)
        disconnected = []
        for client in self._clients:
            try:
                await client.send(payload)
            except Exception:
                disconnected.append(client)
        for client in disconnected:
            self._clients.discard(client)

    async def _ws_handler(self, websocket: websockets.WebSocketServerProtocol) -> None:
        self._clients.add(websocket)
        try:
            await websocket.wait_closed()
        finally:
            self._clients.discard(websocket)

    async def run(self) -> None:
        await self._init_device()
        await self._start_ws_server()
        await asyncio.gather(self._producer(), self._consumer())

    async def _start_ws_server(self) -> None:
        port = config.ws_port
        for _ in range(5):
            try:
                await websockets.serve(self._ws_handler, config.ws_host, port)
                config.ws_port = port
                logger.info("websocket server listening on %s:%s", config.ws_host, port)
                return
            except OSError as error:
                if getattr(error, "errno", None) == 10048:
                    port += 1
                    continue
                raise
        raise RuntimeError("unable to bind websocket server after retries")

    def _debug_dump_roi(self, frame: np.ndarray) -> None:
        now = time.time()
        if now - self._last_debug_dump < config.debug_roi_interval_sec:
            return
        self._last_debug_dump = now
        overlay = frame.copy()
        cv2.rectangle(
            overlay,
            (config.roi_x, config.roi_y),
            (config.roi_x + config.roi_width, config.roi_y + config.roi_height),
            (0, 255, 0),
            2,
        )
        cv2.imwrite("aviator_roi_debug.png", overlay)
