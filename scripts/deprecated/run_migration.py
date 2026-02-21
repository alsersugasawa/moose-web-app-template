import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
import os

async def run_migration():
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/webapp"
    )

    engine = create_async_engine(DATABASE_URL)

    # Read migration SQL
    with open('migrations/001_add_tree_views.sql', 'r') as f:
        sql = f.read()

    # Split by semicolon and execute each statement
    statements = [s.strip() for s in sql.split(';') if s.strip()]

    async with engine.begin() as conn:
        for statement in statements:
            print(f"Executing: {statement[:50]}...")
            await conn.execute(statement)
            print("✓ Success")

    await engine.dispose()
    print("\n✅ Migration completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_migration())
