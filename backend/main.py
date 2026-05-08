import os
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.care import (
    assess_homework_progress,
    build_google_calendar_url,
    build_treatment_plan,
    next_checkin_due,
    suggest_progress_based_cbt_homework,
    summarize_session,
)
from backend import store
from model.engine import Anupama
from backend.openai_responder import generate_reply


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CHECKPOINT_DIR = ROOT_DIR / "checkpoints"
SESSION_DURATION_SECONDS = 20 * 60
SESSION_AUTO_CLOSE_SECONDS = 19 * 60


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(..., min_length=1)
    mode: Literal["support", "cbt", "intake"] = "support"


class MoodLogRequest(BaseModel):
    score: int = Field(..., ge=1, le=5)
    note: str | None = None


class ProfileRequest(BaseModel):
    id: str | None = None
    name: str = Field(..., min_length=1)
    email: str | None = None
    timezone: str = "America/Los_Angeles"
    goals: list[str] = Field(default_factory=list)
    preferred_mode: Literal["support", "cbt", "intake"] = "support"
    date_of_birth: str | None = None
    gender: Literal["female", "male", "nonbinary", "questioning", "prefer_not_to_say"] = "prefer_not_to_say"
    sexual_orientation: Literal[
        "straight",
        "gay",
        "lesbian",
        "bisexual",
        "pansexual",
        "asexual",
        "questioning",
        "prefer_not_to_say",
    ] = "prefer_not_to_say"
    location: str | None = None


class HomeworkUpdateRequest(BaseModel):
    status: Literal["assigned", "in_progress", "completed"]
    reflection: str | None = None


class ScheduleRequest(BaseModel):
    profile_id: str
    title: str = Field(..., min_length=1)
    description: str | None = None
    start_at: str
    end_at: str
    timezone: str = "America/Los_Angeles"


class CloseSessionRequest(BaseModel):
    mode: Literal["support", "cbt", "intake"] | None = None


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: str
    mode: Literal["support", "cbt", "intake"] | None = None
    mood_score: int | None = None
    distortion: str | None = None
    is_crisis: bool | None = None


class SessionState(BaseModel):
    id: str
    created_at: str
    history: list[ChatTurn] = Field(default_factory=list)
    mood_log: list[dict] = Field(default_factory=list)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def seconds_since(timestamp: str) -> int:
    created = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return max(0, int((datetime.now(timezone.utc) - created).total_seconds()))


SELF_HARM_PATTERNS = [
    r"\bkill myself\b",
    r"\bend my life\b",
    r"\bwant to die\b",
    r"\bsuicid(?:e|al)\b",
    r"\bself[- ]harm\b",
    r"\bhurt myself\b",
    r"\boverdose\b",
]

VIOLENCE_PATTERNS = [
    r"\bhit me\b",
    r"\bhurt me\b",
    r"\bbeat me\b",
    r"\bassault(?:ed)?\b",
    r"\babus(?:e|ed|ive)\b",
    r"\battacked me\b",
    r"\bthey hit me\b",
    r"\bsomebody hit me\b",
]

VIOLENCE_SAFETY_RESPONSE = (
    "I'm sorry that happened to you. No one deserves to be hit or hurt. "
    "Are you safe right now? If you're in immediate danger, call emergency services now "
    "or go to a nearby safe place and contact someone you trust. If you want, you can tell me "
    "what happened and whether the person is still near you."
)

SESSION_END_PATTERNS = [
    r"\bbye\b",
    r"\bthat(?:'s| is) all\b",
    r"\bthank you\b",
    r"\bthanks\b",
    r"\bsee you\b",
    r"\bgoodnight\b",
    r"\bi have to go\b",
]

SESSION_WRAP_READINESS_PATTERNS = [
    r"\bthat helps\b",
    r"\bthat makes sense\b",
    r"\bi can try that\b",
    r"\bi'll try that\b",
    r"\bthat's useful\b",
    r"\bthis gives me something to work on\b",
]

HOMEWORK_REFERENCE_PATTERNS = [
    r"\bhomework\b",
    r"\bassignment\b",
    r"\bexercise\b",
    r"\bworksheet\b",
    r"\bthought record\b",
    r"\bcontinuum\b",
    r"\bevidence check\b",
    r"\bprediction log\b",
    r"\bbehavioral experiment\b",
]


def has_pattern(text: str, patterns: list[str]) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in patterns)


