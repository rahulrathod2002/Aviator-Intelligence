from __future__ import annotations

import asyncio
import json
from contextlib import suppress

import websockets
from websockets.server import WebSocketServerProtocol

from backend.config import settings
from backend.logging_config import logger
from backend.ocr.engine import OcrEngine
from backend.services.state_engine import RoundStateEngine
from backend.sources.manager import SourceManager
from backend.storage.csv_store import CsvRoundStore


class AviatorBackend:
    def __init__(self) -> None:
        self._store = CsvRoundStore()
        history = self._store.load_recent(settings.recent_round_limit)
        self._state_engine = RoundStateEngine(self._store, history)
        self._ocr = OcrEngine()
        self._sources = SourceManager()
        self._frame_queue: asyncio.Queue = asyncio.Queue(maxsize=settings.frame_queue_size)
        self._clients: set[WebSocketServerProtocol] = set()
        self._server = None
        self._running = True

    async def run(self) -> None:
        self._server = await websockets.serve(
            self._ws_handler,
            settings.websocket_host,
            settings.websocket_port,
            ping_interval=20,
            ping_timeout=20,
        )
        logger.info("websocket server listening on %s:%s", settings.websocket_host, settings.websocket_port)
        producer = asyncio.create_task(self._producer())
        consumer = asyncio.create_task(self._consumer())
        try:
            await asyncio.gather(producer, consumer)
        finally:
            self._running = False
            producer.cancel()
            consumer.cancel()
            with suppress(Exception):
                await producer
            with suppress(Exception):
                await consumer
            await self._sources.close()
            self._server.close()
            await self._server.wait_closed()

    async def _producer(self) -> None:
        while self._running:
            frame = await self._sources.next_frame()
            if frame is None:
                snapshot = self._state_engine.snapshot(self._sources.current_status)
                await self._broadcast(snapshot.to_dict())
                continue
            if self._frame_queue.full():
                _ = self._frame_queue.get_nowait()
                self._frame_queue.task_done()
            await self._frame_queue.put(frame)

    async def _consumer(self) -> None:
        while self._running:
            frame = await self._frame_queue.get()
            try:
                observation = self._ocr.extract(frame.image_bytes, frame.source)
                snapshot = self._state_engine.apply(observation, self._sources.current_status)
                await self._broadcast(snapshot.to_dict())
            except Exception as error:
                logger.exception("processing failed: %s", error)
            finally:
                self._frame_queue.task_done()

    async def _broadcast(self, payload: dict) -> None:
        if not self._clients:
            return
        message = json.dumps(payload)
        disconnected: list[WebSocketServerProtocol] = []
        for client in self._clients:
            try:
                await client.send(message)
            except Exception:
                disconnected.append(client)
        for client in disconnected:
            self._clients.discard(client)

    async def _ws_handler(self, websocket: WebSocketServerProtocol) -> None:
        self._clients.add(websocket)
        await websocket.send(json.dumps(self._state_engine.snapshot(self._sources.current_status).to_dict()))
        try:
            await websocket.wait_closed()
        finally:
            self._clients.discard(websocket)
