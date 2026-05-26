import asyncio
import json
from datetime import datetime
from typing import Any

from fastapi import WebSocket


class AuthEventBus:
    """Broadcasts live authentication flow events to connected WebSocket clients."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, event: str, data: dict[str, Any]) -> None:
        message = json.dumps(
            {
                "event": event,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "data": data,
            }
        )
        dead: list[WebSocket] = []
        async with self._lock:
            targets = list(self._connections)

        for ws in targets:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.discard(ws)

    def emit_sync(self, event: str, data: dict[str, Any]) -> None:
        """Fire-and-forget from sync route handlers."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(event, data))
        except RuntimeError:
            pass


auth_events = AuthEventBus()