def get_turn_role(item: dict | ChatTurn) -> str:
    return item["role"] if isinstance(item, dict) else item.role


def count_user_turns(history: list[dict | ChatTurn]) -> int:
    return sum(1 for item in history if get_turn_role(item) == "user")


def detect_session_phase(
    mode: str,
    history: list[dict | ChatTurn],
    *,
    is_first_session: bool,
    message: str,
) -> str:
    explicit_wrap = has_pattern(message, SESSION_END_PATTERNS)
    user_turns = count_user_turns(history)
    if explicit_wrap:
        return "closing"
    if is_first_session:
        if user_turns <= 2:
            return "opening"
        if user_turns <= 5:
            return "working"
        return "closing"
    if mode == "cbt":
        if user_turns <= 2:
            return "opening"
        if user_turns <= 5:
            return "working"
        return "closing"
    if user_turns <= 2:
        return "opening"
    return "working"


def should_close_session(
    mode: str,
    history: list[dict | ChatTurn],
    message: str,
    *,
    is_first_session: bool,
) -> bool:
    explicit_wrap = has_pattern(message, SESSION_END_PATTERNS)
    if explicit_wrap:
        return True
    user_turns = count_user_turns(history)
    ready_for_wrap = has_pattern(message, SESSION_WRAP_READINESS_PATTERNS)
    if is_first_session:
        return user_turns >= 6
    if mode == "cbt":
        return user_turns >= 6 or (user_turns >= 4 and ready_for_wrap)
    return False


def build_memory_context(
    *,
    sessions: list[dict],
    current_session_id: str,
    pending_homework: list[dict],
) -> str | None:
    prior_sessions = [item for item in sessions if item["id"] != current_session_id and item.get("summary")]
    if not prior_sessions and not pending_homework:
        return None

    sections: list[str] = []
    if prior_sessions:
        earliest = prior_sessions[-1]
        latest = prior_sessions[0]
        sections.append(f"Initial understanding of the person:\n{earliest['summary']}")
        if latest["id"] != earliest["id"]:
            sections.append(f"Most recent prior session:\n{latest['summary']}")
    if pending_homework:
        homework_titles = ", ".join(item["title"] for item in pending_homework[:3])
        sections.append(f"Open homework to review: {homework_titles}")
    return "\n\n".join(sections)


def message_references_homework(message: str) -> bool:
    return has_pattern(message, HOMEWORK_REFERENCE_PATTERNS)


def build_homework_review_reply(message: str, pending_homework: list[dict]) -> str:
    stripped = message.strip()
    lowered = stripped.lower()
    if any(token in lowered for token in ["not good", "rough", "hard", "overwhelmed", "anxious", "sad", "stressed"]):
        opening = "I'm sorry it has been feeling that heavy."
    elif any(token in lowered for token in ["better", "good", "okay", "fine"]):
        opening = "I'm glad you checked in."
    else:
        opening = "Thanks for sharing that."

    current_homework = pending_homework[0]["title"] if pending_homework else "the exercise from last time"
    return (
        f"{opening} Before we dive further into today, how did it go with {current_homework} from our last session? "
        "What felt doable, and what got in the way if you weren't able to finish it?"
    )


def opening_message_for_mode(
    mode: str,
    *,
    pending_homework: list[dict],
    is_first_session: bool,
) -> str:
    if mode == "cbt" and pending_homework and not is_first_session:
        return build_homework_review_reply("Checking in", pending_homework)
    if mode == "support":
        return "Hi, I’m Anupama. We can start gently. What has this week felt like for you?"
    if mode == "cbt":
        return "Hi, I’m Anupama in CBT Coach mode. We’ll start by understanding what has been weighing on you, then work toward one helpful next step."
    return "Hi, I’m Anupama in Intake Assistant mode. We can use this session to gather your story, what feels hardest lately, and what you want support with."


def get_auth_user(authorization: str | None):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.split(" ", 1)[1]
    try:
        user = store.get_client().auth.get_user(token).user
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid auth token: {exc}") from exc
    if not user:
        raise HTTPException(status_code=401, detail="Invalid auth token")
    return user


