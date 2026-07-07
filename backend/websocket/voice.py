"""Voice pipeline: browser <-> backend <-> OpenAI Realtime API.

The backend relays Realtime events both ways so the API key never reaches the
browser. The Realtime session gets one tool, submit_refund_request, which runs
the same LangGraph agent as text chat — voice never bypasses policy enforcement.
Requires OPENAI_API_KEY; without it the socket reports voice as disabled.
"""

import asyncio
import json
import ssl

import certifi
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config import settings
from services.agent import run_turn

router = APIRouter()

VOICE_INSTRUCTIONS = (
    "You are a friendly e-commerce customer support voice agent handling refunds. "
    "Collect the customer's order id (format ORD-XXXX) and reason, then call "
    "submit_refund_request. Relay its decision to the customer clearly and briefly. "
    "Never promise a refund yourself; only the tool can decide."
)

REFUND_TOOL = {
    "type": "function",
    "name": "submit_refund_request",
    "description": "Submit the refund request for a policy decision. Returns the final decision.",
    "parameters": {
        "type": "object",
        "properties": {
            "order_id": {"type": "string", "description": "Order id, e.g. ORD-1001"},
            "reason": {"type": "string", "description": "Customer's reason for the refund"},
        },
        "required": ["order_id", "reason"],
    },
}


@router.websocket("/ws/voice")
async def voice_ws(ws: WebSocket, customer_id: str, session_id: str):
    await ws.accept()
    if not settings.openai_api_key:
        await ws.send_json({"type": "error",
                            "message": "Voice is disabled: OPENAI_API_KEY is not configured."})
        await ws.close()
        return

    import websockets

    url = f"wss://api.openai.com/v1/realtime?model={settings.realtime_model}"
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    # python.org builds don't wire the system trust store into stdlib ssl; use certifi's bundle.
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    async with websockets.connect(url, additional_headers=headers, max_size=1 << 24,
                                  ssl=ssl_ctx) as oai:
        await oai.send(json.dumps({
            "type": "session.update",
            "session": {
                "type": "realtime",
                "instructions": VOICE_INSTRUCTIONS,
                "output_modalities": ["audio"],
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcm", "rate": 24000},
                        "turn_detection": {"type": "server_vad"},
                    },
                    "output": {"format": {"type": "audio/pcm", "rate": 24000}},
                },
                "tools": [REFUND_TOOL],
                "tool_choice": "auto",
            },
        }))

        async def browser_to_openai():
            while True:
                await oai.send(await ws.receive_text())

        async def openai_to_browser():
            async for raw in oai:
                event = json.loads(raw)
                if event.get("type") == "response.function_call_arguments.done":
                    args = json.loads(event["arguments"])
                    message = (f"I want a refund for order {args.get('order_id', '')}. "
                               f"Reason: {args.get('reason', '')}")
                    view = await asyncio.to_thread(run_turn, session_id, customer_id, message)
                    await oai.send(json.dumps({
                        "type": "conversation.item.create",
                        "item": {
                            "type": "function_call_output",
                            "call_id": event["call_id"],
                            "output": json.dumps({
                                "decision": view.get("final_decision"),
                                "reason": view.get("decision_reason"),
                                "response": view.get("response"),
                            }),
                        },
                    }))
                    await oai.send(json.dumps({"type": "response.create"}))
                await ws.send_text(raw)

        try:
            await asyncio.gather(browser_to_openai(), openai_to_browser())
        except (WebSocketDisconnect, websockets.ConnectionClosed):
            pass
