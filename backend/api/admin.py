from fastapi import APIRouter

from services.events import bus

router = APIRouter(prefix="/api/admin")


@router.get("/events")
def recent_events(limit: int = 200) -> list[dict]:
    return bus.recent(limit)


@router.get("/events/{session_id}")
def session_events(session_id: str) -> list[dict]:
    return bus.history(session_id)
