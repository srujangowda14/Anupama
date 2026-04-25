import os
from typing import Any
from uuid import uuid4

from supabase import Client, create_client
from supabase.lib.client_options import ClientOptions


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        _client = create_client(
            SUPABASE_URL,
            SUPABASE_SERVICE_ROLE_KEY,
            options=ClientOptions(auto_refresh_token=False, persist_session=False),
        )
    return _client


def init_db() -> None:
    get_client()


def _single(table: str, filters: dict[str, Any]) -> dict[str, Any] | None:
    query = get_client().table(table).select("*")
    for key, value in filters.items():
        query = query.eq(key, value)
    data = query.limit(1).execute().data
    return data[0] if data else None


def upsert_profile(*, profile_id: str | None, name: str, email: str | None, timezone: str, goals: list[str], preferred_mode: str, now: str) -> dict[str, Any]:
    payload = {
        "id": profile_id or str(uuid4()),
        "name": name,
        "email": email,
        "timezone": timezone,
        "goals": goals,
        "preferred_mode": preferred_mode,
        "updated_at": now,
    }
    existing = get_profile(payload["id"])
    if existing:
        response = get_client().table("profiles").update(payload).eq("id", payload["id"]).execute()
    else:
        payload["created_at"] = now
        response = get_client().table("profiles").insert(payload).execute()
    return response.data[0]


def get_profile(profile_id: str) -> dict[str, Any] | None:
    return _single("profiles", {"id": profile_id})


def create_session(*, profile_id: str, mode: str, title: str | None, now: str) -> dict[str, Any]:
    payload = {
        "id": str(uuid4()),
        "profile_id": profile_id,
        "mode": mode,
        "title": title,
        "summary": None,
        "created_at": now,
        "updated_at": now,
    }
    return get_client().table("sessions").insert(payload).execute().data[0]


def get_session(session_id: str) -> dict[str, Any] | None:
    return _single("sessions", {"id": session_id})


def update_session_summary(session_id: str, summary: str, now: str) -> None:
    get_client().table("sessions").update({"summary": summary, "updated_at": now}).eq("id", session_id).execute()


def add_message(*, session_id: str, role: str, content: str, timestamp: str, mood_score: int | None = None, distortion: str | None = None, is_crisis: bool | None = None) -> dict[str, Any]:
    payload = {
        "id": str(uuid4()),
        "session_id": session_id,
        "role": role,
        "content": content,
        "timestamp": timestamp,
        "mood_score": mood_score,
        "distortion": distortion,
        "is_crisis": bool(is_crisis),
    }
    return get_client().table("messages").insert(payload).execute().data[0]


def list_session_messages(session_id: str) -> list[dict[str, Any]]:
    return (
        get_client()
        .table("messages")
        .select("*")
        .eq("session_id", session_id)
        .order("timestamp")
        .execute()
        .data
    )


def list_recent_sessions(profile_id: str, limit: int = 5) -> list[dict[str, Any]]:
    return (
        get_client()
        .table("sessions")
        .select("*")
        .eq("profile_id", profile_id)
        .order("updated_at", desc=True)
        .limit(limit)
        .execute()
        .data
    )


def log_mood(*, session_id: str, profile_id: str, score: int, note: str | None, timestamp: str) -> dict[str, Any]:
    payload = {
        "id": str(uuid4()),
        "session_id": session_id,
        "profile_id": profile_id,
        "score": score,
        "note": note,
        "timestamp": timestamp,
    }
    return get_client().table("mood_logs").insert(payload).execute().data[0]


def get_session_mood(session_id: str) -> list[dict[str, Any]]:
    return (
        get_client()
        .table("mood_logs")
        .select("*")
        .eq("session_id", session_id)
        .order("timestamp")
        .execute()
        .data
    )


def create_homework(*, profile_id: str, session_id: str, title: str, instructions: str, due_at: str | None, now: str) -> dict[str, Any]:
    payload = {
        "id": str(uuid4()),
        "profile_id": profile_id,
        "session_id": session_id,
        "title": title,
        "instructions": instructions,
        "status": "assigned",
        "reflection": None,
        "due_at": due_at,
        "created_at": now,
        "updated_at": now,
    }
    return get_client().table("homework").insert(payload).execute().data[0]


def list_pending_homework(profile_id: str) -> list[dict[str, Any]]:
    return (
        get_client()
        .table("homework")
        .select("*")
        .eq("profile_id", profile_id)
        .in_("status", ["assigned", "in_progress"])
        .order("created_at", desc=True)
        .execute()
        .data
    )


def update_homework(homework_id: str, *, status: str, reflection: str | None, now: str) -> dict[str, Any] | None:
    response = (
        get_client()
        .table("homework")
        .update({"status": status, "reflection": reflection, "updated_at": now})
        .eq("id", homework_id)
        .execute()
        .data
    )
    return response[0] if response else None


def create_schedule(*, profile_id: str, title: str, description: str | None, start_at: str, end_at: str, timezone: str, calendar_url: str, now: str) -> dict[str, Any]:
    payload = {
        "id": str(uuid4()),
        "profile_id": profile_id,
        "title": title,
        "description": description,
        "start_at": start_at,
        "end_at": end_at,
        "timezone": timezone,
        "calendar_url": calendar_url,
        "created_at": now,
    }
    return get_client().table("schedules").insert(payload).execute().data[0]


def list_upcoming_schedules(profile_id: str) -> list[dict[str, Any]]:
    return (
        get_client()
        .table("schedules")
        .select("*")
        .eq("profile_id", profile_id)
        .order("start_at")
        .execute()
        .data
    )
