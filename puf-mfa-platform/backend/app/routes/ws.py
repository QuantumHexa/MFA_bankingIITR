from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from app.config import settings
from app.services.event_bus import auth_events
from app.services.auth_service import ALGORITHM

router = APIRouter()


@router.websocket("/ws/auth")
async def auth_flow_ws(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token") or websocket.cookies.get(settings.access_cookie_name)
    if not token:
        await websocket.close(code=4401)
        return
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            await websocket.close(code=4401)
            return
    except JWTError:
        await websocket.close(code=4401)
        return

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
