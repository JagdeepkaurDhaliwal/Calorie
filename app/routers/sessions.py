from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Session as WorkoutSession, User
from app.schemas import (
    ReadingIn,
    SessionStartRequest,
    SessionStartResponse,
    SessionSummary,
    SessionUpdate,
)
from app.security import decode_jwt, get_current_user
from app.services.session_service import (
    add_reading,
    finish_session,
    get_owned_active_session,
    start_session,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/start", response_model=SessionStartResponse, status_code=status.HTTP_201_CREATED)
def start(
    payload: SessionStartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = start_session(db, current_user, payload.body_temp)
    return SessionStartResponse(session_id=session.id, started_at=session.started_at)


@router.post("/{session_id}/readings", response_model=SessionUpdate)
def post_reading(
    session_id: int,
    payload: ReadingIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = get_owned_active_session(db, current_user, session_id)
    update = add_reading(db, current_user, session, payload.heart_rate, payload.interval_sec)
    return SessionUpdate(**update)


@router.post("/{session_id}/end", response_model=SessionSummary)
def end(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = get_owned_active_session(db, current_user, session_id)
    summary_data = finish_session(db, current_user, session)
    return SessionSummary(**summary_data)


@router.websocket("/{session_id}/stream")
async def websocket_stream(
    ws: WebSocket,
    session_id: int,
    token: str | None = None,
    db: Session = Depends(get_db),
):
    if not token:
        await ws.close(code=4401, reason="Missing token")
        return

    try:
        payload = decode_jwt(token)
        user_id = int(payload["sub"])
    except Exception:
        await ws.close(code=4401, reason="Invalid token")
        return

    user = db.get(User, user_id)
    if not user:
        await ws.close(code=4401, reason="User not found")
        return

    session_row = db.query(WorkoutSession).filter(WorkoutSession.id == session_id).first()
    if not session_row:
        await ws.close(code=4404, reason="Session not found")
        return
    if session_row.user_id != user.id:
        await ws.close(code=4403, reason="Forbidden")
        return
    if session_row.status != "active":
        await ws.close(code=4409, reason="Session already ended")
        return

    await ws.accept()
    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type")
            if msg_type == "reading":
                hr = data.get("heart_rate")
                interval = data.get("interval_sec", 5)
                if hr is None or not (40 <= hr <= 220):
                    await ws.send_json(
                        {
                            "type": "error",
                            "code": "INVALID_READING",
                            "message": "heart_rate must be between 40 and 220 bpm",
                        }
                    )
                    continue
                update = add_reading(
                    db,
                    user,
                    session_row,
                    heart_rate=int(hr),
                    interval_sec=int(interval),
                )
                await ws.send_json({"type": "update", **update})
            elif msg_type == "end":
                summary_data = finish_session(db, user, session_row)
                await ws.send_json({"type": "summary", **summary_data})
                await ws.close()
                break
            else:
                await ws.send_json(
                    {
                        "type": "error",
                        "code": "BAD_MESSAGE",
                        "message": f"Unknown message type '{msg_type}'",
                    }
                )
    except WebSocketDisconnect:
        pass
