from fastapi import FastAPI
from app.dependencies import prisma
from app.routes import chat, title_chat

app = FastAPI()

@app.on_event("startup")
async def startup():
    await prisma.connect()

@app.on_event("shutdown")
async def shutdown():
    await prisma.disconnect()

app.include_router(chat.router, prefix="/api")
app.include_router(title_chat.router, prefix="/api")
