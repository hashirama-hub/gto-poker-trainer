#!/usr/bin/env python3
"""Database setup script - run after PostgreSQL is configured."""
import asyncio
import asyncpg
import os

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

async def setup_database(dsn: str):
    conn = await asyncpg.connect(dsn)
    
    with open(SCHEMA_PATH) as f:
        schema = f.read()
    
    # Split by semicolon and execute each statement
    statements = [s.strip() for s in schema.split(';') if s.strip()]
    
    for stmt in statements:
        try:
            await conn.execute(stmt)
            print(f"✓ Executed: {stmt[:60]}...")
        except Exception as e:
            print(f"✗ Error: {e}")
            print(f"  Statement: {stmt[:100]}...")
    
    await conn.close()
    print("Database setup complete!")

if __name__ == "__main__":
    dsn = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/poker_trainer")
    asyncio.run(setup_database(dsn))
