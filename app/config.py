from contextlib import asynccontextmanager
from prisma import Prisma
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    OPENAI_API_KEY: str
    JWT_SECRET: str
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_CALLBACK_URL: str
    FRONTEND_URL: str
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str
    APP_NAME: str
    ENVIRONMENT: str

    class Config:
        env_file = ".env"  # Pydantic will automatically load variables from the .env file

# Create the settings object to access the variables
settings = Settings()
# Singleton pattern for Prisma client
prisma = Prisma()

async def initialize_prisma():
    """Initialize the Prisma Client"""
    await prisma.connect()

async def close_prisma():
    """Close the Prisma Client connection"""
    if prisma.is_connected():
        await prisma.disconnect()

@asynccontextmanager
async def get_prisma():
    """Context manager for Prisma client"""
    if not prisma.is_connected():
        await prisma.connect()
    try:
        yield prisma
    finally:
        # We don't disconnect here to reuse the connection
        pass