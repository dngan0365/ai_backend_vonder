from contextlib import asynccontextmanager
from prisma import Prisma

prisma = Prisma()

async def initialize_prisma():
    await prisma.connect()

async def close_prisma():
    if prisma.is_connected():
        await prisma.disconnect()

@asynccontextmanager
async def get_prisma():
    """Context manager for Prisma client with reconnection if needed"""
    if not prisma.is_connected():
        try:
            await prisma.connect()
        except Exception as e:
            print(f"[Prisma] Reconnection error: {e}")
            raise

    try:
        # Test connection with a lightweight query (optional, more reliable)
        await prisma.execute_raw('SELECT 1')
    except Exception as e:
        print(f"[Prisma] Lost connection, reconnecting...: {e}")
        await prisma.connect()

    try:
        yield prisma
    finally:
        # Keep the connection open for re-use
        pass
