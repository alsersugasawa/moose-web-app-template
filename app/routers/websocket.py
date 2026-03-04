"""
WebSocket endpoints (Phase 4).

  WS /ws/admin/stats       — live system stats stream (admin only)
  WS /ws/notifications     — per-user notification channel (any authenticated user)

Authentication
--------------
WebSocket connections cannot send custom HTTP headers, so the JWT is passed
as a query parameter:  ?token=<jwt>

The connection is closed with code 4001 on auth failure.

Admin stats stream
------------------
Sends a JSON snapshot every 5 seconds:
    {
      "cpu_percent":    <float>,
      "memory_percent": <float>,
      "disk_percent":   <float>,
      "cpu_cores":      <int>,
      "memory_total":   <str>,
      "disk_total":     <str>,
      "active_admins":  <int>,
      "active_users":   <int>,
      "timestamp":      <str ISO-8601>
    }

Notification channel
--------------------
On connect, sends:
    {"type": "connected", "user_id": <int>}

Subsequent messages are pushed by server-side code via ws_manager.send_to_user().
"""

import asyncio
import logging
import psutil
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.ws_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websockets"])


# ── Auth helper ───────────────────────────────────────────────────────────────

async def _get_user_from_token(token: str):
    """Validate a JWT and return the User ORM object, or None on failure."""
    try:
        from jose import JWTError, jwt
        from sqlalchemy import select
        from app.auth import SECRET_KEY, ALGORITHM
        from app.database import async_session_maker
        from app.models import User, UserSession

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        jti: str = payload.get("jti")
        if not username:
            return None

        async with async_session_maker() as db:
            result = await db.execute(select(User).where(User.username == username))
            user = result.scalar_one_or_none()
            if not user or not user.is_active:
                return None
            # Check session not revoked
            if jti:
                import uuid as _uuid
                sess_result = await db.execute(
                    select(UserSession).where(
                        UserSession.jti == _uuid.UUID(jti),
                        UserSession.is_revoked == False,  # noqa: E712
                    )
                )
                if sess_result.scalar_one_or_none() is None:
                    return None
            return user
    except Exception:
        return None


def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


# ── Admin stats stream ────────────────────────────────────────────────────────

@router.websocket("/ws/admin/stats")
async def admin_stats_ws(websocket: WebSocket, token: str = Query(...)):
    user = await _get_user_from_token(token)
    if user is None or not user.is_admin:
        await websocket.close(code=4001)
        return

    ws_id = await ws_manager.connect_admin(websocket)
    try:
        while True:
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            payload = {
                "cpu_percent":    psutil.cpu_percent(interval=None),
                "memory_percent": mem.percent,
                "disk_percent":   disk.percent,
                "cpu_cores":      psutil.cpu_count(logical=True),
                "memory_total":   _fmt_bytes(mem.total),
                "disk_total":     _fmt_bytes(disk.total),
                "active_admins":  ws_manager.admin_count,
                "active_users":   ws_manager.user_count,
                "timestamp":      datetime.now(timezone.utc).isoformat(),
            }
            await websocket.send_json(payload)
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.debug("[ws] admin_stats_ws error: %s", exc)
    finally:
        ws_manager.disconnect_admin(ws_id)


# ── User notification channel ─────────────────────────────────────────────────

@router.websocket("/ws/notifications")
async def notifications_ws(websocket: WebSocket, token: str = Query(...)):
    user = await _get_user_from_token(token)
    if user is None:
        await websocket.close(code=4001)
        return

    await ws_manager.connect_user(user.id, websocket)
    try:
        await websocket.send_json({"type": "connected", "user_id": user.id})
        # Keep connection alive; server pushes messages via ws_manager.send_to_user()
        while True:
            # Ping every 30 s to detect dead connections
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.debug("[ws] notifications_ws error user_id=%d: %s", user.id, exc)
    finally:
        ws_manager.disconnect_user(user.id, websocket)
