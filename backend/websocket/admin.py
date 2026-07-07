import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.events import bus

router = APIRouter()


@router.websocket("/ws/admin")
async def admin_ws(ws: WebSocket):
    await ws.accept()
    for event in bus.recent():
        await ws.send_json(event)
    queue = bus.subscribe()
    try:
        while True:
            event = await queue.get()
            await ws.send_json(event)
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        bus.unsubscribe(queue)
