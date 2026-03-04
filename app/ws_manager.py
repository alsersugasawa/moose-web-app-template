"""
WebSocket connection manager (Phase 4).

Tracks active WebSocket connections for:
  - Admin stats stream  (one broadcast channel for all admin sessions)
  - Per-user notification channel  (keyed by user_id)

The singleton `ws_manager` is imported by the WebSocket router and by any
code that needs to push notifications to connected users.

Usage
-----
    from app.ws_manager import ws_manager

    # Push a notification to a specific user:
    await ws_manager.send_to_user(user_id, {"type": "notification", "message": "Hello"})

    # Broadcast a stats update to all connected admins:
    await ws_manager.broadcast_admin({"cpu_percent": 42.5, ...})
"""

import asyncio
import logging
import uuid
from collections import defaultdict
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        # admin_connections: {ws_id: WebSocket}
        self._admin: dict[str, WebSocket] = {}
        # user_connections: {user_id: [WebSocket, ...]}
        self._users: dict[int, list[WebSocket]] = defaultdict(list)

    # ── Admin channels ────────────────────────────────────────────────────────

    async def connect_admin(self, ws: WebSocket) -> str:
        """Accept connection and register it; returns the assigned ws_id."""
        await ws.accept()
        ws_id = str(uuid.uuid4())
        self._admin[ws_id] = ws
        logger.debug("[ws] admin connected ws_id=%s (total=%d)", ws_id, len(self._admin))
        return ws_id

    def disconnect_admin(self, ws_id: str) -> None:
        self._admin.pop(ws_id, None)
        logger.debug("[ws] admin disconnected ws_id=%s (remaining=%d)", ws_id, len(self._admin))

    async def broadcast_admin(self, data: dict) -> None:
        """Send *data* to every connected admin; silently removes stale connections."""
        dead: list[str] = []
        for ws_id, ws in list(self._admin.items()):
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws_id)
        for ws_id in dead:
            self._admin.pop(ws_id, None)

    # ── User channels ─────────────────────────────────────────────────────────

    async def connect_user(self, user_id: int, ws: WebSocket) -> None:
        """Accept connection and register it under *user_id*."""
        await ws.accept()
        self._users[user_id].append(ws)
        logger.debug("[ws] user %d connected (connections=%d)", user_id, len(self._users[user_id]))

    def disconnect_user(self, user_id: int, ws: WebSocket) -> None:
        conns = self._users.get(user_id, [])
        if ws in conns:
            conns.remove(ws)
        if not conns:
            self._users.pop(user_id, None)

    async def send_to_user(self, user_id: int, data: dict) -> None:
        """Send *data* to all active sessions for *user_id*."""
        dead: list[WebSocket] = []
        for ws in list(self._users.get(user_id, [])):
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect_user(user_id, ws)

    async def broadcast_users(self, data: dict) -> None:
        """Send *data* to every connected user (all sessions)."""
        tasks = [self.send_to_user(uid, data) for uid in list(self._users.keys())]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    # ── Diagnostics ───────────────────────────────────────────────────────────

    @property
    def admin_count(self) -> int:
        return len(self._admin)

    @property
    def user_count(self) -> int:
        return len(self._users)


# Module-level singleton
ws_manager = WebSocketManager()
