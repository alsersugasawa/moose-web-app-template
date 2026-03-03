"""
Plugin auto-loader for the Web Platform Template.

Drop a package into this directory and it will be registered automatically
on application startup. Each plugin package must contain an `__init__.py`.

Convention
----------
- If the package exposes a `router` attribute (a FastAPI APIRouter), it is
  included in the app automatically.
- Any SQLAlchemy models defined in the plugin are registered with the shared
  Base simply by being imported (they don't need special registration).

Example layout
--------------
    plugins/
        my_feature/
            __init__.py          # exposes `router`
            router.py            # defines the APIRouter
            models.py            # optional SQLAlchemy models

Usage in app/main.py
--------------------
    from plugins import load_plugins
    load_plugins(app)            # call AFTER all built-in routers are included
"""

import importlib
import pkgutil
from pathlib import Path

from fastapi import FastAPI


def load_plugins(app: FastAPI) -> list[str]:
    """
    Scan the plugins/ directory, import each sub-package, and register any
    FastAPI router found at the package's `router` attribute.

    Returns a list of loaded plugin names (useful for logging / tests).
    """
    loaded: list[str] = []
    plugins_dir = Path(__file__).parent

    for finder, name, is_pkg in pkgutil.iter_modules([str(plugins_dir)]):
        if not is_pkg:
            continue  # skip plain .py files at the plugins/ root

        module_path = f"plugins.{name}"
        try:
            module = importlib.import_module(module_path)
        except Exception as exc:  # pragma: no cover
            print(f"[plugins] WARNING: failed to load plugin '{name}': {exc}")
            continue

        router = getattr(module, "router", None)
        if router is not None:
            app.include_router(router)

        loaded.append(name)
        print(f"[plugins] Loaded plugin: {name}")

    return loaded
