from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.event_bus import auth_events

router = APIRouter()


@router.websocket("/ws/auth")
async def auth_flow_ws(websocket: WebSocket) -> None:
    await auth_events.connect(websocket)
    try:
        await websocket.send_json(
            {
                "event": "connected",
                "message": "PUF-MFA auth flow stream ready",
            }
        )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await auth_events.disconnect(websocket)
