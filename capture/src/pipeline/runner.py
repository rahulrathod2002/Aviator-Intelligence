from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
import time
from typing import Deque
from collections import deque
from enum import Enum

import aiohttp
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
        self._last_roi_attempt = 0.0
        self._last_roi_scan = 0.0
        self._groq_key: str | None = None
        self._ai_inflight = False
        self._ai_last_sent = 0.0
        self._ai_values: Deque[float] = deque(maxlen=120)
        
        # State machine
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
                packet = FramePacket(
                    timestamp=timestamp,
                    image_bytes=frame,
                )
                if self._frame_queue.full():
                    _ = self._frame_queue.get_nowait()
                    self._frame_queue.task_done()
                await self._frame_queue.put(packet)
                await asyncio.sleep(config.poll_interval_ms / 1000)
            except Exception as error:
                logger.warning("capture loop error: %s", error)
                await asyncio.sleep(2)

    def _update_state(self, multiplier: float, confidence: float, color: str = "white") -> None:
        prev_state = self._state
        now = time.time()

        # COLOR TRIGGER: Red text always means CRASHED
        if color == "red":
            if self._state != GameState.CRASHED:
                self._state = GameState.CRASHED
                self._current_round_max = multiplier
                logger.info("COLOR CRASH DETECTED: %sx", multiplier)
                if multiplier > 1.01:
                    self._round_history.append(multiplier)
                    self._ai_values.append(multiplier)
            return

        # STALL TRIGGER: If multiplier doesn't change for 2 seconds while flying, it's likely crashed/idle
        if self._state == GameState.FLYING and abs(multiplier - self._current_round_max) < 0.001:
            if now - self._last_state_change > 2.0:
                logger.warning("STALL DETECTED at %sx, forcing CRASHED state", multiplier)
                self._state = GameState.CRASHED
                if multiplier > 1.01:
                    self._round_history.append(multiplier)
                    self._ai_values.append(multiplier)
                return

        # SELF-HEALING: If stuck in any non-idle state for too long without change, reset
        if self._state != GameState.IDLE and now - self._last_state_change > 45.0:
            logger.error("STUCK STATE DETECTED (%s for 45s), forcing IDLE reset", self._state.value)
            self._state = GameState.IDLE
            self._current_round_max = 1.0
            self._recent_values.clear()
            return

        # RESET TRIGGER: White text at 1.00x or significant drop means new round/waiting
        if color == "white":
            if multiplier <= 1.01 or (self._state == GameState.FLYING and multiplier < self._current_round_max * 0.5):
                if self._state != GameState.WAITING:
                    logger.info("ROUND RESET/WAITING DETECTED (multiplier: %s)", multiplier)
                    self._state = GameState.WAITING
                    self._current_round_max = 1.0
                return

        # FLYING TRIGGER: White text and increasing
        if color == "white" and multiplier > self._current_round_max + 0.001:
            self._state = GameState.FLYING
            self._current_round_max = multiplier

        if self._state != prev_state:
            self._last_state_change = now
            logger.info("State: %s -> %s (val: %s, col: %s)", prev_state.value, self._state.value, multiplier, color)

    async def _consumer(self) -> None:
        while self._running:
            packet = await self._frame_queue.get()
            try:
                now = time.time()
                
                # Auto ROI scan if needed
                if now - self._last_roi_scan > config.auto_roi_scan_sec:
                    self._last_roi_scan = now
                    roi = self._ocr_engine.locate_multiplier_roi(packet.image_bytes)
                    if roi:
                        config.roi_x, config.roi_y, config.roi_width, config.roi_height = roi
                        logger.info("auto ROI scan updated to x=%s y=%s w=%s h=%s", *roi)

                result = self._ocr_engine.extract(packet.image_bytes)
                
                if result.multiplier is None:
                    # If we were flying and lost OCR, we might have crashed or just have a bad frame
                    if self._state == GameState.FLYING and now - self._last_state_change > 3.0:
                         self._state = GameState.IDLE
                    continue

                candidate = result.multiplier
                if candidate < 1 or candidate > config.max_multiplier:
                    continue

                # State management with color trigger
                self._update_state(candidate, result.confidence, result.color)

                # Broadcast rounds count update
                if self._state in (GameState.WAITING, GameState.CRASHED):
                    await self._broadcast({
                        "type": "rounds_count",
                        "count": len(self._ai_values),
                        "required": 5
                    })

                # Smoothing logic (only when flying)
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
                    "history": self._round_history[-10:] # Last 10 rounds
                }

                await self._broadcast(message)
                await self._maybe_trigger_ai()
                
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
            async for message in websocket:
                try:
                    payload = json.loads(message)
                except json.JSONDecodeError:
                    continue
                if payload.get("type") == "groq_key":
                    key = str(payload.get("key", "")).strip()
                    self._groq_key = key if key else None
                    logger.info("groq key %s", "set" if self._groq_key else "cleared")
        finally:
            self._clients.discard(websocket)

    async def run(self) -> None:
        await self._init_device()
        await websockets.serve(self._ws_handler, config.ws_host, config.ws_port)
        logger.info("websocket server listening on %s:%s", config.ws_host, config.ws_port)
        await asyncio.gather(self._producer(), self._consumer())

    async def _maybe_trigger_ai(self) -> None:
        if not self._groq_key:
            return
        if self._ai_inflight:
            return
        if len(self._ai_values) < 5: 
            return
        now = time.time()
        # Trigger AI on round end, crash, or after a long delay
        if self._state in (GameState.WAITING, GameState.CRASHED) and now - self._ai_last_sent > 3:
            self._ai_inflight = True
            self._ai_last_sent = now
            asyncio.create_task(self._fetch_groq_insight(list(self._ai_values)))

    async def _fetch_groq_insight(self, values: list[float]) -> None:
        payload = {
            "recent_multipliers": values[-50:],
            "volatility": float(np.std(values[-50:])) if len(values) >= 2 else 0.0,
        }
        prompt = (
            "Analyze Aviator game multipliers. Data: " + json.dumps(payload) + 
            "\nReturn JSON: {signal_strength: 'low'|'medium'|'high', insight: 'string', next_round_prob: 'string'}"
        )
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self._groq_key}",
                    },
                    json={
                        "model": "llama-3.1-8b-instant",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.4,
                        "max_tokens": 150,
                    },
                    timeout=10,
                ) as response:
                    if response.status != 200:
                        return
                    data = await response.json()
        except Exception as error:
            logger.warning("groq request failed: %s", error)
            return
        finally:
            self._ai_inflight = False
        
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if "```" in content:
            match = re.search(r"```(?:json)?(.*?)```", content, re.DOTALL)
            if match: content = match.group(1).strip()

        try:
            insight = json.loads(content)
        except Exception:
            return
        
        await self._broadcast({
            "type": "ai_insight",
            "value": insight,
            "timestamp": int(time.time() * 1000),
        })

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
            async for message in websocket:
                try:
                    payload = json.loads(message)
                except json.JSONDecodeError:
                    continue
                if payload.get("type") == "groq_key":
                    key = str(payload.get("key", "")).strip()
                    self._groq_key = key if key else None
                    logger.info("groq key %s", "set" if self._groq_key else "cleared")
        finally:
            self._clients.discard(websocket)

    def _auto_calibrate_roi(self, frame: np.ndarray) -> None:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return
        best = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(best)
        pad = 10
        config.roi_x = max(0, x - pad)
        config.roi_y = max(0, y - pad)
        config.roi_width = min(frame.shape[1] - config.roi_x, w + pad * 2)
        config.roi_height = min(frame.shape[0] - config.roi_y, h + pad * 2)

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

    async def run(self) -> None:
        await self._init_device()
        await websockets.serve(self._ws_handler, config.ws_host, config.ws_port)
        logger.info("websocket server listening on %s:%s", config.ws_host, config.ws_port)
        await asyncio.gather(self._producer(), self._consumer())

    async def _maybe_trigger_ai(self) -> None:
        if not self._groq_key:
            return
        if self._ai_inflight:
            return
        if len(self._ai_values) < 20:
            return
        now = time.time()
        if now - self._ai_last_sent < 8:
            return
        self._ai_inflight = True
        self._ai_last_sent = now
        asyncio.create_task(self._fetch_groq_insight(list(self._ai_values)))

    async def _fetch_groq_insight(self, values: list[float]) -> None:
        payload = {
            "recent_multipliers": values[-100:],
            "volatility": float(np.std(values[-100:])) if len(values) >= 2 else 0.0,
            "streak": 0,
        }
        prompt = (
            "You are an analytics assistant. Analyze crash game multipliers for probabilistic insight only. "
            "Return JSON with: signal_strength (low|medium|high), market_phase (stable|volatile|chaotic), "
            "insight (short), confidence (0-1), range_estimate ([low, high]). "
            "Do NOT predict guaranteed results.\n\nData:\n"
            + json.dumps(payload)
        )
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self._groq_key}",
                    },
                    json={
                        "model": "llama-3.1-8b-instant",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.4,
                        "max_tokens": 200,
                    },
                    timeout=12,
                ) as response:
                    if response.status != 200:
                        return
                    data = await response.json()
        except Exception as error:
            logger.warning("groq request failed: %s", error)
            return
        finally:
            self._ai_inflight = False
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Clean markdown code blocks if present
        if "```" in content:
            match = re.search(r"```(?:json)?(.*?)```", content, re.DOTALL)
            if match:
                content = match.group(1).strip()

        try:
            insight = json.loads(content)
        except Exception:
            return
        insight_message = {
            "type": "ai_insight",
            "value": insight,
            "timestamp": int(time.time() * 1000),
        }
        await self._broadcast(insight_message)
