"""
Example plugin router.

Registers one public endpoint to verify the plugin system is working:
  GET /api/plugins/example/ping → {"pong": true, "plugin": "example"}
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/plugins/example", tags=["plugins"])


@router.get("/ping")
async def ping():
    """Health-check for the example plugin."""
    return {"pong": True, "plugin": "example"}
