import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import admin as admin_api
from api import chat as chat_api
from config import settings
from services.database import init_db
from services.events import bus
from websocket import admin as admin_ws
from websocket import voice as voice_ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    bus.bind_loop(asyncio.get_running_loop())
    yield


app = FastAPI(title="Refund Agent", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chat_api.router)
app.include_router(admin_api.router)
app.include_router(admin_ws.router)
app.include_router(voice_ws.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
