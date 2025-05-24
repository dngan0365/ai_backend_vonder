import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.prisma_client import initialize_prisma, close_prisma
from app.auth.router import router as auth_router
from app.chatbot.router import router as chatbot_router
from app.dashboard.router import router as dashboard_router
from dotenv import load_dotenv
import os
# Load environment variables from the .env file
load_dotenv()

# Get the frontend URL from the environment variable
frontend_url = os.getenv('FRONTEND_URL')

# Add CORS middleware with the URL from .env
origins = [frontend_url]  # Allow the specific frontend URL

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="API for Travel Chatbot and Analytics Dashboard",
    version="1.0.0"
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix='/ai')
app.include_router(chatbot_router, prefix='/ai')
app.include_router(dashboard_router, prefix='/ai')

# Startup event
@app.on_event("startup")
async def startup():
    await initialize_prisma()

# Shutdown event
@app.on_event("shutdown")
async def shutdown():
    await close_prisma()

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to Travel Chatbot & Dashboard API"}