def build_summary(session: SessionState) -> str:
    user_messages = [turn.content for turn in session.history if turn.role == "user"]
    assistant_messages = [turn for turn in session.history if turn.role == "assistant"]
    latest_mode = next((turn.mode for turn in reversed(session.history) if turn.mode), "support")
    latest_assistant = assistant_messages[-1] if assistant_messages else None
    mood_values = [entry["score"] for entry in session.mood_log if isinstance(entry.get("score"), int)]

    average_mood = round(sum(mood_values) / len(mood_values), 1) if mood_values else None
    recent_concerns = "\n".join(f"- {message}" for message in user_messages[-3:]) or "- No user messages recorded yet."

    key_findings = []
    if latest_assistant and latest_assistant.mood_score is not None:
        key_findings.append(f"- Latest detected mood score: {latest_assistant.mood_score}/5")
    if average_mood is not None:
        key_findings.append(f"- Average logged mood: {average_mood}/5")
    if latest_assistant and latest_assistant.distortion:
        key_findings.append(f"- Most recent cognitive distortion signal: {latest_assistant.distortion}")
    if latest_assistant and latest_assistant.is_crisis:
        key_findings.append("- Crisis protocol was triggered during this session.")
    if not key_findings:
        key_findings.append("- No classifier findings are available yet.")

    return (
        "Session Overview\n"
        f"- Session ID: {session.id}\n"
        f"- Conversation mode: {latest_mode}\n"
        f"- Messages exchanged: {len(session.history)}\n"
        f"- Created at: {session.created_at}\n\n"
        "Recent Concerns\n"
        f"{recent_concerns}\n\n"
        "Clinical Signals\n"
        f"{chr(10).join(key_findings)}\n\n"
        "Next-Step Note\n"
        "- This summary is informational only and should be reviewed by a qualified clinician."
    )


def get_allowed_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "*")
    if raw.strip() == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def get_user_id_from_auth(authorization: str | None) -> str:
    return get_auth_user(authorization).id


def build_session_context(user_id: str, session_id: str) -> dict:
    profile = store.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    all_sessions = store.list_all_sessions(user_id)
    all_homework = store.list_all_homework(user_id)
    pending_homework = [item for item in all_homework if item.get("status") in {"assigned", "in_progress"}]
    is_first_session = len(all_sessions) <= 1
    memory_context = build_memory_context(
        sessions=all_sessions,
        current_session_id=session_id,
        pending_homework=pending_homework,
    )
    treatment_plan = build_treatment_plan(
        goals=profile.get("goals", []) or [],
        session_count=len(all_sessions),
        pending_homework_count=len(pending_homework),
    )
    homework_progress = assess_homework_progress(
        homework_items=all_homework,
        treatment_phase=treatment_plan["phase"],
    )
    return {
        "profile": profile,
        "all_sessions": all_sessions,
        "all_homework": all_homework,
        "pending_homework": pending_homework,
        "is_first_session": is_first_session,
        "memory_context": memory_context,
        "treatment_plan": treatment_plan,
        "homework_progress": homework_progress,
    }


def require_owned_session(session_id: str, authorization: str | None) -> dict:
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["profile_id"] != get_user_id_from_auth(authorization):
        raise HTTPException(status_code=403, detail="Forbidden")
    return session


