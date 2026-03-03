"""
Scaffold CLI — generate boilerplate for new resources.

Usage:
    python -m scaffold router <name>

Example:
    python -m scaffold router widget

This creates:
  app/routers/widget.py         — stub CRUD router
  migrations/006_widget.sql     — stub SQL migration
  Appends schema stubs to app/schemas.py

After running:
  1. Apply the migration:
       docker exec webapp-db psql -U postgres -d webapp -f /tmp/006_widget.sql
  2. Register the router in app/main.py:
       from app.routers import widget as widget_router
       app.include_router(widget_router.router)
"""

import re
import sys
from pathlib import Path

from scaffold.templates import ROUTER_TEMPLATE, SCHEMA_STUB_TEMPLATE, MIGRATION_TEMPLATE

# Project root is the parent of the scaffold/ directory
ROOT = Path(__file__).parent.parent


def _next_migration_number() -> str:
    """Return the next zero-padded 3-digit migration number."""
    migrations_dir = ROOT / "migrations"
    existing = sorted(
        int(p.stem.split("_")[0])
        for p in migrations_dir.glob("*.sql")
        if p.stem[0].isdigit()
    )
    next_num = (max(existing) + 1) if existing else 1
    return f"{next_num:03d}"


def _validate_name(name: str) -> str:
    """Normalise and validate the resource name."""
    name = name.strip().lower().replace("-", "_")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        print(f"ERROR: '{name}' is not a valid Python identifier (use lowercase letters, digits, underscores).")
        sys.exit(1)
    return name


def scaffold_router(name: str) -> None:
    name = _validate_name(name)
    Name = name.title().replace("_", "")
    number = _next_migration_number()

    vars = {"name": name, "Name": Name, "number": number}

    # 1. Router file
    router_path = ROOT / "app" / "routers" / f"{name}.py"
    if router_path.exists():
        print(f"ERROR: {router_path.relative_to(ROOT)} already exists. Aborting.")
        sys.exit(1)
    router_path.write_text(ROUTER_TEMPLATE.substitute(vars), encoding="utf-8")
    print(f"  Created  {router_path.relative_to(ROOT)}")

    # 2. Migration file
    migration_path = ROOT / "migrations" / f"{number}_{name}.sql"
    if migration_path.exists():
        print(f"ERROR: {migration_path.relative_to(ROOT)} already exists. Aborting.")
        sys.exit(1)
    migration_path.write_text(MIGRATION_TEMPLATE.substitute(vars), encoding="utf-8")
    print(f"  Created  {migration_path.relative_to(ROOT)}")

    # 3. Append schema stubs
    schemas_path = ROOT / "app" / "schemas.py"
    stub = SCHEMA_STUB_TEMPLATE.substitute(vars)
    with schemas_path.open("a", encoding="utf-8") as f:
        f.write(stub)
    print(f"  Updated  {schemas_path.relative_to(ROOT)}")

    print()
    print("Next steps:")
    print(f"  1. Edit {router_path.relative_to(ROOT)} — implement your endpoints")
    print(f"  2. Edit {migration_path.relative_to(ROOT)} — add your columns")
    print(f"  3. Apply migration:")
    print(f"       docker cp {migration_path.relative_to(ROOT)} webapp-web:/tmp/")
    print(f"       docker exec webapp-db psql -U postgres -d webapp -f /tmp/{migration_path.name}")
    print(f"  4. Register in app/main.py:")
    print(f"       from app.routers import {name} as {name}_router")
    print(f"       app.include_router({name}_router.router)")


def main() -> None:
    args = sys.argv[1:]

    if not args:
        print(__doc__)
        sys.exit(0)

    subcommand = args[0].lower()

    if subcommand == "router":
        if len(args) < 2:
            print("Usage: python -m scaffold router <name>")
            sys.exit(1)
        scaffold_router(args[1])

    else:
        print(f"Unknown subcommand '{subcommand}'. Available: router")
        sys.exit(1)


if __name__ == "__main__":
    main()
