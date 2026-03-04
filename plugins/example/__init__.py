"""
Example plugin — demonstrates the plugin architecture pattern.

This plugin exposes a single `router` which the plugin loader picks up
and registers with the FastAPI app automatically.

To create your own plugin:
  1. Copy this directory to plugins/<your_plugin_name>/
  2. Add your routes to router.py (or directly below)
  3. Restart the application — the plugin is loaded automatically

No configuration required.
"""

from plugins.example.router import router

__all__ = ["router"]