def require_owned_homework(homework_id: str, authorization: str | None) -> dict:
    item = store.get_homework(homework_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Homework not found")
    if item["profile_id"] != get_user_id_from_auth(authorization):
        raise HTTPException(status_code=403, detail="Forbidden")
    return item


def get_or_rehydrate_session_state(session_id: str, session_data: dict) -> SessionState:
    session = SESSIONS.get(session_id)
    if session is not None:
        return session
    messages = store.list_session_messages(session_id)
    session = SessionState(
        id=session_id,
        created_at=session_data["created_at"],
        history=[
            ChatTurn(
                role=message["role"],
                content=message["content"],
                timestamp=message["timestamp"],
                mode=session_data.get("mode"),
                mood_score=message.get("mood_score"),
                distortion=message.get("distortion"),
                is_crisis=message.get("is_crisis"),
            )
            for message in messages
        ],
        mood_log=store.get_session_mood(session_id),
    )
    SESSIONS[session_id] = session
    return session


def build_close_session_payload(
    *,
    engine: Anupama,
    user_id: str,
    session_data: dict,
    session: SessionState,
    mode: str,
) -> dict:
    context = build_session_context(user_id, session_data["id"])
    messages = store.list_session_messages(session_data["id"])
    last_user_message = next((message["content"] for message in reversed(messages) if message["role"] == "user"), "Let's wrap up this session.")
    if not messages:
        raise HTTPException(status_code=400, detail="Session has no messages to close")

    classification = engine.classify(last_user_message)
    reply_text = generate_reply(
        message="Please help me wrap up this session, summarize the key takeaway, and set one realistic between-session practice.",
        mode=mode,
        history=[turn.model_dump() for turn in session.history],
        profile=context["profile"],
        memory_context=context["memory_context"],
        pending_homework=context["pending_homework"],
        homework_progress=context["homework_progress"],
        should_close_session=True,
        is_first_session=context["is_first_session"],
        session_phase="closing",
        treatment_phase=context["treatment_plan"]["phase"],
        treatment_guidance=context["treatment_plan"]["guidance"],
        mood_score=classification.mood_score,
        distortion=classification.distortion,
        crisis_label=classification.crisis_label,
    )

    assistant_turn = ChatTurn(
        role="assistant",
        content=reply_text,
        timestamp=utc_now(),
        mode=mode,
        mood_score=classification.mood_score,
        distortion=classification.distortion,
        is_crisis=False,
    )
    session.history.append(assistant_turn)
    store.add_message(
        session_id=session_data["id"],
        role="assistant",
        content=reply_text,
        timestamp=assistant_turn.timestamp,
        mood_score=classification.mood_score,
        distortion=classification.distortion,
        is_crisis=False,
    )

    homework_item = None
    homework_progress = context["homework_progress"]
    if mode == "cbt" and not context["is_first_session"]:
        title, instructions, homework_progress = suggest_progress_based_cbt_homework(
            distortion=classification.distortion,
            homework_items=context["all_homework"],
            treatment_phase=context["treatment_plan"]["phase"],
        )
        homework_item = store.create_homework(
            profile_id=user_id,
            session_id=session_data["id"],
            title=title,
            instructions=instructions,
            due_at=next_checkin_due(assistant_turn.timestamp),
            now=assistant_turn.timestamp,
        )

    updated_messages = store.list_session_messages(session_data["id"])
    store.update_session_summary(
        session_data["id"],
        summarize_session(
            mode=mode,
            messages=updated_messages,
            distortion=classification.distortion,
            mood_score=classification.mood_score,
        ),
        assistant_turn.timestamp,
    )

    elapsed_seconds = seconds_since(session_data["created_at"])
    return {
        "user_id": user_id,
        "session_id": session_data["id"],
        "reply": reply_text,
        "timestamp": assistant_turn.timestamp,
        "is_crisis": False,
        "mood_score": classification.mood_score,
        "valence": classification.valence,
        "distortion": classification.distortion,
        "crisis_label": classification.crisis_label,
        "conditioning_tokens": engine._build_cond_tokens(classification, mode),
        "homework": homework_item,
        "homework_progress": homework_progress,
        "previous_session_summary": context["memory_context"],
        "pending_homework": context["pending_homework"],
        "session_phase": "closing",
        "session_closing": True,
        "is_first_session": context["is_first_session"],
        "treatment_plan": context["treatment_plan"],
        "session_started_at": session_data["created_at"],
        "session_elapsed_seconds": elapsed_seconds,
        "session_time_remaining_seconds": max(0, SESSION_DURATION_SECONDS - elapsed_seconds),
        "opening_message": opening_message_for_mode(
            mode,
            pending_homework=context["pending_homework"],
            is_first_session=context["is_first_session"],
        ),
    }


@lru_cache(maxsize=1)
def load_engine() -> Anupama:
    checkpoint_dir = Path(os.getenv("MINDFUL_CHECKPOINT_DIR", DEFAULT_CHECKPOINT_DIR))
    if not checkpoint_dir.exists():
        raise RuntimeError(
            f"Checkpoint directory not found: {checkpoint_dir}. "
            "Set MINDFUL_CHECKPOINT_DIR to the folder containing vocab.pkl and model weights."
        )

    required = ["vocab.pkl", "embed_matrix.npy"]
    missing = [name for name in required if not (checkpoint_dir / name).exists()]
    has_model = any((checkpoint_dir / name).exists() for name in ("best_model.pt", "final_model.pt"))
    if missing or not has_model:
        raise RuntimeError(
            "Checkpoint directory is incomplete. Expected vocab.pkl, embed_matrix.npy, "
            "and either best_model.pt or final_model.pt."
        )

    device = os.getenv("MODEL_DEVICE", "auto")
    return Anupama.load(str(checkpoint_dir), device_str=device)


app = FastAPI(title="Anupama API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSIONS: dict[str, SessionState] = {}
store.init_db()


@app.get("/")
def root():
    return {
        "name": "Anupama API",
        "status": "ok",
        "health": "/health",
    }


@app.get("/health")
def health():
    checkpoint_dir = Path(os.getenv("MINDFUL_CHECKPOINT_DIR", DEFAULT_CHECKPOINT_DIR))
    model_ready = checkpoint_dir.exists() and any(
        (checkpoint_dir / name).exists()
        for name in ("best_model.pt", "final_model.pt")
    )
    return {
        "status": "ok",
        "model_ready": bool(model_ready),
        "hf_ready": bool(os.getenv("HF_TOKEN")),
        "llm_provider": "huggingface",
        "checkpoint_dir": str(checkpoint_dir),
        "timestamp": utc_now(),
    }


@app.post("/profiles")
def upsert_profile(payload: ProfileRequest, authorization: str | None = Header(default=None)):
    auth_user = get_auth_user(authorization)
    user_id = auth_user.id
    profile = store.upsert_profile(
        profile_id=user_id,
        name=payload.name.strip(),
        email=payload.email or auth_user.email,
        timezone=payload.timezone,
        goals=payload.goals,
        preferred_mode=payload.preferred_mode,
        date_of_birth=payload.date_of_birth,
        gender=payload.gender,
        sexual_orientation=payload.sexual_orientation,
        location=payload.location,
        now=utc_now(),
    )
    return {"profile": profile}


@app.get("/profiles/{profile_id}")
def get_profile(profile_id: str, authorization: str | None = Header(default=None)):
    if profile_id != get_user_id_from_auth(authorization):
        raise HTTPException(status_code=403, detail="Forbidden")
    profile = store.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"profile": profile}


@app.get("/profiles/{profile_id}/dashboard")
def dashboard(profile_id: str, authorization: str | None = Header(default=None)):
    if profile_id != get_user_id_from_auth(authorization):
        raise HTTPException(status_code=403, detail="Forbidden")
    profile = store.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    recent_sessions = store.list_all_sessions(profile_id)
    upcoming_sessions = store.list_upcoming_schedules(profile_id)
    pending_homework = store.list_pending_homework(profile_id)
    all_homework = store.list_all_homework(profile_id)
    treatment_plan = build_treatment_plan(
        goals=profile.get("goals", []) or [],
        session_count=len(recent_sessions),
        pending_homework_count=len(pending_homework),
    )
    homework_progress = assess_homework_progress(
        homework_items=all_homework,
        treatment_phase=treatment_plan["phase"],
    )
    return {
        "profile": profile,
        "recent_sessions": recent_sessions,
        "upcoming_sessions": upcoming_sessions,
        "pending_homework": pending_homework,
        "all_homework": all_homework,
        "treatment_plan": treatment_plan,
        "homework_progress": homework_progress,
    }


@app.get("/profiles/{profile_id}/sessions")
def list_sessions(profile_id: str, authorization: str | None = Header(default=None)):
    if profile_id != get_user_id_from_auth(authorization):
        raise HTTPException(status_code=403, detail="Forbidden")
    return {"sessions": store.list_all_sessions(profile_id)}


@app.get("/profiles/{profile_id}/homework")
def list_homework(profile_id: str, authorization: str | None = Header(default=None)):
    if profile_id != get_user_id_from_auth(authorization):
        raise HTTPException(status_code=403, detail="Forbidden")
    return {"homework": store.list_all_homework(profile_id)}


@app.post("/profiles/{profile_id}/schedule")
def schedule_session(profile_id: str, payload: ScheduleRequest, authorization: str | None = Header(default=None)):
    if profile_id != get_user_id_from_auth(authorization):
        raise HTTPException(status_code=403, detail="Forbidden")
    profile = store.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    calendar_url = build_google_calendar_url(
        title=payload.title,
        description=payload.description or "Follow-up Anupama session",
        start_at=payload.start_at,
        end_at=payload.end_at,
    )
    item = store.create_schedule(
        profile_id=profile_id,
        title=payload.title,
        description=payload.description,
        start_at=payload.start_at,
        end_at=payload.end_at,
        timezone=payload.timezone,
        calendar_url=calendar_url,
        now=utc_now(),
    )
    return {"schedule": item}


@app.get("/profiles/{profile_id}/schedule")
def list_schedule(profile_id: str, authorization: str | None = Header(default=None)):
    if profile_id != get_user_id_from_auth(authorization):
        raise HTTPException(status_code=403, detail="Forbidden")
    return {"items": store.list_upcoming_schedules(profile_id)}


@app.post("/homework/{homework_id}")
def update_homework(homework_id: str, payload: HomeworkUpdateRequest, authorization: str | None = Header(default=None)):
    require_owned_homework(homework_id, authorization)
    item = store.update_homework(homework_id, status=payload.status, reflection=payload.reflection, now=utc_now())
    if not item:
        raise HTTPException(status_code=404, detail="Homework not found")
    return {"homework": item}


@app.post("/chat")
def chat(payload: ChatRequest, authorization: str | None = Header(default=None)):
    try:
        engine = load_engine()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    user_id = get_user_id_from_auth(authorization)

    session_data = store.get_session(payload.session_id) if payload.session_id else None
    if payload.session_id and not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    is_new_session = session_data is None
    if session_data:
        session_id = session_data["id"]
    else:
        session_data = store.create_session(
            profile_id=user_id,
            mode=payload.mode,
            title=f"{payload.mode.title()} session",
            now=utc_now(),
        )
        session_id = session_data["id"]

    session = get_or_rehydrate_session_state(session_id, session_data)

    elapsed_seconds = seconds_since(session_data["created_at"])
    if elapsed_seconds >= SESSION_DURATION_SECONDS:
        raise HTTPException(status_code=409, detail="This session has ended. Start a new session to continue.")

    user_turn = ChatTurn(
        role="user",
        content=payload.message.strip(),
        timestamp=utc_now(),
        mode=payload.mode,
    )
    session.history.append(user_turn)
    store.add_message(
        session_id=session_id,
        role="user",
        content=payload.message.strip(),
        timestamp=user_turn.timestamp,
    )

    classification = engine.classify(payload.message.strip())
    explicit_self_harm = has_pattern(payload.message, SELF_HARM_PATTERNS)
    violence_disclosure = has_pattern(payload.message, VIOLENCE_PATTERNS)
    is_crisis = classification.crisis_label == "crisis" and explicit_self_harm
    conditioning_tokens = engine._build_cond_tokens(classification, payload.mode) if not is_crisis else []
    context = build_session_context(user_id, session_id)
    profile = context["profile"]
    all_homework = context["all_homework"]
    pending_homework = context["pending_homework"]
    is_first_session = context["is_first_session"]
    treatment_plan = context["treatment_plan"]
    homework_progress = context["homework_progress"]
    session_phase = detect_session_phase(
        payload.mode,
        session.history,
        is_first_session=is_first_session,
        message=payload.message.strip(),
    )
    closing = elapsed_seconds >= SESSION_AUTO_CLOSE_SECONDS or should_close_session(
        payload.mode,
        session.history,
        payload.message.strip(),
        is_first_session=is_first_session,
    )

    if is_crisis:
        reply_text = engine.CRISIS_PROTOCOL
    elif violence_disclosure:
        reply_text = VIOLENCE_SAFETY_RESPONSE
    elif (
        payload.mode == "cbt"
        and is_new_session
        and not is_first_session
        and pending_homework
        and session_phase == "opening"
        and not message_references_homework(payload.message)
    ):
        reply_text = build_homework_review_reply(payload.message, pending_homework)
    else:
        try:
            reply_text = generate_reply(
                message=payload.message.strip(),
                mode=payload.mode,
                history=[turn.model_dump() for turn in session.history[:-1]],
                profile=profile,
                memory_context=context["memory_context"],
                pending_homework=pending_homework,
                homework_progress=homework_progress,
                should_close_session=closing,
                is_first_session=is_first_session,
                session_phase=session_phase,
                treatment_phase=treatment_plan["phase"],
                treatment_guidance=treatment_plan["guidance"],
                mood_score=classification.mood_score,
                distortion=classification.distortion,
                crisis_label=classification.crisis_label,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Hugging Face generation failed: {exc}") from exc

    assistant_turn = ChatTurn(
        role="assistant",
        content=reply_text,
        timestamp=utc_now(),
        mode=payload.mode,
        mood_score=classification.mood_score,
        distortion=classification.distortion,
        is_crisis=is_crisis,
    )
    session.history.append(assistant_turn)
    store.add_message(
        session_id=session_id,
        role="assistant",
        content=reply_text,
        timestamp=assistant_turn.timestamp,
        mood_score=classification.mood_score,
        distortion=classification.distortion,
        is_crisis=is_crisis,
    )

    homework_item = None
    if payload.mode == "cbt" and not is_crisis and closing and not is_first_session:
        title, instructions, homework_progress = suggest_progress_based_cbt_homework(
            distortion=classification.distortion,
            homework_items=all_homework,
            treatment_phase=treatment_plan["phase"],
        )
        homework_item = store.create_homework(
            profile_id=user_id,
            session_id=session_id,
            title=title,
            instructions=instructions,
            due_at=next_checkin_due(assistant_turn.timestamp),
            now=assistant_turn.timestamp,
        )

    session_messages = store.list_session_messages(session_id)
    store.update_session_summary(
        session_id,
        summarize_session(
            mode=payload.mode,
            messages=session_messages,
            distortion=classification.distortion,
            mood_score=classification.mood_score,
        ),
        assistant_turn.timestamp,
    )

    return {
        "user_id": user_id,
        "session_id": session_id,
        "reply": reply_text,
        "timestamp": assistant_turn.timestamp,
        "is_crisis": is_crisis,
        "mood_score": classification.mood_score,
        "valence": classification.valence,
        "distortion": classification.distortion,
        "crisis_label": classification.crisis_label,
        "conditioning_tokens": conditioning_tokens,
        "homework": homework_item,
        "homework_progress": homework_progress,
        "previous_session_summary": context["memory_context"],
        "pending_homework": pending_homework,
        "session_phase": session_phase,
        "session_closing": closing,
        "is_first_session": is_first_session,
        "treatment_plan": treatment_plan,
        "session_started_at": session_data["created_at"],
        "session_elapsed_seconds": elapsed_seconds,
        "session_time_remaining_seconds": max(0, SESSION_DURATION_SECONDS - elapsed_seconds),
        "opening_message": opening_message_for_mode(
            payload.mode,
            pending_homework=pending_homework,
            is_first_session=is_first_session,
        ),
    }


@app.post("/session/{session_id}/close")
def close_session(session_id: str, payload: CloseSessionRequest, authorization: str | None = Header(default=None)):
    try:
        engine = load_engine()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    session_data = require_owned_session(session_id, authorization)
    user_id = get_user_id_from_auth(authorization)
    mode = payload.mode or session_data.get("mode") or "support"
    session = get_or_rehydrate_session_state(session_id, session_data)
    return build_close_session_payload(
        engine=engine,
        user_id=user_id,
        session_data=session_data,
        session=session,
        mode=mode,
    )


@app.post("/mood/{session_id}")
def log_mood(session_id: str, payload: MoodLogRequest, authorization: str | None = Header(default=None)):
    require_owned_session(session_id, authorization)
    user_id = get_user_id_from_auth(authorization)

    entry = store.log_mood(
        session_id=session_id,
        profile_id=user_id,
        score=payload.score,
        note=payload.note,
        timestamp=utc_now(),
    )
    return {"session_id": session_id, "mood_log": store.get_session_mood(session_id), "entry": entry}


@app.get("/mood/{session_id}")
def get_mood(session_id: str, authorization: str | None = Header(default=None)):
    require_owned_session(session_id, authorization)
    return {"session_id": session_id, "mood_log": store.get_session_mood(session_id)}


@app.get("/summary/{session_id}")
def get_summary(session_id: str, authorization: str | None = Header(default=None)):
    session = require_owned_session(session_id, authorization)
    summary = session.get("summary")
    if not summary:
        messages = store.list_session_messages(session_id)
        if not messages:
            raise HTTPException(status_code=404, detail="Session not found")
        summary = build_summary(
            SessionState(
                id=session["id"],
                created_at=session["created_at"],
                history=[ChatTurn(**message) for message in messages],
                mood_log=store.get_session_mood(session_id),
            )
        )
    return {"session_id": session_id, "summary": summary}


@app.delete("/session/{session_id}")
def delete_session(session_id: str, authorization: str | None = Header(default=None)):
    require_owned_session(session_id, authorization)
    SESSIONS.pop(session_id, None)
    return {"deleted": True, "session_id": session_id}


@app.delete("/account")
def delete_account(authorization: str | None = Header(default=None)):
    user_id = get_user_id_from_auth(authorization)
    store.delete_profile_data(user_id)
    store.get_client().auth.admin.delete_user(user_id, should_soft_delete=True)
    return {"deleted": True}
